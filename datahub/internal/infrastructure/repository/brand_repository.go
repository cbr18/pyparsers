package repository

import (
	"context"
	"errors"
	"time"

	"datahub/internal/domain"
	"datahub/internal/infrastructure/database"

	"gorm.io/gorm"
)

// BrandRepository - репозиторий для работы с моделью Brand
type BrandRepository struct {
	db *gorm.DB
}

// NewBrandRepository - создает новый экземпляр репозитория брендов
func NewBrandRepository() *BrandRepository {
	return &BrandRepository{
		db: database.DB,
	}
}

// GetByOrigName - получает Brand по оригинальному имени (brand_name из Car)
func (r *BrandRepository) GetByOrigName(ctx context.Context, origName string) (*domain.Brand, error) {
	var brand domain.Brand
	// Ищем по полю name или orig_name
	err := r.db.WithContext(ctx).Where("name = ? OR orig_name = ?", origName, origName).First(&brand).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil // Возвращаем nil, nil если запись не найдена
		}
		return nil, err
	}
	return &brand, nil
}

// Create - создаёт новую запись Brand в базе данных
func (r *BrandRepository) Create(ctx context.Context, brand *domain.Brand) error {
	now := time.Now()
	if brand.CreatedAt.IsZero() {
		brand.CreatedAt = now
	}
	brand.UpdatedAt = now
	return r.db.WithContext(ctx).Create(brand).Error
}
