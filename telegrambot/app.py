import os
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    WebAppInfo,
    MenuButtonWebApp,
    ReplyKeyboardMarkup,
    KeyboardButton,
)


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    # Fail fast to make misconfiguration obvious in container logs
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

LEAD_TARGET_CHAT = os.getenv("LEAD_TARGET_CHAT", "@Maksim_CarCatch")
WEBAPP_URL = os.getenv("TELEGRAM_WEBAPP_URL", "https://car-catch.ru/podbortg")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dispatcher = Dispatcher()

app = FastAPI()


def build_reply_keyboard() -> ReplyKeyboardMarkup:
    # Left-most WebApp button, plus a "Начать" text button
    keyboard = [
        [
            KeyboardButton(text="🚗 Открыть мини‑приложение", web_app=WebAppInfo(url=WEBAPP_URL)),
            KeyboardButton(text="Начать"),
        ]
    ]
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
        one_time_keyboard=False,
    )


# --- Telegram Bot Handlers ---
@dispatcher.message(CommandStart())
async def handle_start(message: Message):
    reply_kb = build_reply_keyboard()
    await message.answer(
        "Бот для заявок CarCatch активен!\n\nОткройте мини‑приложение кнопкой слева или нажмите \"Начать\".",
        reply_markup=reply_kb,
    )


@dispatcher.message(F.text.casefold() == "начать")
async def handle_begin(message: Message):
    reply_kb = build_reply_keyboard()
    await message.answer(
        "Готово! Используйте кнопку слева \"🚗 Открыть мини‑приложение\" для запуска.",
        reply_markup=reply_kb,
    )


# --- API Schemas ---
class CarPayload(BaseModel):
    brand_name: Optional[str] = None
    car_name: Optional[str] = None
    year: Optional[Any] = None
    city: Optional[str] = None
    price: Optional[Any] = None
    link: Optional[str] = None


class LeadRequest(BaseModel):
    car: CarPayload
    user: Optional[str] = None


# --- Service Endpoints ---
@app.get("/health", response_class=PlainTextResponse)
async def health() -> str:
    return "healthy\n"


@app.post("/lead")
async def lead(payload: LeadRequest):
    car = payload.car

    # Compose message text similarly to the Node.js version
    lines = ["🚗 Новая заявка с сайта"]
    if payload.user:
        lines.append(f"Пользователь: {payload.user}")
    lines.append(f"Бренд: {car.brand_name or '-'}")
    lines.append(f"Модель: {car.car_name or '-'}")
    lines.append(f"Год: {car.year or '-'}")
    lines.append(f"Город: {car.city or '-'}")
    lines.append(f"Цена: {car.price or '-'}")
    lines.append(f"Ссылка: {car.link or '-'}")

    text = "\n".join(lines)

    try:
        await bot.send_message(chat_id=LEAD_TARGET_CHAT, text=text, parse_mode="Markdown")
        return {"ok": True}
    except Exception as exc:
        # Mirror Node.js behavior with 500 on send failure
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/bot")
async def telegram_webhook(request: Request):
    try:
        update_dict = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    try:
        update = Update.model_validate(update_dict)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Telegram update")

    # Feed update to dispatcher
    try:
        await dispatcher.feed_update(bot, update)
    except Exception:
        # Don't leak internal errors to Telegram
        return JSONResponse(status_code=200, content={"ok": True})

    return {"ok": True}


@app.on_event("startup")
async def on_startup():
    webhook_url = os.getenv("TELEGRAM_WEBHOOK_URL")
    # If provided, set webhook automatically; otherwise, assume it's configured externally
    if webhook_url:
        await bot.set_webhook(url=webhook_url)

    # Set a menu button to open the Mini App
    try:
        await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(text="🚗 Подбор авто", web_app=WebAppInfo(url=WEBAPP_URL)))
    except Exception:
        # Non-critical; continue startup even if Telegram rejects
        pass


@app.on_event("shutdown")
async def on_shutdown():
    await bot.session.close()
