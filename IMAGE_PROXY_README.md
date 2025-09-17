# Image Proxy Configuration

## Описание

Настроен nginx прокси для обхода CORS ограничений при загрузке внешних изображений в React приложении.

## Как это работает

1. **Nginx прокси** (`/proxy-image/`) - перехватывает запросы к внешним изображениям
2. **React утилита** (`imageProxy.js`) - автоматически преобразует внешние URL в прокси-URL
3. **Автоматическое применение** - компонент `CarCard` использует прокси для всех внешних изображений

## Конфигурация nginx

```nginx
location /proxy-image/ {
    # Удаляем префикс /proxy-image/ и получаем оригинальный URL
    rewrite ^/proxy-image/(.*)$ $1 break;
    
    # Проксируем запрос к внешнему серверу
    proxy_pass $1;
    
    # Убираем проблемные заголовки
    proxy_set_header Host "";
    proxy_set_header Referer "";
    proxy_set_header Origin "";
    
    # Кэшируем изображения на 1 час
    proxy_cache static_cache;
    proxy_cache_valid 200 1h;
}
```

## Использование в React

```javascript
import { getProxiedImageUrl } from '../utils/imageProxy';

// Автоматическое преобразование URL
const imageUrl = getProxiedImageUrl(car.image);

// В компоненте
<img src={imageUrl} alt="Car" />
```

## Поддерживаемые URL

- ✅ Внешние HTTP/HTTPS URL (autoimg.cn, etc.)
- ✅ Относительные URL (остаются без изменений)
- ✅ Data URL (base64 изображения)
- ✅ URL с того же домена (остаются без изменений)

## Тестирование

```bash
# Запустить тестовый скрипт
./test-image-proxy.sh

# Или вручную протестировать URL
curl -I "http://localhost/proxy-image/https%3A//autoimg.cn/example.jpg"
```

## Безопасность

- Ограничение скорости запросов (rate limiting)
- Валидация URL параметров
- Graceful error handling с fallback изображением
- Кэширование для снижения нагрузки

## Мониторинг

- Логи nginx: `./logs/nginx/access.log`
- Статус кэша: заголовок `X-Cache-Status`
- Ошибки: fallback SVG изображение
