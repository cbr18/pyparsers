package repository

import (
	"context"
	"errors"
	"fmt"
	"log"
	"time"

	"datahub/internal/domain"
	"datahub/internal/infrastructure/database"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"
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

// Create - создаёт новую запись Car в базе данных
// Также проверяет наличие бренда в таблице Brands и создает его при необходимости
func (r *CarRepository) Create(ctx context.Context, car domain.Car) error {
	now := time.Now()
	if car.CreatedAt.IsZero() {
		car.CreatedAt = now
	}
	car.UpdatedAt = now

	// Начинаем транзакцию
	tx := r.db.WithContext(ctx).Begin()
	if tx.Error != nil {
		return tx.Error
	}

	// Откатываем транзакцию в случае ошибки
	defer func() {
		if r := recover(); r != nil {
			tx.Rollback()
		}
	}()

	// Проверяем наличие бренда по brand_name
	fmt.Printf("BrandName: %s\n", car.BrandName)
	if car.BrandName != "" {
		// Ищем бренд в рамках транзакции
		var brand domain.Brand
		// Ищем по полю name или orig_name
		err := tx.Where("name = ? OR orig_name = ?", car.BrandName, car.BrandName).First(&brand).Error

		// Если бренд не найден, создаем его
		if errors.Is(err, gorm.ErrRecordNotFound) {
			brandName := car.BrandName
			newBrand := &domain.Brand{
				Name:      &brandName,
				OrigName:  &brandName, // Устанавливаем оригинальное имя бренда
				CreatedAt: now,
				UpdatedAt: now,
			}

			if err := tx.Create(newBrand).Error; err != nil {
				tx.Rollback()
				return err
			}

			// Устанавливаем связь с новым брендом
			car.MybrandID = &newBrand.ID
		} else if err != nil {
			// Если произошла другая ошибка
			tx.Rollback()
			return err
		} else {
			// Устанавливаем связь с существующим брендом
			car.MybrandID = &brand.ID
		}

	}

	// Создаем машину
	if err := tx.Create(&car).Error; err != nil {
		tx.Rollback()
		return err
	}

	// Фиксируем транзакцию
	return tx.Commit().Error
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

// GetByID - получает Car по ID
func (r *CarRepository) GetByID(ctx context.Context, id int64) (*domain.Car, error) {
	var car domain.Car
	err := r.db.WithContext(ctx).Where("car_id = ?", id).First(&car).Error
	if err != nil {
		if errors.Is(err, gorm.ErrRecordNotFound) {
			return nil, nil // Возвращаем nil, nil если запись не найдена
		}
		return nil, err
	}
	return &car, nil
}

// Update - обновляет запись Car
func (r *CarRepository) Update(ctx context.Context, car domain.Car) error {
	car.UpdatedAt = time.Now()
	return r.db.WithContext(ctx).Save(&car).Error
}

// Delete - удаляет запись Car по UUID
func (r *CarRepository) Delete(ctx context.Context, uuid string) error {
	return r.db.WithContext(ctx).Where("uuid = ?", uuid).Delete(&domain.Car{}).Error
}

// List - получает список Car с применением фильтров
func (r *CarRepository) List(ctx context.Context, filter domain.CarFilter, page, limit int, sort string) ([]domain.Car, int, error) {
	var cars []domain.Car
	var count int64

	query := r.db.WithContext(ctx).Model(&domain.Car{})

	// Применяем фильтры
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

	// Получаем общее количество записей
	if err := query.Count(&count).Error; err != nil {
		return nil, 0, err
	}

	// Определяем порядок сортировки
	orderBy := "sort_number DESC, created_at DESC"
	if sort != "" {
		orderBy = sort
	}

	// Вычисляем смещение
	offset := (page - 1) * limit
	if offset < 0 {
		offset = 0
	}

	// Получаем записи с пагинацией
	if err := query.Order(orderBy).
		Offset(offset).
		Limit(limit).
		Find(&cars).Error; err != nil {
		return nil, 0, err
	}

	return cars, int(count), nil
}

// DeleteBySource - удаляет все записи Car по источнику
func (r *CarRepository) DeleteBySource(ctx context.Context, source string) error {
	return r.db.WithContext(ctx).Where("source = ?", source).Delete(&domain.Car{}).Error
}

// CreateMany - создаёт множество записей Car в базе данных
// Также проверяет наличие бренда в таблице Brands и создает его при необходимости
func (r *CarRepository) CreateMany(ctx context.Context, cars []domain.Car) error {
	if len(cars) == 0 {
		return nil
	}

	now := time.Now()
	// Собираем уникальные пары (source, car_id) из вставляемых машин
	type carKey struct {
		Source string
		CarID  int64
	}
	carKeySet := make(map[carKey]struct{})
	for _, car := range cars {
		carKeySet[carKey{Source: car.Source, CarID: car.CarID}] = struct{}{}
	}

	// Получаем уже существующие машины с такими ключами
	var existing []domain.Car
	var sources []string
	var carIDs []int64
	for k := range carKeySet {
		sources = append(sources, k.Source)
		carIDs = append(carIDs, k.CarID)
	}
	if len(sources) > 0 && len(carIDs) > 0 {
		r.db.WithContext(ctx).
			Where("source IN ? AND car_id IN ?", sources, carIDs).
			Find(&existing)
	}
	existingMap := make(map[carKey]struct{})
	for _, car := range existing {
		existingMap[carKey{Source: car.Source, CarID: car.CarID}] = struct{}{}
	}

	// Оставляем только новые машины
	filtered := make([]domain.Car, 0, len(cars))
	for _, car := range cars {
		if _, found := existingMap[carKey{Source: car.Source, CarID: car.CarID}]; !found {
			filtered = append(filtered, car)
		}
	}
	if len(filtered) == 0 {
		return nil
	}

	// Начинаем транзакцию
	tx := r.db.WithContext(ctx).Begin()
	if tx.Error != nil {
		return tx.Error
	}
	defer func() {
		if r := recover(); r != nil {
			tx.Rollback()
		}
	}()

	// Обрабатываем каждую машину (бренд)
	for i := range filtered {
		if filtered[i].CreatedAt.IsZero() {
			filtered[i].CreatedAt = now
		}
		filtered[i].UpdatedAt = now

		if filtered[i].BrandName != "" {
			var brand domain.Brand
			err := tx.Where("name = ? OR orig_name = ?", filtered[i].BrandName, filtered[i].BrandName).First(&brand).Error
			if errors.Is(err, gorm.ErrRecordNotFound) {
				brandName := filtered[i].BrandName
				newBrand := &domain.Brand{
					Name:      &brandName,
					OrigName:  &brandName,
					CreatedAt: now,
					UpdatedAt: now,
				}
				if err := tx.Create(newBrand).Error; err != nil {
					tx.Rollback()
					log.Printf("ERROR: failed to create brand '%s': %v", brandName, err)
					return err
				}
				log.Printf("Created new brand: %s (ID=%s)", brandName, newBrand.ID)
				filtered[i].MybrandID = &newBrand.ID
			} else if err != nil {
				tx.Rollback()
				log.Printf("ERROR: failed to find brand '%s': %v", filtered[i].BrandName, err)
				return err
			} else {
				filtered[i].MybrandID = &brand.ID
			}
		}
	}

	// Вставляем все машины, пропуская дубликаты на уровне базы
	if err := tx.Clauses(clause.OnConflict{DoNothing: true}).Create(&filtered).Error; err != nil {
		tx.Rollback()
		log.Printf("ERROR: failed to insert cars (possible duplicate): %v", err)
		return err
	}

	return tx.Commit().Error
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
