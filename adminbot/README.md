# Admin Bot

Телеграм бот для администраторов с функциями поиска по базе данных и управления админами.

## Функциональность

- 🔍 **Поиск по UUID** - поиск машин в базе данных по UUID с выводом полной информации
- 👥 **Управление админами** - добавление новых администраторов
- 📋 **Список админов** - просмотр всех администраторов
- 📨 **Уведомления о заявках** - получение уведомлений о заявках с сайта

## Установка и запуск

### Локальная разработка

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Создайте файл `.env` на основе `env.example`:
```bash
cp env.example .env
```

3. Заполните переменные окружения в `.env`:
```env
ADMIN_BOT_TOKEN=your_telegram_bot_token_here
ADMIN_WEBHOOK_URL=https://yourdomain.com/admin-bot
DATAHUB_URL=http://localhost:8080
ADMIN_USERNAME=cbr_18
```

4. Запустите бота:
```bash
python app.py
```

### Docker

1. Соберите образ:
```bash
docker build -t adminbot .
```

2. Запустите контейнер:
```bash
docker run -d \
  --name adminbot \
  --env-file .env \
  -p 8002:8000 \
  adminbot
```

## API Endpoints

### `GET /health`
Проверка работоспособности бота.

### `POST /lead`
Прием заявок от telegramapp и отправка уведомлений всем админам.

**Тело запроса:**
```json
{
  "car": {
    "uuid": "string",
    "title": "string",
    "brand_name": "string",
    "car_name": "string",
    "year": "number",
    "price": "string",
    "city": "string",
    "link": "string"
  },
  "user": "string"
}
```

### `POST /bot`
Webhook для получения обновлений от Telegram.

## Команды бота

- `/start` - Запуск бота и главное меню
- Кнопки в интерфейсе:
  - 🔍 **Поиск по UUID** - поиск машины по UUID
  - 👥 **Управление админами** - добавление новых админов
  - ℹ️ **Список админов** - просмотр всех админов

## Интеграция с telegramapp

Для интеграции с существующим telegramapp необходимо:

1. Обновить функцию `sendLeadRequest` в `telegramapp/src/services/api.js`:
```javascript
export const sendLeadRequest = async (car, user = '') => {
  try {
    const response = await fetch('/admin-lead', {  // Изменить URL
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ car, user })
    });
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error sending lead:', error);
    throw error;
  }
};
```

2. Добавить проксирование в nginx:
```nginx
location /admin-lead {
    proxy_pass http://adminbot_backend/lead;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

## Структура проекта

```
adminbot/
├── app.py              # Основной файл приложения
├── requirements.txt    # Python зависимости
├── Dockerfile         # Docker конфигурация
├── env.example        # Пример переменных окружения
└── README.md          # Документация
```
