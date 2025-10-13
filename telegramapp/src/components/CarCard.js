import React from 'react';
import { sendLeadRequest } from '../services/api';
import { getProxiedImageUrl, shouldUseProxy } from '../utils/imageProxy';

const CarCard = ({ car }) => {
  // Placeholder for missing images
  const placeholder = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80"><rect width="100%" height="100%" fill="%23ccc"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="%23666" font-size="16">Нет фото</text></svg>';

  const handleLeadRequest = async () => {
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
    try { sendLeadRequest(car).catch(() => {}); } catch (_) {}

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
        <p><b>Цена:</b> {car.price || '—'}</p>
        <p><b>Год:</b> {car.year || '—'}</p>
        <p><b>Пробег:</b> {car.mileage || '—'} км</p>
        <p><b>Город:</b> {car.city || '—'}</p>
        <p><b>Бренд:</b> {car.brand_name || '—'}</p>
        <p><b>Серия:</b> {car.series_name || '—'}</p>
        <p><b>Модель:</b> {car.car_name || '—'}</p>
        <button className="lead-btn" onClick={handleLeadRequest}>Оставить заявку</button>
        {/* Убрали модалку подтверждения */}
      </div>
    </div>
  );
};

export default CarCard;
