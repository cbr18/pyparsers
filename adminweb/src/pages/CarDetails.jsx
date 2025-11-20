import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { fetchCarByUuid } from '../services/api'
import './CarDetails.css'

const formatKey = (key) =>
  key
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())

const formatValue = (key, value) => {
  if (value === null || value === undefined || value === '') {
    return '—'
  }

  if (typeof value === 'boolean') {
    return value ? 'Да' : 'Нет'
  }

  if (['created_at', 'updated_at', 'last_detail_update'].includes(key) && value) {
    const date = new Date(value)
    if (!Number.isNaN(date.getTime())) {
      return date.toLocaleString()
    }
  }

  // Форматирование цены в рублях
  if (key === 'rub_price' && typeof value === 'number' && value > 0) {
    return new Intl.NumberFormat('ru-RU', { 
      style: 'currency', 
      currency: 'RUB', 
      maximumFractionDigits: 0 
    }).format(value)
  }

  if (Array.isArray(value)) {
    return value.length ? value.join(', ') : '—'
  }

  return value
}

function CarDetailsPage() {
  const { uuid: routeUuid } = useParams()
  const navigate = useNavigate()
  const [inputUuid, setInputUuid] = useState(routeUuid || '')
  const [car, setCar] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [currentImageIndex, setCurrentImageIndex] = useState(0)

  useEffect(() => {
    if (!routeUuid) {
      setCar(null)
      setError('')
      setInputUuid('')
      setLoading(false)
      return
    }

    const trimmed = routeUuid.trim()
    if (!trimmed) {
      setCar(null)
      setError('Некорректный UUID')
      setLoading(false)
      return
    }

    setInputUuid(trimmed)
    setLoading(true)
    setError('')

    fetchCarByUuid(trimmed)
      .then((result) => {
        const fetchedCar = result?.data ?? result
        if (!fetchedCar) {
          setError('Машина не найдена')
          setCar(null)
        } else {
          setCar(fetchedCar)
        }
      })
      .catch((err) => {
        if (err?.response?.status === 404) {
          setError('Машина не найдена')
        } else {
          setError(err?.response?.data?.error || err?.message || 'Ошибка загрузки данных')
        }
        setCar(null)
      })
      .finally(() => {
        setLoading(false)
      })
  }, [routeUuid])

  const galleryImages = useMemo(() => {
    if (!car) {
      return []
    }
    if (car.image_gallery) {
      return car.image_gallery
        .split(/\s+/)
        .map((url) => url.trim())
        .filter(Boolean)
    }
    if (car.image) {
      return [car.image]
    }
    return []
  }, [car])

  useEffect(() => {
    setCurrentImageIndex(0)
  }, [galleryImages])

  const handleSubmit = (event) => {
    event.preventDefault()
    const trimmed = inputUuid.trim()
    if (!trimmed) {
      setError('Введите UUID')
      setCar(null)
      return
    }
    navigate(`/cars/${trimmed}`)
  }

  const handlePrevImage = () => {
    if (!galleryImages.length) return
    setCurrentImageIndex((prev) => (prev - 1 + galleryImages.length) % galleryImages.length)
  }

  const handleNextImage = () => {
    if (!galleryImages.length) return
    setCurrentImageIndex((prev) => (prev + 1) % galleryImages.length)
  }

  const fields = useMemo(() => {
    if (!car) {
      return []
    }

    return Object.entries(car)
      .filter(([key]) => key !== 'image_gallery')
      .map(([key, value]) => ({
        key,
        label: formatKey(key),
        value: formatValue(key, value)
      }))
      .sort((a, b) => a.label.localeCompare(b.label, 'ru'))
  }, [car])

  return (
    <div className="car-details-page">
      <div className="car-details-header">
        <h1>Информация о машине</h1>
        <form className="uuid-form" onSubmit={handleSubmit}>
          <input
            type="text"
            value={inputUuid}
            onChange={(event) => setInputUuid(event.target.value)}
            placeholder="Введите UUID"
          />
          <button type="submit" className="btn-primary">
            Загрузить
          </button>
        </form>
      </div>

      {error && <div className="error-message">{error}</div>}

      {loading && <div className="loading">Загрузка данных...</div>}

      {!loading && car && (
        <div className="car-details-content">
          <section className="car-images">
            <h2>Фотографии</h2>
            {galleryImages.length > 0 ? (
              <div className="carousel">
                <button
                  type="button"
                  className="carousel-control"
                  onClick={handlePrevImage}
                  aria-label="Предыдущее изображение"
                >
                  ‹
                </button>
                <div className="carousel-image-wrapper">
                  <img src={galleryImages[currentImageIndex]} alt="Изображение автомобиля" />
                </div>
                <button
                  type="button"
                  className="carousel-control"
                  onClick={handleNextImage}
                  aria-label="Следующее изображение"
                >
                  ›
                </button>
              </div>
            ) : (
              <div className="carousel placeholder">Нет изображений</div>
            )}
            {galleryImages.length > 1 && (
              <div className="carousel-indicator">
                {currentImageIndex + 1} / {galleryImages.length}
              </div>
            )}
          </section>

          <section className="car-link">
            <h2>Ссылка на источник</h2>
            {car.link ? (
              <a href={car.link} target="_blank" rel="noopener noreferrer">
                Открыть оригинальную страницу
              </a>
            ) : (
              <span>Ссылка недоступна</span>
            )}
          </section>

          <section className="car-fields">
            <h2>Поля автомобиля</h2>
            <div className="fields-grid">
              {fields.map(({ key, label, value }) => (
                <div key={key} className="field-item">
                  <span className="field-label">{label}</span>
                  <span className="field-value">{value}</span>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  )
}

export default CarDetailsPage
