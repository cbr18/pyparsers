package repository

import (
	"context"
	"errors"
	"fmt"
	"os"
	"time"

	"datahub/internal/domain"
	"datahub/internal/infrastructure/database"

	"github.com/google/uuid"
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

// Create - создаёт новую запись Car в базе данных
// Также проверяет наличие бренда в таблице Brands и создает его при необходимости
func (r *CarRepository) Create(ctx context.Context, car *domain.Car) error {
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
	if err := tx.Create(car).Error; err != nil {
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
func (r *CarRepository) Update(ctx context.Context, car *domain.Car) error {
	car.UpdatedAt = time.Now()
	return r.db.WithContext(ctx).Save(car).Error
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
	// Добавляем явное логирование в начале метода
	fmt.Println("=== CreateMany called with", len(cars), "cars ===")
	
	// Запись в файл для отладки
	f, _ := os.OpenFile("debug_log.txt", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	if f != nil {
		defer f.Close()
		fmt.Fprintf(f, "=== CreateMany called with %d cars ===\n", len(cars))
	}
	
	if len(cars) == 0 {
		fmt.Println("No cars to create, returning")
		return nil
	}

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

	now := time.Now()

	// Обрабатываем каждую машину
	for i := range cars {
		if cars[i].CreatedAt.IsZero() {
			cars[i].CreatedAt = now
		}
		cars[i].UpdatedAt = now

		// Проверяем наличие бренда по brand_name
		if cars[i].BrandName != "" {
			fmt.Printf("Processing car with BrandName: %s\n", cars[i].BrandName)
			
			// Ищем бренд в рамках транзакции
			var brand domain.Brand
			// Ищем по полю name или orig_name
			err := tx.Debug().Where("name = ? OR orig_name = ?", cars[i].BrandName, cars[i].BrandName).First(&brand).Error

			if err != nil {
				fmt.Printf("Search result for brand '%s': %v\n", cars[i].BrandName, err)
			} else {
				fmt.Printf("Found existing brand: ID=%s, Name=%s\n", brand.ID, *brand.Name)
			}

			// Если бренд не найден, создаем его
			if errors.Is(err, gorm.ErrRecordNotFound) {
				brandName := cars[i].BrandName
				newBrand := &domain.Brand{
					Name:      &brandName,
					OrigName:  &brandName, // Устанавливаем оригинальное имя бренда
					CreatedAt: now,
					UpdatedAt: now,
				}

				// Логируем создание бренда
				fmt.Printf("Creating brand: %s\n", brandName)

				// Пробуем создать бренд напрямую через SQL
				brandID := uuid.New().String()
				sqlResult := tx.Exec(`
					INSERT INTO brands (id, name, orig_name, created_at, updated_at)
					VALUES (?, ?, ?, ?, ?)
				`, brandID, brandName, brandName, now, now)
				
				if sqlResult.Error != nil {
					// Логируем ошибку SQL
					fmt.Printf("SQL Error creating brand: %v\n", sqlResult.Error)
					tx.Rollback()
					return sqlResult.Error
				}
				
				// Устанавливаем ID для нового бренда
				newBrand.ID = brandID

				// Логируем успешное создание бренда
				fmt.Printf("Brand created successfully with ID: %s\n", newBrand.ID)

				// Устанавливаем связь с новым брендом
				cars[i].MybrandID = &newBrand.ID
				fmt.Printf("Set MybrandID for car to: %s\n", *cars[i].MybrandID)
			} else if err != nil {
				// Если произошла другая ошибка
				fmt.Printf("Error searching for brand: %v\n", err)
				tx.Rollback()
				return err
			} else {
				// Устанавливаем связь с существующим брендом
				cars[i].MybrandID = &brand.ID
				fmt.Printf("Set MybrandID for car to existing brand: %s\n", *cars[i].MybrandID)
			}
		}
	}

	// Создаем все машины
	if err := tx.Create(&cars).Error; err != nil {
		tx.Rollback()
		return err
	}

	// Фиксируем транзакцию
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
