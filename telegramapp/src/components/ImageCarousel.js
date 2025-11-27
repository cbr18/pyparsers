import React, { useState } from 'react';
import { getProxiedImageUrl } from '../utils/imageProxy';
import './ImageCarousel.css';

const ImageCarousel = ({ images, mainImage, alt }) => {
  const [currentIndex, setCurrentIndex] = useState(0);

  // Формируем массив картинок: главная + галерея
  const allImages = React.useMemo(() => {
    const result = [];
    
    if (mainImage) {
      result.push(mainImage);
    }
    
    if (images && typeof images === 'string') {
      // image_gallery может быть строкой с URLs разделенными пробелами
      const galleryUrls = images.split(' ').filter(url => url && url.trim());
      result.push(...galleryUrls);
    }
    
    // Удаляем дубликаты
    return [...new Set(result)];
  }, [images, mainImage]);

  const placeholder = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="350" height="220"><defs><linearGradient id="grad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:%23ff5f6d;stop-opacity:0.1" /><stop offset="100%" style="stop-color:%23ffc371;stop-opacity:0.1" /></linearGradient></defs><rect width="100%" height="100%" fill="url(%23grad)"/><g transform="translate(175,110)"><circle cx="0" cy="0" r="30" fill="none" stroke="%23ff5f6d" stroke-width="2" opacity="0.3"/><path d="M-20,-10 L20,-10 M-20,0 L20,0 M-20,10 L20,10" stroke="%23ff5f6d" stroke-width="2" opacity="0.3"/><text x="0" y="35" text-anchor="middle" fill="%23ff5f6d" font-size="14" font-family="Arial, sans-serif" opacity="0.6">Нет фото</text></g></svg>';

  const goToPrevious = () => {
    setCurrentIndex((prevIndex) => 
      prevIndex === 0 ? allImages.length - 1 : prevIndex - 1
    );
  };

  const goToNext = () => {
    setCurrentIndex((prevIndex) => 
      prevIndex === allImages.length - 1 ? 0 : prevIndex + 1
    );
  };

  const goToSlide = (index) => {
    setCurrentIndex(index);
  };

  if (!allImages || allImages.length === 0) {
    return (
      <div className="image-carousel">
        <div className="carousel-main-image">
          <img src={placeholder} alt={alt || 'Нет фото'} />
        </div>
      </div>
    );
  }

  const currentImageUrl = getProxiedImageUrl(allImages[currentIndex]);

  return (
    <div className="image-carousel">
      <div className="carousel-main-image">
        <img
          src={currentImageUrl || placeholder}
          alt={alt || 'Фото автомобиля'}
          onError={(e) => {
            e.target.onerror = null;
            if (currentIndex === 0 && allImages.length > 1) {
              setCurrentIndex(1);
              return;
            }
            e.target.src = placeholder;
          }}
        />
        
        {allImages.length > 1 && (
          <>
            <button className="carousel-btn carousel-btn-prev" onClick={goToPrevious} aria-label="Предыдущее фото">
              ‹
            </button>
            <button className="carousel-btn carousel-btn-next" onClick={goToNext} aria-label="Следующее фото">
              ›
            </button>
            
            <div className="carousel-counter">
              {currentIndex + 1} / {allImages.length}
            </div>
          </>
        )}
      </div>

      {allImages.length > 1 && (
        <div className="carousel-thumbnails">
          {allImages.map((img, index) => {
            const thumbUrl = getProxiedImageUrl(img);
            return (
              <button
                key={index}
                className={`carousel-thumbnail ${index === currentIndex ? 'active' : ''}`}
                onClick={() => goToSlide(index)}
                aria-label={`Перейти к фото ${index + 1}`}
              >
                <img
                  src={thumbUrl || placeholder}
                  alt={`Миниатюра ${index + 1}`}
                  onError={(e) => { 
                    e.target.onerror = null; 
                    e.target.src = placeholder; 
                  }}
                />
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default ImageCarousel;

