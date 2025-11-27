import React from 'react';
import { useNavigate } from 'react-router-dom';
import { getProxiedImageUrl } from '../utils/imageProxy';
import { createOrder } from '../services/api';

const CarCard = ({ car }) => {
  const navigate = useNavigate();
  
  // Beautiful placeholder for missing images
  const placeholder = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="350" height="220"><defs><linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:%23ff5f6d;stop-opacity:0.1" /><stop offset="100%" style="stop-color:%23ffc371;stop-opacity:0.1" /></linearGradient></defs><rect width="100%" height="100%" fill="url(%23grad)"/><g transform="translate(175,110)"><circle cx="0" cy="0" r="30" fill="none" stroke="%23ff5f6d" stroke-width="2" opacity="0.3"/><path d="M-20,-10 L20,-10 M-20,0 L20,0 M-20,10 L20,10" stroke="%23ff5f6d" stroke-width="2" opacity="0.3"/><text x="0" y="35" text-anchor="middle" fill="%23ff5f6d" font-size="14" font-family="Arial, sans-serif" opacity="0.6">Нет фото</text></g></svg>';

  const handleCardClick = () => {
    navigate(`/car/${car.uuid || car.id}`);
  };

  const handleWriteMessage = (e) => {
    e.stopPropagation(); // Предотвращаем всплытие события
    // Получаем данные пользователя из Telegram WebApp
    const tg = window.Telegram?.WebApp;
    let username = 'Пользователь';
    
    if (tg?.initDataUnsafe?.user) {
      const user = tg.initDataUnsafe.user;
      username = user.username ? `@${user.username}` : 
                 user.first_name ? user.first_name : 
                 'Пользователь';
    } else if (tg?.initData) {
      // Альтернативный способ через initData
      try {
        const params = new URLSearchParams(tg.initData);
        const userParam = params.get('user');
        if (userParam) {
          const user = JSON.parse(decodeURIComponent(userParam));
          username = user.username ? `@${user.username}` : 
                     user.first_name ? user.first_name : 
                     'Пользователь';
        }
      } catch (e) {
        console.log('Could not parse user data:', e);
      }
    }
    
    // Подготовим сообщение с UUID машины, названием, ссылкой и username
    const carTitle = car.title || car.car_name || 'Без названия';
    const carUuid = car.uuid || car.id || 'ID не найден';
    const carLink = car.link || '';
    
    let message = `Здравствуйте, меня интересует данная машина:\n\nНазвание: ${carTitle}\nUUID: ${carUuid}`;
    
    if (carLink) {
      message += `\nСсылка: ${carLink}`;
    }
    
    message += `\n\nПользователь: ${username}`;
    
    // Простая ссылка на Telegram с предзаполненным текстом
    const tgUrl = `https://t.me/cbr_18?text=${encodeURIComponent(message)}`;
    
    // Открываем ссылку
    window.open(tgUrl, '_blank');
  };

const handleLeadRequest = (e) => {
  e.stopPropagation(); // Предотвращаем всплытие события
  const tg = window.Telegram?.WebApp;
  alert('Заявка отправлена');

  let username = 'Пользователь сайта';
  let chatId = null;

  if (tg?.initDataUnsafe?.user) {
    const user = tg.initDataUnsafe.user;
    username = user.username
      ? `@${user.username}`
      : user.first_name
      ? user.first_name
      : 'Пользователь сайта';
    chatId = user.id ?? null;
  } else if (tg?.initData) {
    try {
      const params = new URLSearchParams(tg.initData);
      const userParam = params.get('user');
      if (userParam) {
        const user = JSON.parse(decodeURIComponent(userParam));
        username = user.username
          ? `@${user.username}`
          : user.first_name
          ? user.first_name
          : 'Пользователь сайта';
        chatId = user.id ?? null;
      }
    } catch (err) {
      console.log('Could not parse user data:', err);
    }
  }

  createOrder({
    carUuid: car?.uuid || car?.id,
    clientTelegramId: username,
    clientChatId: chatId,
    tgId: username,
    car
  })
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const title = car?.title || car?.car_name || car?.car_model || 'Без названия';
      const brand = car?.brand_name || car?.brand || '';
      const model = car?.car_name || car?.model || '';
      const image = car?.image || null;

      tg?.sendData?.(JSON.stringify({
        type: 'order_success',
        car: {
          uuid: car?.uuid || car?.id || '',
          title,
          brand,
          model,
          image
        }
      }));
    })
    .catch((error) => {
      console.error('Error sending lead request:', error);
      tg?.showPopup?.({
        title: 'Ошибка',
        message: 'Не удалось отправить заявку. Попробуйте позже.',
        buttons: [{ type: 'ok', text: 'Ок' }]
      });
    });
};


  // Get proxied image URL
  const proxiedUrl = getProxiedImageUrl(car.image);

  const displayPrice = car?.final_price && car.final_price > 0 ? car.final_price : car?.rub_price;

  return (
    <div className="car-card" onClick={handleCardClick} style={{ cursor: 'pointer' }}>
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
        <h2>{car.title || car.car_name || 'Без названия'}</h2>
        {displayPrice && displayPrice > 0 && (
          <p className="price-highlight"><b>Цена:</b> <span>{new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(displayPrice)}</span></p>
        )}
        <p><b>Год:</b> <span>{car.year || '—'}</span></p>
        {car.mileage > 0 && (
          <p><b>Пробег:</b> <span>{car.mileage.toLocaleString('ru-RU')} км</span></p>
        )}
        {car.city && (
          <p><b>Город:</b> <span>{car.city}</span></p>
        )}
        <p><b>Бренд:</b> <span>{car.brand_name || '—'}</span></p>
        {car.series_name && (
          <p><b>Серия:</b> <span>{car.series_name}</span></p>
        )}
        {car.car_name && car.title !== car.car_name && (
          <p><b>Модель:</b> <span>{car.car_name}</span></p>
        )}
        <div className="car-buttons">
          <button className="lead-btn" onClick={handleLeadRequest}>
            <span>Оставить заявку</span>
          </button>
          <button 
            className="write-btn" 
            onClick={handleWriteMessage}
          >
            <span>Написать</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default CarCard;

