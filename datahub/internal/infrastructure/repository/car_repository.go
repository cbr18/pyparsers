package repository

import (
	"context"
	"errors"

	"datahub/internal/domain"
	"datahub/internal/infrastructure/database"

	"gorm.io/gorm"
)

// CarRepository - репозиторий для работы с моделью Car
type CarRepository struct {
	db *gorm.DB
}

// NewCarRepository - создает новый экземпляр репозитория
func NewCarRepository() *CarRepository {
	return &CarRepository{
		db: database.DB,
	}
}

// Create - создает новую запись Car в базе данных
func (r *CarRepository) Create(ctx context.Context, car *domain.Car) error {
	return r.db.WithContext(ctx).Create(car).Error
}

// GetByUUID - получает Car по UUID
func (r *CarRepository) GetByUUID(ctx context.Context, uuid string) (*domain.Car, error) {
	var car domain.Car
	err := r.db.WithContext(ctx).Where("uuid = ?", uuid).First(&car).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil // Возвращаем nil, nil если запись не найдена
		}
		return nil, err
	}
	return &car, nil
}

// Update - обновляет запись Car
func (r *CarRepository) Update(ctx context.Context, car *domain.Car) error {
	return r.db.WithContext(ctx).Save(car).Error
}

// Delete - удаляет запись Car по UUID
func (r *CarRepository) Delete(ctx context.Context, uuid string) error {
	return r.db.WithContext(ctx).Where("uuid = ?", uuid).Delete(&domain.Car{}).Error
}

// List - получает список Car с применением фильтров
func (r *CarRepository) List(ctx context.Context, filter *domain.CarFilter, offset, limit int) ([]*domain.Car, int64, error) {
	var cars []*domain.Car
	var count int64

	query := r.db.WithContext(ctx).Model(&domain.Car{})

	// Применяем фильтры
	if filter != nil {
		if filter.Source != nil {
			query = query.Where("source = ?", *filter.Source)
		}
		if filter.BrandName != nil {
			query = query.Where("brand_name = ?", *filter.BrandName)
		}
		if filter.City != nil {
			query = query.Where("city = ?", *filter.City)
		}
		if filter.Year != nil {
			query = query.Where("year = ?", *filter.Year)
		}
		if filter.IsAvailable != nil {
			query = query.Where("is_available = ?", *filter.IsAvailable)
		}
		if filter.Search != nil {
			query = query.Where("title ILIKE ? OR car_name ILIKE ?", "%"+*filter.Search+"%", "%"+*filter.Search+"%")
		}
	}

	// Получаем общее количество записей
	if err := query.Count(&count).Error; err != nil {
		return nil, 0, err
	}

	// Получаем записи с пагинацией
	if err := query.Order("sort_number DESC, created_at DESC").
		Offset(offset).
		Limit(limit).
		Find(&cars).Error; err != nil {
		return nil, 0, err
	}

	return cars, count, nil
}

// DeleteBySource - удаляет все записи Car по источнику
func (r *CarRepository) DeleteBySource(ctx context.Context, source string) error {
	return r.db.WithContext(ctx).Where("source = ?", source).Delete(&domain.Car{}).Error
}

// CreateMany - создает множество записей Car в базе данных
func (r *CarRepository) CreateMany(ctx context.Context, cars []domain.Car) error {
	if len(cars) == 0 {
		return nil
	}
	return r.db.WithContext(ctx).Create(&cars).Error
}

// GetBySourceAndSort - получает последние N записей Car по источнику, отсортированные по sort_number и created_at
func (r *CarRepository) GetBySourceAndSort(ctx context.Context, source string, limit int) ([]domain.Car, error) {
	var cars []domain.Car
	err := r.db.WithContext(ctx).
		Where("source = ?", source).
		Order("sort_number DESC, created_at DESC").
		Limit(limit).
		Find(&cars).Error
	return cars, err
}
