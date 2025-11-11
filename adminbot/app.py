import os
import asyncio
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Update,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

import httpx
import json
from html import escape

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
TELEGRAM_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("ADMIN_BOT_TOKEN is not set")

DATAHUB_URL = os.getenv("DATAHUB_URL", "http://localhost:8080")
ADMIN_SERVICE_URL = os.getenv("ADMIN_SERVICE_URL", "http://adminservice:8080")
ADMIN_USERNAME = "cbr_18"

# Инициализация бота
bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dispatcher = Dispatcher(storage=storage)
app = FastAPI()

# Состояния для FSM
class AdminStates(StatesGroup):
    waiting_for_new_admin = State()
    waiting_for_uuid_search = State()

# Хранилище админов (в реальном проекте лучше использовать БД)
admins_lock = asyncio.Lock()
admins: Dict[str, Dict[str, Any]] = {}


def _normalize_telegram_identifier(identifier: str) -> Optional[Tuple[str, Any, str]]:
    if identifier is None:
        return None

    raw = str(identifier).strip()
    if not raw:
        return None

    if raw.startswith("@"):
        raw = raw[1:]
    if not raw:
        return None

    is_numeric = raw.lstrip("-").isdigit()

    if is_numeric:
        key = f"id:{raw}"
        try:
            chat_ref: Any = int(raw)
        except ValueError:
            chat_ref = raw
        display = raw
    else:
        normalized_username = raw
        key = f"username:{normalized_username.lower()}"
        chat_ref = f"@{normalized_username}"
        display = f"@{normalized_username}"

    return key, chat_ref, display


