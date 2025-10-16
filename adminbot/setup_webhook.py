#!/usr/bin/env python3
"""
Скрипт для настройки webhook для CBR18 Admin Bot
"""
import os
import asyncio
import sys
from aiogram import Bot

async def setup_webhook():
    """Настройка webhook для бота"""
    bot_token = os.getenv("ADMIN_BOT_TOKEN")
    webhook_url = os.getenv("ADMIN_WEBHOOK_URL")
    
    if not bot_token:
        print("❌ ADMIN_BOT_TOKEN не установлен")
        sys.exit(1)
    
    if not webhook_url:
        print("❌ ADMIN_WEBHOOK_URL не установлен")
        sys.exit(1)
    
    bot = Bot(token=bot_token)
    
    try:
        # Устанавливаем webhook
        await bot.set_webhook(url=webhook_url)
        print(f"✅ Webhook установлен: {webhook_url}")
        
        # Проверяем информацию о боте
        bot_info = await bot.get_me()
        print(f"🤖 Бот: @{bot_info.username} ({bot_info.first_name})")
        
        # Проверяем webhook
        webhook_info = await bot.get_webhook_info()
        print(f"🔗 Webhook URL: {webhook_info.url}")
        print(f"📊 Ожидающих обновлений: {webhook_info.pending_update_count}")
        
    except Exception as e:
        print(f"❌ Ошибка при настройке webhook: {e}")
        sys.exit(1)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(setup_webhook())
