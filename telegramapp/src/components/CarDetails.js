import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchCarByUUID, createOrder } from '../services/api';
import ImageCarousel from './ImageCarousel';
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

  return (
    <div className="car-details-container">
      <div className="car-details-header">
        <button className="back-button" onClick={() => navigate('/')}>
          ← Назад
        </button>
        <h1>Детали автомобиля</h1>
      </div>

      <div className="car-details-content">
        {/* Карусель картинок */}
        <ImageCarousel 
          images={car.image_gallery} 
          mainImage={car.image}
          alt={car.title || 'Автомобиль'}
        />

        <div className="car-details-info">
          <h2>{car.title || car.car_name || 'Без названия'}</h2>
          
          <div className="car-details-section">
            <h3>Основная информация</h3>
            <div className="info-grid">
              {car.rub_price && car.rub_price > 0 && (
                <div className="info-item">
                  <span className="info-label">Цена:</span>
                  <span className="info-value price">{new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(car.rub_price)}</span>
                </div>
              )}
              <div className="info-item">
                <span className="info-label">Год выпуска:</span>
                <span className="info-value">{car.year || '—'}</span>
              </div>
              {car.mileage > 0 && (
                <div className="info-item">
                  <span className="info-label">Пробег:</span>
                  <span className="info-value">{car.mileage.toLocaleString('ru-RU')} км</span>
                </div>
              )}
              {car.city && (
                <div className="info-item">
                  <span className="info-label">Город:</span>
                  <span className="info-value">{car.city}</span>
                </div>
              )}
              {car.source && (
                <div className="info-item">
                  <span className="info-label">Источник:</span>
                  <span className="info-value">{car.source === 'dongchedi' ? 'Dongchedi' : car.source === 'che168' ? 'Che168' : car.source}</span>
                </div>
              )}
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

          {/* Технические характеристики */}
          <div className="car-details-section">
            <h3>Технические характеристики</h3>
            <div className="info-grid">
              {car.engine_volume && (
                <div className="info-item">
                  <span className="info-label">Объем двигателя:</span>
                  <span className="info-value">{car.engine_volume} л</span>
                </div>
              )}
              {car.power && (
                <div className="info-item">
                  <span className="info-label">Мощность:</span>
                  <span className="info-value">{car.power} л.с.</span>
                </div>
              )}
              {car.torque && (
                <div className="info-item">
                  <span className="info-label">Крутящий момент:</span>
                  <span className="info-value">{car.torque} Н⋅м</span>
                </div>
              )}
              {car.transmission_type && (
                <div className="info-item">
                  <span className="info-label">КПП:</span>
                  <span className="info-value">{car.transmission_type}</span>
                </div>
              )}
              {car.transmission && !car.transmission_type && (
                <div className="info-item">
                  <span className="info-label">КПП:</span>
                  <span className="info-value">{car.transmission}</span>
                </div>
              )}
              {car.drive_type && (
                <div className="info-item">
                  <span className="info-label">Привод:</span>
                  <span className="info-value">{car.drive_type}</span>
                </div>
              )}
              {car.fuel_type && (
                <div className="info-item">
                  <span className="info-label">Тип топлива:</span>
                  <span className="info-value">{car.fuel_type}</span>
                </div>
              )}
              {car.fuel_consumption && (
                <div className="info-item">
                  <span className="info-label">Расход топлива:</span>
                  <span className="info-value">{car.fuel_consumption} л/100км</span>
                </div>
              )}
              {car.acceleration && (
                <div className="info-item">
                  <span className="info-label">Разгон 0-100:</span>
                  <span className="info-value">{car.acceleration} сек</span>
                </div>
              )}
              {car.max_speed && (
                <div className="info-item">
                  <span className="info-label">Макс. скорость:</span>
                  <span className="info-value">{car.max_speed} км/ч</span>
                </div>
              )}
            </div>
          </div>

          {/* Размеры и вес */}
          {(car.length || car.width || car.height || car.wheelbase || car.curb_weight) && (
            <div className="car-details-section">
              <h3>Размеры и вес</h3>
              <div className="info-grid">
                {car.length && (
                  <div className="info-item">
                    <span className="info-label">Длина:</span>
                    <span className="info-value">{car.length} мм</span>
                  </div>
                )}
                {car.width && (
                  <div className="info-item">
                    <span className="info-label">Ширина:</span>
                    <span className="info-value">{car.width} мм</span>
                  </div>
                )}
                {car.height && (
                  <div className="info-item">
                    <span className="info-label">Высота:</span>
                    <span className="info-value">{car.height} мм</span>
                  </div>
                )}
                {car.wheelbase && (
                  <div className="info-item">
                    <span className="info-label">Колесная база:</span>
                    <span className="info-value">{car.wheelbase} мм</span>
                  </div>
                )}
                {car.curb_weight && (
                  <div className="info-item">
                    <span className="info-label">Снаряженная масса:</span>
                    <span className="info-value">{car.curb_weight} кг</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Кузов и экстерьер */}
          {(car.body_type || car.color || car.exterior_color || car.door_count || car.seat_count) && (
            <div className="car-details-section">
              <h3>Кузов и экстерьер</h3>
              <div className="info-grid">
                {car.body_type && (
                  <div className="info-item">
                    <span className="info-label">Тип кузова:</span>
                    <span className="info-value">{car.body_type}</span>
                  </div>
                )}
                {(car.exterior_color || car.color) && (
                  <div className="info-item">
                    <span className="info-label">Цвет:</span>
                    <span className="info-value">{car.exterior_color || car.color}</span>
                  </div>
                )}
                {car.door_count && (
                  <div className="info-item">
                    <span className="info-label">Количество дверей:</span>
                    <span className="info-value">{car.door_count}</span>
                  </div>
                )}
                {car.seat_count && (
                  <div className="info-item">
                    <span className="info-label">Количество мест:</span>
                    <span className="info-value">{car.seat_count}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Дополнительная информация */}
          {(car.condition || car.owner_count || car.emission_standard || car.certification) && (
            <div className="car-details-section">
              <h3>Дополнительная информация</h3>
              <div className="info-grid">
                {car.condition && (
                  <div className="info-item">
                    <span className="info-label">Состояние:</span>
                    <span className="info-value">{car.condition}</span>
                  </div>
                )}
                {car.owner_count > 0 && (
                  <div className="info-item">
                    <span className="info-label">Владельцев:</span>
                    <span className="info-value">{car.owner_count}</span>
                  </div>
                )}
                {car.emission_standard && (
                  <div className="info-item">
                    <span className="info-label">Экостандарт:</span>
                    <span className="info-value">{car.emission_standard}</span>
                  </div>
                )}
                {car.certification && (
                  <div className="info-item">
                    <span className="info-label">Сертификация:</span>
                    <span className="info-value">{car.certification}</span>
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