def _store_admin(
    identifier: str,
    *,
    source: str,
    added_by: Optional[str] = None,
    alias_of: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    normalized = _normalize_telegram_identifier(identifier)
    if not normalized:
        return None

    key, chat_ref, display = normalized
    record = {
        "chat_ref": chat_ref,
        "display": display,
        "source": source,
        "added_by": added_by or "system",
        "added_at": datetime.now(),
        "alias_of": alias_of,
        "key": key,
    }
    admins[key] = record
    return record


# Изначально добавляем fallback-админа для совместимости
_store_admin(ADMIN_USERNAME, source="fallback", added_by="system")

# HTTP клиент для работы с datahub
http_client = httpx.AsyncClient(timeout=30.0)

# --- Модели данных ---
class CarSearchRequest(BaseModel):
    uuid: str

class LeadNotification(BaseModel):
    car: dict
    user: Optional[str] = None

# --- Вспомогательные функции ---
async def is_admin(username: str) -> bool:
    """Проверяет, является ли пользователь админом"""
    normalized = _normalize_telegram_identifier(username)
    if not normalized:
        return False
    key = normalized[0]
    async with admins_lock:
        return key in admins


async def refresh_admins_from_service() -> int:
    """Подтягивает Telegram ID администраторов из adminservice"""
    target_url = f"{ADMIN_SERVICE_URL.rstrip('/')}/api/tgid/list"

    try:
        response = await http_client.get(target_url)
        response.raise_for_status()
        payload = response.json()

        if not isinstance(payload, list):
            logger.warning("Unexpected response while fetching Telegram IDs: %s", payload)
            return 0

        processed: list[tuple[str, Optional[int]]] = []
        for item in payload:
            if isinstance(item, dict):
                telegram_identifier = str(item.get("telegramId", "") or "").strip()
                chat_identifier = item.get("chatId")

                chat_value: Optional[int] = None
                if chat_identifier is not None:
                    try:
                        chat_value = int(chat_identifier)
                    except (TypeError, ValueError):
                        logger.warning("Invalid chatId received from adminservice: %s", chat_identifier)

                processed.append((telegram_identifier, chat_value))
            elif isinstance(item, (str, int)):
                processed.append((str(item).strip(), None))

        processed = [entry for entry in processed if entry[0] or entry[1] is not None]

        async with admins_lock:
            # Сохраняем уже заданных через бота админов
            service_keys = [key for key, meta in admins.items() if meta.get("source") == "service"]
            for key in service_keys:
                admins.pop(key, None)

            for telegram_identifier, chat_value in processed:
                preferred_identifier: Optional[str]
                if chat_value is not None:
                    preferred_identifier = str(chat_value)
                elif telegram_identifier:
                    preferred_identifier = telegram_identifier
                else:
                    preferred_identifier = None

                if not preferred_identifier:
                    continue

                record = _store_admin(preferred_identifier, source="service", added_by="adminservice")
                if record is None:
                    continue

                if telegram_identifier:
                    record["display"] = telegram_identifier
                    record["telegram_identifier"] = telegram_identifier
                if chat_value is not None:
                    record["chat_ref"] = chat_value
                    record["chat_id"] = chat_value

                if telegram_identifier and chat_value is not None:
                    alias_record = _store_admin(
                        telegram_identifier,
                        source="service",
                        added_by="adminservice",
                        alias_of=record.get("key")
                    )
                    if alias_record is not None:
                        alias_record["display"] = telegram_identifier
                        alias_record["chat_ref"] = record["chat_ref"]
                        alias_record["chat_id"] = chat_value

            total = sum(
                1
                for meta in admins.values()
                if meta.get("source") == "service" and not meta.get("alias_of")
            )

        logger.info("Synced %s admin Telegram IDs from adminservice", total)
        return total

    except httpx.HTTPStatusError as exc:
        logger.error(
            "HTTP error while syncing Telegram IDs from adminservice: %s - %s",
            exc.response.status_code,
            exc.response.text,
        )
        raise
    except Exception as exc:
        logger.error("Failed to sync Telegram IDs from adminservice: %s", exc)
        raise

async def send_to_all_admins(message_text: str, reply_markup: Optional[InlineKeyboardMarkup] = None):
    """Отправляет сообщение всем админам"""
    # Получаем chat_id из переменной окружения или используем username
    admin_chat_id = os.getenv("ADMIN_CHAT_ID")

    targets: list[Any] = []
    seen: set[str] = set()

    async with admins_lock:
        recipients = list(admins.values())

    if admin_chat_id:
        targets.append(admin_chat_id)
        seen.add(str(admin_chat_id))

    for admin_meta in recipients:
        if admin_meta.get("alias_of"):
            continue
        chat_ref = admin_meta.get("chat_ref")
        key_ref = str(chat_ref)
        if key_ref not in seen:
            targets.append(chat_ref)
            seen.add(key_ref)

    for target in targets:
        try:
            await bot.send_message(
                chat_id=target,
                text=message_text,
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Failed to send message to {target}: {e}")

async def send_car_image(image_url: str, caption: str = "Фото машины"):
    """Отправляет картинку машины всем админам"""
    admin_chat_id = os.getenv("ADMIN_CHAT_ID")

    targets: list[Any] = []
    seen: set[str] = set()

    async with admins_lock:
        recipients = list(admins.values())

    if admin_chat_id:
        targets.append(admin_chat_id)
        seen.add(str(admin_chat_id))

    for admin_meta in recipients:
        if admin_meta.get("alias_of"):
            continue
        chat_ref = admin_meta.get("chat_ref")
        key_ref = str(chat_ref)
        if key_ref not in seen:
            targets.append(chat_ref)
            seen.add(key_ref)

    for target in targets:
        try:
            await bot.send_photo(
                chat_id=target,
                photo=image_url,
                caption=f"📸 {caption}"
            )
        except Exception as e:
            logger.error(f"Failed to send image to {target}: {e}")

async def search_car_by_uuid(uuid: str) -> Optional[dict]:
    """Поиск машины по UUID в datahub"""
    try:
        response = await http_client.get(f"{DATAHUB_URL}/cars/uuid/{uuid}")
        if response.status_code == 200:
            data = response.json()
            return data.get("data")
        elif response.status_code == 404:
            return None
        else:
            logger.error(f"Unexpected status code {response.status_code} for UUID {uuid}")
            return None
    except Exception as e:
        logger.error(f"Error searching car by UUID {uuid}: {e}")
        return None

def format_car_info(car: dict) -> str:
    """Форматирует информацию о машине для отправки"""
    return f"""
🚗 <b>Информация о машине</b>

<b>UUID:</b> {car.get('uuid', 'N/A')}
<b>Название:</b> {car.get('title', 'N/A')}
<b>Бренд:</b> {car.get('brand_name', 'N/A')}
<b>Модель:</b> {car.get('car_name', 'N/A')}
<b>Серия:</b> {car.get('series_name', 'N/A')}
<b>Год:</b> {car.get('year', 'N/A')}
<b>Пробег:</b> {car.get('mileage', 'N/A')} км
<b>Цена:</b> {car.get('price', 'N/A')}
<b>Город:</b> {car.get('city', 'N/A')}
<b>Источник:</b> {car.get('source', 'N/A')}
<b>Ссылка:</b> {car.get('link', 'N/A')}
<b>Описание:</b> {car.get('description', 'N/A')}
<b>Цвет:</b> {car.get('color', 'N/A')}
<b>КПП:</b> {car.get('transmission', 'N/A')}
<b>Тип топлива:</b> {car.get('fuel_type', 'N/A')}
<b>Объем двигателя:</b> {car.get('engine_volume', 'N/A')}
<b>Тип кузова:</b> {car.get('body_type', 'N/A')}
<b>Привод:</b> {car.get('drive_type', 'N/A')}
<b>Состояние:</b> {car.get('condition', 'N/A')}
<b>Доступна:</b> {'Да' if car.get('is_available') else 'Нет'}
"""

# --- Обработчики команд ---
@dispatcher.message(CommandStart())
async def handle_start(message: Message):
    """Обработчик команды /start"""
    username = message.from_user.username
    if not username:
        await message.answer("❌ Для использования бота необходимо указать username в настройках Telegram")
        return
    
    if await is_admin(username):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Поиск по UUID", callback_data="search_uuid")],
            [InlineKeyboardButton(text="👥 Управление админами", callback_data="manage_admins")],
            [InlineKeyboardButton(text="ℹ️ Список админов", callback_data="list_admins")]
        ])
        await message.answer(
            f"👋 Добро пожаловать, @{username}!\n\n"
            "Вы являетесь администратором бота.\n"
            "Выберите действие:",
            reply_markup=keyboard
        )
    else:
        await message.answer(
            "❌ У вас нет прав доступа к этому боту.\n"
            "Обратитесь к администратору"
        )


