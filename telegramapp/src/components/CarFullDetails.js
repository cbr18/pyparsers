import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchCarByUUID } from '../services/api';
import './CarFullDetails.css';

const CarFullDetails = () => {
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

  const handleBack = () => {
    navigate(-1);
  };

  if (loading) {
    return (
      <div className="car-full-details-container">
        <div className="loader-container">
          <div className="loader">Загрузка подробной информации...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="car-full-details-container">
        <div className="error-message">{error}</div>
        <button className="back-button" onClick={handleBack}>
          Вернуться назад
        </button>
      </div>
    );
  }

  if (!car) {
    return (
      <div className="car-full-details-container">
        <div className="error-message">Машина не найдена</div>
        <button className="back-button" onClick={handleBack}>
          Вернуться назад
        </button>
      </div>
    );
  }

  // Функция для форматирования значений
  const formatValue = (value, key = '') => {
    if (value === null || value === undefined || value === '') {
      return '—';
    }
    if (typeof value === 'boolean') {
      return value ? 'Да' : 'Нет';
    }
    if (typeof value === 'number') {
      // Показываем 0 для некоторых полей (mileage, year, owner_count, view_count, favorite_count)
      if (value === 0) {
        const showZeroFields = ['mileage', 'year', 'owner_count', 'view_count', 'favorite_count', 'image_count'];
        return showZeroFields.includes(key) ? '0' : '—';
      }
      return value.toLocaleString('ru-RU');
    }
    // Для строк проверяем, не пустая ли она после trim
    if (typeof value === 'string' && value.trim() === '') {
      return '—';
    }
    return String(value);
  };

  // Функция для получения читаемого названия поля
  const getFieldLabel = (key) => {
    const labels = {
      // Основная информация
      source: 'Источник',
      title: 'Название',
      car_name: 'Модель',
      year: 'Год выпуска',
      mileage: 'Пробег (км)',
      price: 'Цена (оригинал)',
      rub_price: 'Цена в рублях',
      final_price: 'Финальная цена',
      image: 'Главное изображение',
      link: 'Ссылка на источник',
      brand_name: 'Бренд',
      series_name: 'Серия',
      city: 'Город',
      tags: 'Теги',
      tags_v2: 'Теги (v2)',
      description: 'Описание',
      
      // Цвета
      color: 'Цвет',
      exterior_color: 'Цвет кузова',
      interior_color: 'Цвет салона',
      
      // Трансмиссия
      transmission: 'Коробка передач',
      transmission_type: 'Тип КПП',
      gear_count: 'Количество передач',
      differential_type: 'Тип дифференциала',
      
      // Двигатель
      fuel_type: 'Тип топлива',
      engine_volume: 'Объем двигателя (л)',
      engine_volume_ml: 'Объем двигателя (мл)',
      engine_type: 'Тип двигателя',
      engine_code: 'Код двигателя',
      cylinder_count: 'Количество цилиндров',
      valve_count: 'Количество клапанов',
      compression_ratio: 'Степень сжатия',
      turbo_type: 'Тип турбонаддува',
      
      // Электрические характеристики
      battery_capacity: 'Емкость батареи (кВт·ч)',
      electric_range: 'Запас хода (км)',
      charging_time: 'Время зарядки',
      fast_charge_time: 'Время быстрой зарядки',
      charge_port_type: 'Тип зарядного порта',
      
      // Технические характеристики
      power: 'Мощность',
      torque: 'Крутящий момент (Н·м)',
      acceleration: 'Разгон 0-100 (сек)',
      max_speed: 'Максимальная скорость (км/ч)',
      fuel_consumption: 'Расход топлива (л/100км)',
      emission_standard: 'Экологический стандарт',
      
      // Размеры и вес
      length: 'Длина (мм)',
      width: 'Ширина (мм)',
      height: 'Высота (мм)',
      wheelbase: 'Колесная база (мм)',
      curb_weight: 'Снаряженная масса (кг)',
      gross_weight: 'Полная масса (кг)',
      trunk_volume: 'Объем багажника',
      fuel_tank_volume: 'Объем топливного бака',
      
      // Кузов
      body_type: 'Тип кузова',
      door_count: 'Количество дверей',
      seat_count: 'Количество мест',
      
      // Подвеска и тормоза
      front_suspension: 'Передняя подвеска',
      rear_suspension: 'Задняя подвеска',
      front_brakes: 'Передние тормоза',
      rear_brakes: 'Задние тормоза',
      brake_system: 'Тормозная система',
      
      // Колеса и шины
      wheel_size: 'Размер колес',
      tire_size: 'Размер шин',
      wheel_type: 'Тип колес',
      tire_type: 'Тип шин',
      
      // Безопасность
      airbag_count: 'Количество подушек безопасности',
      abs: 'АБС',
      esp: 'ESP',
      tcs: 'TCS',
      hill_assist: 'Помощь при трогании на подъеме',
      blind_spot_monitor: 'Мониторинг слепых зон',
      lane_departure: 'Система предупреждения о покидании полосы',
      
      // Комфорт
      air_conditioning: 'Кондиционер',
      climate_control: 'Климат-контроль',
      seat_heating: 'Подогрев сидений',
      seat_ventilation: 'Вентиляция сидений',
      seat_massage: 'Массаж сидений',
      steering_wheel_heating: 'Подогрев руля',
      
      // Мультимедиа
      navigation: 'Навигация',
      audio_system: 'Аудиосистема',
      speakers_count: 'Количество динамиков',
      bluetooth: 'Bluetooth',
      usb: 'USB',
      aux: 'AUX',
      
      // Освещение
      headlight_type: 'Тип фар',
      fog_lights: 'Противотуманные фары',
      led_lights: 'LED освещение',
      daytime_running: 'Дневные ходовые огни',
      
      // История
      first_registration_time: 'Дата первой регистрации',
      owner_count: 'Количество владельцев',
      accident_history: 'История ДТП',
      service_history: 'История обслуживания',
      warranty_info: 'Информация о гарантии',
      inspection_date: 'Дата техосмотра',
      insurance_info: 'Информация о страховке',
      
      // Дополнительно
      condition: 'Состояние',
      upholstery: 'Обивка салона',
      sunroof: 'Люк',
      panoramic_roof: 'Панорамная крыша',
      view_count: 'Количество просмотров',
      favorite_count: 'Количество добавлений в избранное',
      contact_info: 'Контактная информация',
      dealer_info: 'Информация о дилере',
      certification: 'Сертификация',
      
      // Изображения
      image_gallery: 'Галерея изображений',
      image_count: 'Количество изображений',
      
      // Таможенные сборы
      recycling_fee: 'Утильсбор',
      customs_duty: 'Таможенная пошлина',
      customs_fee: 'Таможенный сбор',
      
      // Привод
      drive_type: 'Привод',
    };

    return labels[key] || key;
  };

  // Поля, которые нужно исключить
  const excludedFields = [
    'uuid', 'car_id', 'sku_id', 'shop_id', 'brand_id', 'series_id', 
    'mybrand_id', 'car_source_city_name', 'created_at', 'updated_at',
    'has_details', 'last_detail_update', 'failed_enhancement_attempts',
    'is_available', 'sort_number'
  ];

  // Получаем все поля и фильтруем
  const fields = Object.keys(car)
    .filter(key => !excludedFields.includes(key))
    .map(key => ({
      key,
      label: getFieldLabel(key),
      value: car[key]
    }));

  // Группируем поля по категориям для лучшей организации
  const groupedFields = {
    'Основная информация': ['source', 'title', 'car_name', 'year', 'mileage', 'price', 'rub_price', 'final_price', 'city', 'brand_name', 'series_name', 'link', 'description'],
    'Цвета': ['color', 'exterior_color', 'interior_color'],
    'Двигатель': ['engine_volume', 'engine_volume_ml', 'engine_type', 'engine_code', 'cylinder_count', 'valve_count', 'compression_ratio', 'turbo_type', 'power', 'torque'],
    'Трансмиссия и привод': ['transmission', 'transmission_type', 'gear_count', 'differential_type', 'drive_type'],
    'Электрические характеристики': ['battery_capacity', 'electric_range', 'charging_time', 'fast_charge_time', 'charge_port_type'],
    'Технические характеристики': ['fuel_type', 'fuel_consumption', 'acceleration', 'max_speed', 'emission_standard'],
    'Размеры и вес': ['length', 'width', 'height', 'wheelbase', 'curb_weight', 'gross_weight', 'trunk_volume', 'fuel_tank_volume'],
    'Кузов': ['body_type', 'door_count', 'seat_count'],
    'Подвеска и тормоза': ['front_suspension', 'rear_suspension', 'front_brakes', 'rear_brakes', 'brake_system'],
    'Колеса и шины': ['wheel_size', 'tire_size', 'wheel_type', 'tire_type'],
    'Безопасность': ['airbag_count', 'abs', 'esp', 'tcs', 'hill_assist', 'blind_spot_monitor', 'lane_departure'],
    'Комфорт': ['air_conditioning', 'climate_control', 'seat_heating', 'seat_ventilation', 'seat_massage', 'steering_wheel_heating'],
    'Мультимедиа': ['navigation', 'audio_system', 'speakers_count', 'bluetooth', 'usb', 'aux'],
    'Освещение': ['headlight_type', 'fog_lights', 'led_lights', 'daytime_running'],
    'История и состояние': ['first_registration_time', 'owner_count', 'condition', 'accident_history', 'service_history', 'warranty_info', 'inspection_date', 'insurance_info'],
    'Дополнительно': ['upholstery', 'sunroof', 'panoramic_roof', 'certification', 'contact_info', 'dealer_info'],
    'Метаданные': ['view_count', 'favorite_count', 'tags', 'tags_v2'],
    'Изображения': ['image', 'image_gallery', 'image_count'],
    'Таможенные сборы': ['recycling_fee', 'customs_duty', 'customs_fee']
  };

  // Создаем группы полей
  const categorizedFields = {};
  fields.forEach(field => {
    let category = 'Прочее';
    for (const [catName, catFields] of Object.entries(groupedFields)) {
      if (catFields.includes(field.key)) {
        category = catName;
        break;
      }
    }
    if (!categorizedFields[category]) {
      categorizedFields[category] = [];
    }
    categorizedFields[category].push(field);
  });

  return (
    <div className="car-full-details-container">
      <div className="car-full-details-header">
        <button className="back-button" onClick={handleBack}>
          ← Назад
        </button>
        <h1>Подробная информация</h1>
      </div>

      <div className="car-full-details-content">
        <h2 className="car-title">{car.title || car.car_name || 'Без названия'}</h2>

        {Object.keys(categorizedFields).sort().map(category => (
          categorizedFields[category].length > 0 && (
            <div key={category} className="details-section">
              <h3 className="section-title">{category}</h3>
              <table className="details-table">
                <tbody>
                  {categorizedFields[category].map(field => (
                    <tr key={field.key}>
                      <td className="field-label">{field.label}</td>
                      <td className="field-value">
                        {field.key === 'image' || field.key === 'image_gallery' ? (
                          <span className="image-url">{formatValue(field.value, field.key)}</span>
                        ) : field.key === 'link' ? (
                          field.value ? (
                            <a href={field.value} target="_blank" rel="noopener noreferrer" className="external-link">
                              {field.value}
                            </a>
                          ) : (
                            '—'
                          )
                        ) : (
                          formatValue(field.value, field.key)
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ))}
      </div>
    </div>
  );
};

export default CarFullDetails;

