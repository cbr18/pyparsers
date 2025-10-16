import React, { useState } from 'react';
import { sendLeadRequest } from '../services/api';
import { getProxiedImageUrl, shouldUseProxy } from '../utils/imageProxy';

const CarCard = ({ car }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [buttonState, setButtonState] = useState('normal'); // normal, success, error
  // Beautiful placeholder for missing images
  const placeholder = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="350" height="220"><defs><linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:%23667eea;stop-opacity:0.1" /><stop offset="100%" style="stop-color:%23764ba2;stop-opacity:0.1" /></linearGradient></defs><rect width="100%" height="100%" fill="url(%23grad)"/><g transform="translate(175,110)"><circle cx="0" cy="0" r="30" fill="none" stroke="%23667eea" stroke-width="2" opacity="0.3"/><path d="M-20,-10 L20,-10 M-20,0 L20,0 M-20,10 L20,10" stroke="%23667eea" stroke-width="2" opacity="0.3"/><text x="0" y="35" text-anchor="middle" fill="%23667eea" font-size="14" font-family="Arial, sans-serif" opacity="0.6">Нет фото</text></g></svg>';

  const handleLeadRequest = async () => {
    if (isLoading) return;
    
    setIsLoading(true);
    setButtonState('normal');
    
    try {
      // Подготовим сообщение с ссылкой на машину
      const carUrl = car.link || '';
      const message = `Здравствуйте, меня интересует данная машина: ${carUrl}`;

      // Скопируем текст в буфер обмена на случай, если Telegram проигнорирует автотекст
      try { await navigator.clipboard.writeText(message); } catch (_) {}

      // Пытаемся открыть Telegram с предзаполненным сообщением
      // Прямой deep-link с текстом может игнорироваться в Mini App, поэтому используем web-share, где возможно
      const tgDeepLink = `tg://resolve?domain=cbr_18&text=${encodeURIComponent(message)}`;

      // Детекция платформы для корректных веб-фолбэков
      const ua = (typeof navigator !== 'undefined' && navigator.userAgent) ? navigator.userAgent : '';
      const isMobile = /Android|iPhone|iPad|iPod/i.test(ua);

      // Веб-варианты:
      // - Desktop/Web: можно открыть чат с текстом через web Telegram
      const tgWebDesktopChat = `https://t.me/cbr_18?text=${encodeURIComponent(message)}`;
      // - Mobile: официальный способ с текстом — общий share, пользователь выберет контакт
      const tgWebShare = `https://t.me/share/url?url=${encodeURIComponent(carUrl)}&text=${encodeURIComponent(message)}`;

      // Параллельно тихо отправим лид на бэкенд (не блокируем UX)
      try { 
        await sendLeadRequest(car);
        setButtonState('success');
        setTimeout(() => setButtonState('normal'), 2000);
      } catch (_) {
        setButtonState('error');
        setTimeout(() => setButtonState('normal'), 2000);
      }

      // Если мы внутри Telegram Mini App — используем официальный API
      const webApp = (typeof window !== 'undefined' && window.Telegram && window.Telegram.WebApp) ? window.Telegram.WebApp : null;
      // 1) Попробуем инлайн-режим: откроет выбор чата с предзаполненным запросом
      if (webApp && typeof webApp.switchInlineQuery === 'function') {
        try {
          webApp.switchInlineQuery(message, true);
          return;
        } catch (_) {}
      }
      const openUrl = (url) => {
        if (webApp && typeof webApp.openTelegramLink === 'function') {
          webApp.openTelegramLink(url);
        } else {
          window.location.href = url;
        }
      };

      // В Mini App лучше сразу использовать share-URL — он корректно подставляет текст (где поддерживается)
      if (webApp) {
        openUrl(isMobile ? tgWebShare : tgWebDesktopChat);
        return;
      }

      // Пробуем открыть app-ссылку; если не сработает, дадим веб-фолбэк
      const fallbackTimer = setTimeout(() => {
        // Если deep link не сработал, используем лучший веб‑вариант для текущей платформы
        openUrl(isMobile ? tgWebShare : tgWebDesktopChat);
      }, 800);

      try {
        openUrl(tgDeepLink);
        // Если приложение перехватило протокол, переход произойдет и таймер можно игнорировать
        // Отменить таймер корректно нельзя без детекции, оставим как есть
      } catch (_) {
        clearTimeout(fallbackTimer);
        openUrl(isMobile ? tgWebShare : tgWebDesktopChat);
      }
    } catch (error) {
      console.error('Error in handleLeadRequest:', error);
      setButtonState('error');
      setTimeout(() => setButtonState('normal'), 2000);
    } finally {
      setIsLoading(false);
    }
  };

  // Get proxied image URL
  const proxiedUrl = getProxiedImageUrl(car.image);

  return (
    <div className="car-card">
      <img
        src={proxiedUrl || placeholder}
        alt={car.title || 'Без названия'}
        className="car-image"
        onError={(e) => { 
          e.target.onerror = null; 
          e.target.src = placeholder; 
        }}
      />
      <div className="car-info">
        <h2>{car.title || 'Без названия'}</h2>
        <p><b>Цена:</b> <span>{car.price || '—'}</span></p>
        <p><b>Год:</b> <span>{car.year || '—'}</span></p>
        <p><b>Пробег:</b> <span>{car.mileage ? `${car.mileage} км` : '—'}</span></p>
        <p><b>Город:</b> <span>{car.city || '—'}</span></p>
        <p><b>Бренд:</b> <span>{car.brand_name || '—'}</span></p>
        <p><b>Серия:</b> <span>{car.series_name || '—'}</span></p>
        <p><b>Модель:</b> <span>{car.car_name || '—'}</span></p>
        <button 
          className={`lead-btn ${buttonState}`} 
          onClick={handleLeadRequest}
          disabled={isLoading}
        >
          <span>
            {isLoading ? 'Отправка...' : 
             buttonState === 'success' ? '✓ Отправлено' :
             buttonState === 'error' ? '✗ Ошибка' :
             'Оставить заявку'}
          </span>
        </button>
      </div>
    </div>
  );
};

export default CarCard;
