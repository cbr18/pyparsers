import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchCarByUUID, createOrder } from '../services/api';
import { getProxiedImageUrl } from '../utils/imageProxy';
import './CarDetails.css';

const CarDetails = () => {
  const { uuid } = useParams();
  const navigate = useNavigate();
  const [car, setCar] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadCar = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetchCarByUUID(uuid);
        setCar(response.data);
      } catch (err) {
        setError('Ошибка загрузки данных о машине');
        console.error('Error loading car:', err);
      } finally {
        setLoading(false);
      }
    };

    if (uuid) {
      loadCar();
    }
  }, [uuid]);

  const placeholder = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="350" height="220"><defs><linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:%23667eea;stop-opacity:0.1" /><stop offset="100%" style="stop-color:%23764ba2;stop-opacity:0.1" /></linearGradient></defs><rect width="100%" height="100%" fill="url(%23grad)"/><g transform="translate(175,110)"><circle cx="0" cy="0" r="30" fill="none" stroke="%23667eea" stroke-width="2" opacity="0.3"/><path d="M-20,-10 L20,-10 M-20,0 L20,0 M-20,10 L20,10" stroke="%23667eea" stroke-width="2" opacity="0.3"/><text x="0" y="35" text-anchor="middle" fill="%23667eea" font-size="14" font-family="Arial, sans-serif" opacity="0.6">Нет фото</text></g></svg>';

  const handleWriteMessage = () => {
    const tg = window.Telegram?.WebApp;
    let username = 'Пользователь';
    
    if (tg?.initDataUnsafe?.user) {
      const user = tg.initDataUnsafe.user;
      username = user.username ? `@${user.username}` : 
                 user.first_name ? user.first_name : 
                 'Пользователь';
    } else if (tg?.initData) {
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
    
    const message = `Здравствуйте, меня интересует данная машина: ${car?.uuid || 'ID не найден'}\n\nПользователь: ${username}`;
    const tgUrl = `https://t.me/cbr_18?text=${encodeURIComponent(message)}`;
    window.open(tgUrl, '_blank');
  };

  const handleLeadRequest = () => {
    const tg = window.Telegram?.WebApp;
    alert('Заявка отправлена');

    let username = 'Пользователь сайта';

    let chatId = null;

    if (tg?.initDataUnsafe?.user) {
      const user = tg.initDataUnsafe.user;
      username = user.username ? `@${user.username}` : 
                 user.first_name ? user.first_name : 
                 'Пользователь сайта';
      chatId = user.id ?? null;
    } else if (tg?.initData) {
      try {
        const params = new URLSearchParams(tg.initData);
        const userParam = params.get('user');
        if (userParam) {
          const user = JSON.parse(decodeURIComponent(userParam));
          username = user.username ? `@${user.username}` : 
                     user.first_name ? user.first_name : 
                     'Пользователь сайта';
          chatId = user.id ?? null;
        }
      } catch (e) {
        console.log('Could not parse user data:', e);
      }
    }

    createOrder({
      carUuid: car?.uuid || uuid,
      clientTelegramId: username,
      clientChatId: chatId,
      tgId: username,
      car
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(`HTTP error! Status: ${response.status}`);
        }

        const title = car?.title || car?.car_name || 'Без названия';
        const brand = car?.brand_name || car?.brand || '';
        const model = car?.car_name || car?.model || '';
        const image = car?.image || null;

        tg?.sendData?.(JSON.stringify({
          type: 'order_success',
          car: {
            uuid: car?.uuid || uuid || '',
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

  if (loading) {
    return (
      <div className="car-details-container">
        <div className="loader-container">
          <div className="loader">Загрузка информации о машине...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="car-details-container">
        <div className="error-message">{error}</div>
        <button className="back-button" onClick={() => navigate('/')}>
          Вернуться назад
        </button>
      </div>
    );
  }

  if (!car) {
    return (
      <div className="car-details-container">
        <div className="error-message">Машина не найдена</div>
        <button className="back-button" onClick={() => navigate('/')}>
          Вернуться назад
        </button>
      </div>
    );
  }

  const proxiedUrl = getProxiedImageUrl(car.image);

  return (
    <div className="car-details-container">
      <div className="car-details-header">
        <button className="back-button" onClick={() => navigate('/')}>
          ← Назад
        </button>
        <h1>Детали автомобиля</h1>
      </div>

      <div className="car-details-content">
        <div className="car-details-image">
          <img
            src={proxiedUrl || placeholder}
            alt={car.title || 'Без названия'}
            onError={(e) => { 
              e.target.onerror = null; 
              e.target.src = placeholder; 
            }}
          />
        </div>

        <div className="car-details-info">
          <h2>{car.title || 'Без названия'}</h2>
          
          <div className="car-details-section">
            <h3>Основная информация</h3>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">Цена:</span>
                <span className="info-value price">{car.price || '—'}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Год:</span>
                <span className="info-value">{car.year || '—'}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Пробег:</span>
                <span className="info-value">{car.mileage ? `${car.mileage} км` : '—'}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Город:</span>
                <span className="info-value">{car.city || '—'}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Источник:</span>
                <span className="info-value">{car.source || '—'}</span>
              </div>
            </div>
          </div>

          <div className="car-details-section">
            <h3>Марка и модель</h3>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">Бренд:</span>
                <span className="info-value">{car.brand_name || '—'}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Серия:</span>
                <span className="info-value">{car.series_name || '—'}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Модель:</span>
                <span className="info-value">{car.car_name || '—'}</span>
              </div>
            </div>
          </div>

          {(car.color || car.transmission || car.fuel_type || car.engine_volume || 
            car.body_type || car.drive_type || car.condition) && (
            <div className="car-details-section">
              <h3>Технические характеристики</h3>
              <div className="info-grid">
                {car.color && (
                  <div className="info-item">
                    <span className="info-label">Цвет:</span>
                    <span className="info-value">{car.color}</span>
                  </div>
                )}
                {car.transmission && (
                  <div className="info-item">
                    <span className="info-label">КПП:</span>
                    <span className="info-value">{car.transmission}</span>
                  </div>
                )}
                {car.fuel_type && (
                  <div className="info-item">
                    <span className="info-label">Топливо:</span>
                    <span className="info-value">{car.fuel_type}</span>
                  </div>
                )}
                {car.engine_volume && (
                  <div className="info-item">
                    <span className="info-label">Объем двигателя:</span>
                    <span className="info-value">{car.engine_volume}</span>
                  </div>
                )}
                {car.body_type && (
                  <div className="info-item">
                    <span className="info-label">Тип кузова:</span>
                    <span className="info-value">{car.body_type}</span>
                  </div>
                )}
                {car.drive_type && (
                  <div className="info-item">
                    <span className="info-label">Привод:</span>
                    <span className="info-value">{car.drive_type}</span>
                  </div>
                )}
                {car.condition && (
                  <div className="info-item">
                    <span className="info-label">Состояние:</span>
                    <span className="info-value">{car.condition}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {car.description && (
            <div className="car-details-section">
              <h3>Описание</h3>
              <p className="description">{car.description}</p>
            </div>
          )}

          {car.link && (
            <div className="car-details-section">
              <a href={car.link} target="_blank" rel="noopener noreferrer" className="external-link">
                Перейти к источнику →
              </a>
            </div>
          )}

          <div className="car-details-buttons">
            <button className="lead-btn" onClick={handleLeadRequest}>
              Оставить заявку
            </button>
            <button className="write-btn" onClick={handleWriteMessage}>
              Написать
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CarDetails;
