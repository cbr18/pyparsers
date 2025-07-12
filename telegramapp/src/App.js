import React, { useEffect, useState } from 'react';
import './App.css';

// Используем относительный путь для API
const API_URL = '';

function App() {
  const [cars, setCars] = useState([]);
  const [loading, setLoading] = useState(true);

  // Заглушка для картинок
  const placeholder = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80"><rect width="100%" height="100%" fill="%23ccc"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="%23666" font-size="16">Нет фото</text></svg>';

  useEffect(() => {
    // Глобальный обработчик ошибок для диагностики
    window.onerror = function (message, source, lineno, colno, error) {
      alert('JS Error: ' + message);
    };
    window.onunhandledrejection = function (e) {
      alert('Promise Error: ' + e.reason);
    };

    fetch(`/cars/che168`)
      .then(res => res.json())
      .then(data => {
        setCars(data.data && Array.isArray(data.data.search_sh_sku_info_list) ? data.data.search_sh_sku_info_list : []);
        setLoading(false);
      });
  }, []);

  if (loading) return <div className="loader">Загрузка...</div>;

  return (
    <div className="car-list">
      {cars.map((car, idx) => (
        <div className="car-card" key={idx}>
          <img
            src={car && car.image ? car.image : placeholder}
            alt={car && car.title ? car.title : 'Без названия'}
            className="car-image"
            onError={e => { e.target.onerror = null; e.target.src = placeholder; }}
          />
          <div className="car-info">
            <h2>{car && car.title ? car.title : 'Без названия'}</h2>
            <p><b>Цена:</b> {car && car.sh_price ? car.sh_price : '—'}</p>
            <p><b>Год:</b> {car && car.car_year ? car.car_year : '—'}</p>
            <p><b>Пробег:</b> {car && car.car_mileage ? car.car_mileage : '—'}</p>
            <p><b>Город:</b> {car && car.car_source_city_name ? car.car_source_city_name : '—'}</p>
            <p><b>Бренд:</b> {car && car.brand_name ? car.brand_name : '—'}</p>
            <p><b>Серия:</b> {car && car.series_name ? car.series_name : '—'}</p>
            <p><b>Модель:</b> {car && car.car_name ? car.car_name : '—'}</p>
            <p><b>Тип источника:</b> {car && car.car_source_type ? car.car_source_type : '—'}</p>
            <p><b>Кол-во владельцев:</b> {car && car.transfer_cnt ? car.transfer_cnt : '—'}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

export default App;