@dispatcher.message(F.web_app_data)
async def handle_web_app_data(message: Message):
    """Обработчик данных, полученных из Telegram WebApp"""
    data = message.web_app_data.data if message.web_app_data else None
    if not data:
        await message.answer("Не удалось обработать данные из WebApp.")
        return

    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        await message.answer("Получены некорректные данные из WebApp.")
        return

    if payload.get("type") != "order_success":
        # Игнорируем прочие события
        return

    car_payload = payload.get("car", {})
    title = car_payload.get("title") or payload.get("carTitle") or "Без названия"
    brand = car_payload.get("brand") or ""
    model = car_payload.get("model") or ""
    image_url = car_payload.get("image") or payload.get("imageUrl")

    safe_title = escape(title)
    safe_brand = escape(brand) if brand else None
    safe_model = escape(model) if model else None

    lines = [f"✅ Заявка по машине «{safe_title}» успешно отправлена."]
    info_lines = []
    if safe_brand:
        info_lines.append(f"Марка: {safe_brand}")
    if safe_model:
        info_lines.append(f"Модель: {safe_model}")
    if info_lines:
        lines.append("")
        lines.extend(info_lines)

    caption = "\n".join(lines)

    if image_url:
        try:
            await message.answer_photo(
                photo=image_url,
                caption=caption,
                parse_mode="HTML"
            )
            return
        except Exception as exc:
            logger.warning("Failed to send web app image: %s", exc)

    await message.answer(caption, parse_mode="HTML")


