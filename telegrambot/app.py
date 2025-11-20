import os
import json
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Update,
    Message,
    WebAppInfo,
    MenuButtonWebApp,
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


# Reply keyboard удалена: используем только кнопку меню (гамбургер)


# --- Telegram Bot Handlers ---
@dispatcher.message(CommandStart())
async def handle_start(message: Message):
    await message.answer(
        "Бот для заявок CarCatch активен!\n\nОткройте мини‑приложение через кнопку в меню.",
    )


@dispatcher.message(F.text.casefold() == "начать")
async def handle_begin(message: Message):
    await message.answer(
        "Готово! Используйте кнопку в меню "
        "\"🚗 Подбор авто\" для запуска мини‑приложения.",
    )


@dispatcher.message(F.web_app_data)
async def handle_web_app_data(message: Message):
    data = message.web_app_data.data if message.web_app_data else None
    if not data:
        await message.answer("Не удалось обработать данные мини‑приложения.")
        return

    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        await message.answer("Получены некорректные данные мини‑приложения.")
        return

    if payload.get("type") != "order_success":
        return

    car_payload = payload.get("car") or {}
    title = car_payload.get("title") or car_payload.get("car_name") or car_payload.get("model") or "Без названия"
    brand = car_payload.get("brand") or car_payload.get("brand_name")
    model = car_payload.get("model") or car_payload.get("car_name")
    price = car_payload.get("price")
    city = car_payload.get("city")
    image_url = car_payload.get("image")

    lines = [f"✅ Заявка по машине «{title}» успешно отправлена."]
    if brand or model:
        lines.append("")
        if brand:
            lines.append(f"Марка: {brand}")
        if model:
            lines.append(f"Модель: {model}")
    if price:
        lines.append(f"Цена: {price}")
    if city:
        lines.append(f"Город: {city}")
    lines.append("")
    lines.append("Мы свяжемся с вами в ближайшее время.")

    message_text = "\n".join(lines)

    try:
        if image_url:
            await message.answer_photo(photo=image_url, caption=message_text)
        else:
            await message.answer(message_text)
    except Exception:
        await message.answer("Заявка отправлена! Мы свяжемся с вами в ближайшее время.")


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


class NotifyUserRequest(BaseModel):
    chatId: int
    message: str
    imageUrl: Optional[str] = None


# --- Service Endpoints ---
@app.get("/health")
@app.head("/health")
async def health():
    """
    Проверка работоспособности API.
    """
    return {
        "data": {
            "status": "ok",
            "service": "telegrambot",
            "bot_connected": TELEGRAM_BOT_TOKEN is not None
        },
        "message": "Service is healthy",
        "status": 200
    }


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


@app.post("/notify-user")
async def notify_user(payload: NotifyUserRequest):
    try:
        if payload.imageUrl:
            await bot.send_photo(
                chat_id=payload.chatId,
                photo=payload.imageUrl,
                caption=payload.message
            )
        else:
            await bot.send_message(
                chat_id=payload.chatId,
                text=payload.message
            )
        return {"ok": True}
    except Exception as exc:
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
