import React, { useState } from 'react';
import { sendLeadRequest } from '../services/api';

const CarCard = ({ car }) => {
  // Placeholder for missing images
  const placeholder = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80"><rect width="100%" height="100%" fill="%23ccc"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="%23666" font-size="16">Нет фото</text></svg>';

  const [modalOpen, setModalOpen] = useState(false);
  const handleLeadRequest = async () => {
    try {
      await sendLeadRequest(car);
      setModalOpen(true);
    } catch (e) {
      alert('Ошибка отправки заявки: ' + (e.message || e));
    }
  };

  return (
    <div className="car-card">
      <img
        src={car.image || placeholder}
        alt={car.title || 'Без названия'}
        className="car-image"
        onError={(e) => { e.target.onerror = null; e.target.src = placeholder; }}
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
        {modalOpen && (
          <div className="modal-overlay" onClick={() => setModalOpen(false)}>
            <div className="modal-content">
              <p>Мы скоро с вами свяжемся</p>
              <button onClick={() => setModalOpen(false)}>Закрыть</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CarCard;