@dispatcher.callback_query(F.data == "search_uuid")
async def handle_search_uuid_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки поиска по UUID"""
    await callback.message.edit_text(
        "🔍 <b>Поиск по UUID</b>\n\n"
        "Введите UUID машины для поиска:",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_uuid_search)
    await callback.answer()

@dispatcher.message(AdminStates.waiting_for_uuid_search)
async def handle_uuid_input(message: Message, state: FSMContext):
    """Обработчик ввода UUID"""
    uuid = message.text.strip()
    
    # Показываем индикатор загрузки
    loading_msg = await message.answer("🔍 Поиск машины...")
    
    # Ищем машину
    car = await search_car_by_uuid(uuid)
    
    if car:
        car_info = format_car_info(car)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Новый поиск", callback_data="search_uuid")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        await loading_msg.edit_text(car_info, reply_markup=keyboard, parse_mode="HTML")
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Попробовать снова", callback_data="search_uuid")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
        await loading_msg.edit_text(
            f"❌ Машина с UUID <code>{uuid}</code> не найдена.\n\n"
            "Проверьте правильность UUID и попробуйте снова.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    
    await state.clear()

@dispatcher.callback_query(F.data == "manage_admins")
async def handle_manage_admins_callback(callback: CallbackQuery):
    """Обработчик кнопки управления админами"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить админа", callback_data="add_admin")],
        [InlineKeyboardButton(text="👥 Список админов", callback_data="list_admins")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    await callback.message.edit_text(
        "👥 <b>Управление админами</b>\n\n"
        "Выберите действие:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@dispatcher.callback_query(F.data == "add_admin")
async def handle_add_admin_callback(callback: CallbackQuery, state: FSMContext):
    """Обработчик добавления админа"""
    await callback.message.edit_text(
        "➕ <b>Добавление админа</b>\n\n"
        "Введите username нового админа (без @):",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_new_admin)
    await callback.answer()

@dispatcher.message(AdminStates.waiting_for_new_admin)
async def handle_new_admin_input(message: Message, state: FSMContext):
    """Обработчик ввода username нового админа"""
    new_admin = message.text.strip().lstrip('@')
    
    if not new_admin:
        await message.answer("❌ Username не может быть пустым")
        return
    
    normalized = _normalize_telegram_identifier(new_admin)
    if not normalized:
        await message.answer("❌ Некорректный username")
        await state.clear()
        return

    key = normalized[0]

    async with admins_lock:
        if key in admins:
            await message.answer(f"❌ @{new_admin} уже является админом")
            await state.clear()
            return
        record = _store_admin(new_admin, source="bot", added_by=message.from_user.username)
    display_name = (record or {}).get("display") or f"@{new_admin}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Управление админами", callback_data="manage_admins")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await message.answer(
        f"✅ @{new_admin} успешно добавлен в список админов!",
        reply_markup=keyboard
    )
    
    # Уведомляем всех админов о добавлении нового
    await send_to_all_admins(
        f"👥 <b>Новый админ добавлен</b>\n\n"
        f"{display_name} добавлен в список админов пользователем @{message.from_user.username}",
        keyboard
    )
    
    await state.clear()

@dispatcher.callback_query(F.data == "list_admins")
async def handle_list_admins_callback(callback: CallbackQuery):
    """Обработчик показа списка админов"""
    admin_list = []
    async with admins_lock:
        snapshot = list(admins.values())

    for admin_data in snapshot:
        if admin_data.get("alias_of"):
            continue
        added_by = admin_data.get("added_by", "system")
        added_at = admin_data.get("added_at", datetime.now()).strftime("%d.%m.%Y %H:%M")
        source = admin_data.get("source", "bot")
        display = admin_data.get("display") or admin_data.get("chat_ref")
        chat_id = admin_data.get("chat_id")
        chat_info = f", chat_id {chat_id}" if chat_id is not None else ""
        admin_list.append(f"• {display}{chat_info} (источник: {source}, добавлен @{added_by}, {added_at})")
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Управление админами", callback_data="manage_admins")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(
        f"👥 <b>Список админов</b>\n\n" + "\n".join(admin_list),
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

@dispatcher.callback_query(F.data == "main_menu")
async def handle_main_menu_callback(callback: CallbackQuery):
    """Обработчик возврата в главное меню"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Поиск по UUID", callback_data="search_uuid")],
        [InlineKeyboardButton(text="👥 Управление админами", callback_data="manage_admins")],
        [InlineKeyboardButton(text="ℹ️ Список админов", callback_data="list_admins")]
    ])
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>\n\n"
        "Выберите действие:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    await callback.answer()

# --- API эндпоинты ---
@app.get("/health")
async def health():
    """Проверка работоспособности"""
    return {
        "status": "ok",
        "service": "adminbot",
        "admins_count": len(admins)
    }

@app.post("/lead")
async def handle_lead_request(payload: LeadNotification):
    """Обработка заявок от telegramapp"""
    try:
        car = payload.car
        user = payload.user or "Неизвестный пользователь"
        
        # Получаем текущее время
        current_time = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        # Формируем сообщение о заявке
        message_text = f"""
🚗 <b>Новая заявка с сайта</b>

<b>⏰ Время:</b> {current_time}
<b>👤 Пользователь:</b> {user}
<b>🔍 UUID:</b> <code>{car.get('uuid', 'N/A')}</code>
<b>📝 Название:</b> {car.get('title', 'N/A')}
<b>🏷️ Бренд:</b> {car.get('brand_name', 'N/A')}
<b>🚙 Модель:</b> {car.get('car_name', 'N/A')}
<b>📅 Год:</b> {car.get('year', 'N/A')}
<b>💰 Цена:</b> {car.get('price', 'N/A')}
<b>🏙️ Город:</b> {car.get('city', 'N/A')}
<b>🔗 Ссылка:</b> {car.get('link', 'N/A')}
        """
        
        # Отправляем сообщение
        await send_to_all_admins(message_text)
        
        # Если есть картинка, отправляем её отдельно
        if car.get('image'):
            try:
                await send_car_image(car['image'], car.get('title', 'Машина'))
            except Exception as e:
                logger.error(f"Failed to send car image: {e}")

        return {"status": "ok", "message": "Lead notification sent to all admins"}
        
    except Exception as e:
        logger.error(f"Error handling lead request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sync/telegram-ids")
async def sync_telegram_ids():
    """Применяет список Telegram ID из adminservice"""
    try:
        synced = await refresh_admins_from_service()
        async with admins_lock:
            total = len(admins)
        return {"status": "ok", "synced": synced, "total": total}
    except Exception as exc:
        logger.exception("Failed to sync Telegram IDs via API")
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/bot")
async def telegram_webhook(request: Request):
    """Webhook для получения обновлений от Telegram"""
    try:
        update_dict = await request.json()
        update = Update.model_validate(update_dict)
        await dispatcher.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        return JSONResponse(status_code=200, content={"ok": True})

@app.on_event("startup")
async def on_startup():
    """Инициализация при запуске"""
    webhook_url = os.getenv("ADMIN_WEBHOOK_URL")
    if webhook_url:
        await bot.set_webhook(url=webhook_url)
    try:
        synced = await refresh_admins_from_service()
        logger.info("Loaded %s admin Telegram IDs from adminservice on startup", synced)
    except Exception as exc:
        logger.warning("Unable to sync Telegram IDs on startup: %s", exc)
    logger.info("Admin Bot started")

@app.on_event("shutdown")
async def on_shutdown():
    """Очистка при остановке"""
    await bot.session.close()
    await http_client.aclose()
    logger.info("Admin Bot stopped")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
