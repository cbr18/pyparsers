package repository

import (
	"context"
	"errors"
	"fmt"
	"log"
	"strings"
	"time"

	"datahub/internal/domain"
	"datahub/internal/filters"
	"datahub/internal/infrastructure/database"

	"gorm.io/gorm"
	"gorm.io/gorm/clause"
	"github.com/google/uuid"
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
	// Ensure UUID is set
	if car.UUID == "" {
		car.UUID = uuid.NewString()
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

	// Проверяем наличие бренда по brand_name
	fmt.Printf("BrandName: %s\n", car.BrandName)
	if car.BrandName != "" {
		// Ищем бренд в рамках транзакции
		var brand domain.Brand
		// Ищем по полю name, orig_name или в списке алиасов (в нижнем регистре)
		// Также проверяем обратное вхождение: входят ли name или orig_name в искомую строку
		searchTerm := strings.ToLower(strings.TrimSpace(car.BrandName))
		err := tx.Where(
			`LOWER(COALESCE(name, '')) = ? OR 
			 LOWER(COALESCE(orig_name, '')) = ? OR 
			 LOWER(COALESCE(aliases, '')) LIKE ? OR
			 (? LIKE '%' || LOWER(COALESCE(name, '')) || '%' AND LOWER(COALESCE(name, '')) != '') OR
			 (? LIKE '%' || LOWER(COALESCE(orig_name, '')) || '%' AND LOWER(COALESCE(orig_name, '')) != '') OR
			 EXISTS (
			   SELECT 1 FROM unnest(string_to_array(LOWER(COALESCE(aliases, '')), ',')) AS alias_item
			   WHERE ? LIKE '%' || TRIM(alias_item) || '%' AND TRIM(alias_item) != ''
			 )`,
			searchTerm, searchTerm, "%"+searchTerm+"%",
			searchTerm, searchTerm,
			searchTerm,
		).First(&brand).Error

		// Если бренд не найден, создаем его
		if errors.Is(err, gorm.ErrRecordNotFound) {
			// Создаем бренд с правильной логикой: orig_name - китайское, name - английское
			newBrand, err := r.CreateBrandWithTranslation(ctx, car.BrandName, nil)
			if err != nil {
				tx.Rollback()
				return err
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
	priceFieldExpr := "(CASE WHEN final_price IS NOT NULL AND final_price > 0 THEN final_price ELSE rub_price END)"

	// отдаём только машины с детальной информацией и доступные по флагу
	query = query.Where("has_details = ? AND is_available = ?", true, true)

	query = filters.ApplyViewerFilters(query)

	// Применяем фильтры
	if filter.Source != nil {
		query = query.Where("source = ?", *filter.Source)
	}
	if filter.BrandName != nil {
		// Используем ILIKE для нечувствительности к регистру и частичного совпадения
		query = query.Where("brand_name ILIKE ?", "%"+*filter.BrandName+"%")
	}
	if filter.City != nil {
		// Используем ILIKE для нечувствительности к регистру и частичного совпадения
		query = query.Where("city ILIKE ?", "%"+*filter.City+"%")
	}
	if filter.Year != nil {
		query = query.Where("year = ?", *filter.Year)
	}
	// Диапазон года
	if filter.YearFrom != nil {
		query = query.Where("year >= ?", *filter.YearFrom)
	}
	if filter.YearTo != nil {
		query = query.Where("year <= ?", *filter.YearTo)
	}
	// Диапазон цены (по final_price если есть, иначе rub_price)
	if filter.PriceFrom != nil {
		query = query.Where(priceFieldExpr+" >= ?", *filter.PriceFrom)
	}
	if filter.PriceTo != nil {
		query = query.Where(priceFieldExpr+" <= ?", *filter.PriceTo)
	}
	if filter.IsAvailable != nil {
		query = query.Where("is_available = ?", *filter.IsAvailable)
	}
	if filter.HasDetails != nil {
		query = query.Where("has_details = ?", *filter.HasDetails)
	}
	if filter.Search != nil {
		query = query.Where("title ILIKE ? OR car_name ILIKE ?", "%"+*filter.Search+"%", "%"+*filter.Search+"%")
	}

	// Получаем общее количество записей
	if err := query.Count(&count).Error; err != nil {
		return nil, 0, err
	}

	// Определяем порядок сортировки
	// ВСЕГДА сначала показываем машины с детальной информацией (has_details=true)
	// Это приоритет над любой другой сортировкой
	var orderBy string
	if sort != "" {
		// Если задана пользовательская сортировка, добавляем has_details в начало
		orderBy = "has_details DESC NULLS LAST, " + sort
	} else {
		// Дефолтная сортировка
		orderBy = "has_details DESC NULLS LAST, sort_number DESC, updated_at DESC"
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

// DeleteUnavailableCars удаляет только записи без деталей и недоступные, чтобы сохранить подтвержденные машины
func (r *CarRepository) DeleteUnavailableCars(ctx context.Context, source string) error {
	return r.db.WithContext(ctx).
		Where("source = ? AND has_details = ? AND is_available = ?", source, false, false).
		Delete(&domain.Car{}).Error
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
	// Также устраняем дубликаты внутри входного набора по (source, car_id)
	seenNew := make(map[carKey]struct{}, len(cars))
	for _, car := range cars {
		key := carKey{Source: car.Source, CarID: car.CarID}
		if _, exists := existingMap[key]; exists {
			// уже есть в БД — пропускаем
			continue
		}
		if _, dup := seenNew[key]; dup {
			// дубликат внутри входного массива — пропускаем
			continue
		}
		seenNew[key] = struct{}{}
		filtered = append(filtered, car)
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
		// Ensure UUID is set for batch create
		if filtered[i].UUID == "" {
			filtered[i].UUID = uuid.NewString()
		}

		if filtered[i].BrandName != "" {
			var brand domain.Brand
			// Ищем по полю name, orig_name или в списке алиасов (в нижнем регистре)
			// Также проверяем обратное вхождение: входят ли name или orig_name в искомую строку
			searchTerm := strings.ToLower(strings.TrimSpace(filtered[i].BrandName))
			err := tx.Where(
				`LOWER(COALESCE(name, '')) = ? OR 
				 LOWER(COALESCE(orig_name, '')) = ? OR 
				 LOWER(COALESCE(aliases, '')) LIKE ? OR
				 (? LIKE '%' || LOWER(COALESCE(name, '')) || '%' AND LOWER(COALESCE(name, '')) != '') OR
				 (? LIKE '%' || LOWER(COALESCE(orig_name, '')) || '%' AND LOWER(COALESCE(orig_name, '')) != '')`,
				searchTerm, searchTerm, "%"+searchTerm+"%",
				searchTerm, searchTerm,
			).First(&brand).Error
			if errors.Is(err, gorm.ErrRecordNotFound) {
				// Создаем бренд с правильной логикой: orig_name - китайское, name - английское
				newBrand, err := r.CreateBrandWithTranslation(ctx, filtered[i].BrandName, nil)
				if err != nil {
					tx.Rollback()
					log.Printf("ERROR: failed to create brand '%s': %v", filtered[i].BrandName, err)
					return err
				}
				if err := tx.Create(newBrand).Error; err != nil {
					tx.Rollback()
					log.Printf("ERROR: failed to create brand '%s': %v", filtered[i].BrandName, err)
					return err
				}
				log.Printf("Created new brand: %s (ID=%s)", filtered[i].BrandName, newBrand.ID)
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

    // Вставляем все машины батчами, пропуская дубликаты на уровне базы
    // С учетом 117+ полей, максимальный батч: 65535 / 117 ≈ 560
    const batchSize = 500
    for i := 0; i < len(filtered); i += batchSize {
        end := i + batchSize
        if end > len(filtered) {
            end = len(filtered)
        }
        batch := filtered[i:end]
        if err := tx.Clauses(clause.OnConflict{DoNothing: true}).CreateInBatches(&batch, batchSize).Error; err != nil {
            tx.Rollback()
            log.Printf("ERROR: failed to insert cars batch [%d:%d]: %v", i, end, err)
            return err
        }
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

// GetCarsForValidation gets cars with is_available=true sorted by updated_at ASC
func (r *CarRepository) GetCarsForValidation(ctx context.Context, source string, limit int) ([]domain.Car, error) {
	var cars []domain.Car
	err := r.db.WithContext(ctx).
		Where("source = ? AND is_available = ?", source, true).
		Order("updated_at ASC").
		Limit(limit).
		Find(&cars).Error
	return cars, err
}

// CountCarsForValidation counts cars with is_available=true for a source
func (r *CarRepository) CountCarsForValidation(ctx context.Context, source string) (int64, error) {
	var count int64
	err := r.db.WithContext(ctx).
		Where("source = ? AND is_available = ?", source, true).
		Model(&domain.Car{}).
		Count(&count).Error
	return count, err
}

// GetAllIDsBySource returns sku_id or car_id values for the given source
func (r *CarRepository) GetAllIDsBySource(ctx context.Context, source string) ([]string, error) {
	var rows []struct {
		SkuID string
		CarID int64
	}
	if err := r.db.WithContext(ctx).
		Model(&domain.Car{}).
		Where("source = ?", source).
		Select("sku_id, car_id").
		Find(&rows).Error; err != nil {
		return nil, err
	}

	ids := make([]string, 0, len(rows))
	seen := make(map[string]struct{}, len(rows))
	for _, row := range rows {
		var id string
		if source == "dongchedi" {
			if row.SkuID != "" {
				id = row.SkuID
			} else if row.CarID != 0 {
				id = fmt.Sprintf("%d", row.CarID)
			}
		} else {
			if row.CarID != 0 {
				id = fmt.Sprintf("%d", row.CarID)
			}
		}
		if id == "" {
			continue
		}
		if _, ok := seen[id]; ok {
			continue
		}
		seen[id] = struct{}{}
		ids = append(ids, id)
	}
	return ids, nil
}

// ReplaceBySource — атомарно заменяет все записи по источнику в одной транзакции
func (r *CarRepository) ReplaceBySource(ctx context.Context, source string, cars []domain.Car) error {
    now := time.Now()
    tx := r.db.WithContext(ctx).Begin()
    if tx.Error != nil {
        return tx.Error
    }
    defer func() {
        if r := recover(); r != nil {
            tx.Rollback()
        }
    }()

    // Удаляем всё по источнику
    if err := tx.Where("source = ?", source).Delete(&domain.Car{}).Error; err != nil {
        tx.Rollback()
        return err
    }

    if len(cars) == 0 {
        return tx.Commit().Error
    }

    // Устраним дубликаты по (source, car_id) внутри входного слайса
    type carKey struct { Source string; CarID int64 }
    seen := make(map[carKey]struct{}, len(cars))
    dedup := make([]domain.Car, 0, len(cars))
    for i := range cars {
        key := carKey{ Source: cars[i].Source, CarID: cars[i].CarID }
        if _, ok := seen[key]; ok {
            continue
        }
        seen[key] = struct{}{}
        dedup = append(dedup, cars[i])
    }

    // Обеспечим UUID/времена и бренды
    for i := range dedup {
        if dedup[i].CreatedAt.IsZero() {
            dedup[i].CreatedAt = now
        }
        dedup[i].UpdatedAt = now
        if dedup[i].UUID == "" {
            dedup[i].UUID = uuid.NewString()
        }
        // Привяжем бренд
        if dedup[i].BrandName != "" {
            var brand domain.Brand
            // Ищем по полю name, orig_name или в списке алиасов (в нижнем регистре)
            // Также проверяем обратное вхождение: входят ли name или orig_name в искомую строку
            searchTerm := strings.ToLower(strings.TrimSpace(dedup[i].BrandName))
            err := tx.Where(
                `LOWER(COALESCE(name, '')) = ? OR 
                 LOWER(COALESCE(orig_name, '')) = ? OR 
                 LOWER(COALESCE(aliases, '')) LIKE ? OR
                 (? LIKE '%' || LOWER(COALESCE(name, '')) || '%' AND LOWER(COALESCE(name, '')) != '') OR
                 (? LIKE '%' || LOWER(COALESCE(orig_name, '')) || '%' AND LOWER(COALESCE(orig_name, '')) != '')`,
                searchTerm, searchTerm, "%"+searchTerm+"%",
                searchTerm, searchTerm,
            ).First(&brand).Error
            if errors.Is(err, gorm.ErrRecordNotFound) {
                // Создаем бренд с правильной логикой: orig_name - китайское, name - английское
                b, err := r.CreateBrandWithTranslation(ctx, dedup[i].BrandName, nil)
                if err != nil {
                    tx.Rollback()
                    return err
                }
                if err := tx.Create(b).Error; err != nil {
                    tx.Rollback()
                    return err
                }
                dedup[i].MybrandID = &b.ID
            } else if err != nil {
                tx.Rollback()
                return err
            } else {
                dedup[i].MybrandID = &brand.ID
            }
        }
    }

    // Вставляем все машины батчами в одной транзакции
    // С учетом 117+ полей, максимальный батч: 65535 / 117 ≈ 560
    const batchSize = 500
    for i := 0; i < len(dedup); i += batchSize {
        end := i + batchSize
        if end > len(dedup) {
            end = len(dedup)
        }
        batch := dedup[i:end]
        if err := tx.Clauses(clause.OnConflict{DoNothing: true}).CreateInBatches(&batch, batchSize).Error; err != nil {
            tx.Rollback()
            log.Printf("ERROR: failed to insert cars batch [%d:%d]: %v", i, end, err)
            return err
        }
    }

    return tx.Commit().Error
}

// CreateBrandWithTranslation создает бренд с переводом названия
func (r *CarRepository) CreateBrandWithTranslation(ctx context.Context, brandName string, translationService interface{}) (*domain.Brand, error) {
	origBrandName := brandName
	translatedBrandName := brandName // По умолчанию используем оригинальное имя
	
	// Переводим название бренда на английский если TranslationService доступен
	if translationService != nil {
		// Приводим к правильному типу и переводим
		if ts, ok := translationService.(interface {
			TranslateBrandName(ctx context.Context, brandName string) (string, error)
		}); ok {
			translated, err := ts.TranslateBrandName(ctx, brandName)
			if err != nil {
				fmt.Printf("Failed to translate brand name '%s': %v\n", brandName, err)
			} else {
				translatedBrandName = translated
			}
		}
	}
	
	now := time.Now()
	brand := &domain.Brand{
		Name:      &translatedBrandName, // Переведенное имя на английском
		OrigName:  &origBrandName,       // Оригинальное китайское имя
		CreatedAt: now,
		UpdatedAt: now,
	}
	
	return brand, nil
}

// CreateManyWithTranslation создает множество автомобилей с переводом брендов
func (r *CarRepository) CreateManyWithTranslation(ctx context.Context, cars []domain.Car, translationService interface{}) error {
	if len(cars) == 0 {
		return nil
	}

	now := time.Now()
	
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

	// Обрабатываем каждую машину
	for i := range cars {
		if cars[i].CreatedAt.IsZero() {
			cars[i].CreatedAt = now
		}
		cars[i].UpdatedAt = now
		
		// Ensure UUID is set
		if cars[i].UUID == "" {
			cars[i].UUID = uuid.NewString()
		}

		// Нормализуем first_registration_time: пустые строки -> пустая строка (будет NULL через Omit)
		if normalized, ok := domain.NormalizeFirstRegistrationDate(cars[i].FirstRegistrationTime); ok {
			cars[i].FirstRegistrationTime = normalized
		} else {
			// Для пустых/невалидных строк оставляем пустую строку - будем использовать Omit при вставке
			cars[i].FirstRegistrationTime = ""
		}

		// Обрабатываем бренд если есть
		if cars[i].BrandName != "" {
			var brand domain.Brand
			// Ищем по полю name, orig_name или в списке алиасов (в нижнем регистре)
			// Также проверяем обратное вхождение: входят ли name или orig_name в искомую строку
			searchTerm := strings.ToLower(strings.TrimSpace(cars[i].BrandName))
			err := tx.Where(
				`LOWER(COALESCE(name, '')) = ? OR 
				 LOWER(COALESCE(orig_name, '')) = ? OR 
				 LOWER(COALESCE(aliases, '')) LIKE ? OR
				 (? LIKE '%' || LOWER(COALESCE(name, '')) || '%' AND LOWER(COALESCE(name, '')) != '') OR
				 (? LIKE '%' || LOWER(COALESCE(orig_name, '')) || '%' AND LOWER(COALESCE(orig_name, '')) != '')`,
				searchTerm, searchTerm, "%"+searchTerm+"%",
				searchTerm, searchTerm,
			).First(&brand).Error

			// Если бренд не найден, создаем его с переводом
			if errors.Is(err, gorm.ErrRecordNotFound) {
				newBrand, err := r.CreateBrandWithTranslation(ctx, cars[i].BrandName, translationService)
				if err != nil {
					tx.Rollback()
					return err
				}

				if err := tx.Create(newBrand).Error; err != nil {
					tx.Rollback()
					return err
				}

				cars[i].MybrandID = &newBrand.ID
			} else if err != nil {
				tx.Rollback()
				return err
			} else {
				cars[i].MybrandID = &brand.ID
			}
		}
	}

	// Разделяем машины на две группы: с нормализованной датой и с пустой строкой
	var carsWithDate []domain.Car
	var carsWithoutDate []domain.Car
	
	for i := range cars {
		if cars[i].FirstRegistrationTime != "" {
			carsWithDate = append(carsWithDate, cars[i])
		} else {
			carsWithoutDate = append(carsWithoutDate, cars[i])
		}
	}
	
	// Вставляем машины с датой обычным способом
	const batchSize = 500
	if len(carsWithDate) > 0 {
		for i := 0; i < len(carsWithDate); i += batchSize {
			end := i + batchSize
			if end > len(carsWithDate) {
				end = len(carsWithDate)
			}
			batch := carsWithDate[i:end]
			if err := tx.Clauses(clause.OnConflict{DoNothing: true}).CreateInBatches(&batch, batchSize).Error; err != nil {
				tx.Rollback()
				return err
			}
		}
	}
	
	// Вставляем машины без даты - используем Create с Omit (будет NULL в БД)
	if len(carsWithoutDate) > 0 {
		// Создаем батчами, но для каждой записи используем Omit
		for i := 0; i < len(carsWithoutDate); i += batchSize {
			end := i + batchSize
			if end > len(carsWithoutDate) {
				end = len(carsWithoutDate)
			}
			batch := carsWithoutDate[i:end]
			// Вставляем каждую запись отдельно с Omit
			for j := range batch {
				if err := tx.Clauses(clause.OnConflict{DoNothing: true}).Omit("first_registration_time").Create(&batch[j]).Error; err != nil {
					tx.Rollback()
					return err
				}
			}
		}
	}

	return tx.Commit().Error
}

// ReplaceBySourceWithTranslation атомарно заменяет все записи источника на новые с переводом брендов
func (r *CarRepository) ReplaceBySourceWithTranslation(ctx context.Context, source string, cars []domain.Car, translationService interface{}) error {
	// Удаляем старые записи
	if err := r.DeleteBySource(ctx, source); err != nil {
		return err
	}
	
	// Создаем новые записи с переводом
	return r.CreateManyWithTranslation(ctx, cars, translationService)
}

// GetCarsWithoutDetails - получает машины без детальной информации
func (r *CarRepository) GetCarsWithoutDetails(ctx context.Context, source string, limit int) ([]domain.Car, error) {
	var cars []domain.Car
	err := r.db.WithContext(ctx).
		Where("source = ? AND (has_details = ? OR has_details IS NULL)", source, false).
		Order("created_at DESC").
		Limit(limit).
		Find(&cars).Error
	return cars, err
}

// UpdateCar - обновляет машину в БД (только детальные поля, не трогая ключевые поля source и car_id)
// НЕ обновляет поля, если они пустые (чтобы не перезаписывать существующие значения)
func (r *CarRepository) UpdateCar(ctx context.Context, car domain.Car) error {
	car.UpdatedAt = time.Now()

	updates := map[string]interface{}{
		// Всегда обновляем эти поля
		"year":                   car.Year,
		"mileage":                car.Mileage,
		"has_details":            car.HasDetails,
		"last_detail_update":     car.LastDetailUpdate,
		"is_available":           car.IsAvailable,
		"power":                  car.Power,
		"powertrain_type":        car.PowertrainType,
		"updated_at":             car.UpdatedAt,
		"failed_enhancement_attempts": car.FailedEnhancementAttempts,
	}

	// Обновляем строковые поля только если они не пустые
	if car.Title != "" {
		updates["title"] = car.Title
	}
	if car.CarName != "" {
		updates["car_name"] = car.CarName
	}
	if car.Price != "" {
		updates["price"] = car.Price
	}
	if car.Image != "" {
		updates["image"] = car.Image
	}
	if car.City != "" {
		updates["city"] = car.City
	}
	if car.ShopID != "" {
		updates["shop_id"] = car.ShopID
	}
	if car.Description != "" {
		updates["description"] = car.Description
	}
	if car.Color != "" {
		updates["color"] = car.Color
	}
	if car.Transmission != "" {
		updates["transmission"] = car.Transmission
	}
	if car.FuelType != "" {
		updates["fuel_type"] = car.FuelType
	}
	if car.EngineVolume != "" {
		updates["engine_volume"] = car.EngineVolume
	}
	if car.EngineVolumeML != "" {
		updates["engine_volume_ml"] = car.EngineVolumeML
	}
	if car.BodyType != "" {
		updates["body_type"] = car.BodyType
	}
	if car.DriveType != "" {
		updates["drive_type"] = car.DriveType
	}
	if car.Condition != "" {
		updates["condition"] = car.Condition
	}
	if car.BrandName != "" {
		updates["brand_name"] = car.BrandName
	}
	if car.SeriesName != "" {
		updates["series_name"] = car.SeriesName
	}
	if car.CarSourceCityName != "" {
		updates["car_source_city_name"] = car.CarSourceCityName
	}
	if car.Tags != "" {
		updates["tags"] = car.Tags
	}
	if car.TagsV2 != "" {
		updates["tags_v2"] = car.TagsV2
	}
	if car.Torque != "" {
		updates["torque"] = car.Torque
	}
	if car.Acceleration != "" {
		updates["acceleration"] = car.Acceleration
	}
	if car.MaxSpeed != "" {
		updates["max_speed"] = car.MaxSpeed
	}
	if car.FuelConsumption != "" {
		updates["fuel_consumption"] = car.FuelConsumption
	}
	if car.EmissionStandard != "" {
		updates["emission_standard"] = car.EmissionStandard
	}
	if car.Length != "" {
		updates["length"] = car.Length
	}
	if car.Width != "" {
		updates["width"] = car.Width
	}
	if car.Height != "" {
		updates["height"] = car.Height
	}
	if car.Wheelbase != "" {
		updates["wheelbase"] = car.Wheelbase
	}
	if car.CurbWeight != "" {
		updates["curb_weight"] = car.CurbWeight
	}
	if car.GrossWeight != "" {
		updates["gross_weight"] = car.GrossWeight
	}
	if car.EngineType != "" {
		updates["engine_type"] = car.EngineType
	}
	if car.EngineCode != "" {
		updates["engine_code"] = car.EngineCode
	}
	if car.CylinderCount != "" {
		updates["cylinder_count"] = car.CylinderCount
	}
	if car.ValveCount != "" {
		updates["valve_count"] = car.ValveCount
	}
	if car.CompressionRatio != "" {
		updates["compression_ratio"] = car.CompressionRatio
	}
	if car.TurboType != "" {
		updates["turbo_type"] = car.TurboType
	}
	if car.BatteryCapacity != "" {
		updates["battery_capacity"] = car.BatteryCapacity
	}
	if car.ElectricRange != "" {
		updates["electric_range"] = car.ElectricRange
	}
	if car.ChargingTime != "" {
		updates["charging_time"] = car.ChargingTime
	}
	if car.FastChargeTime != "" {
		updates["fast_charge_time"] = car.FastChargeTime
	}
	if car.ChargePortType != "" {
		updates["charge_port_type"] = car.ChargePortType
	}
	if car.TransmissionType != "" {
		updates["transmission_type"] = car.TransmissionType
	}
	if car.GearCount != "" {
		updates["gear_count"] = car.GearCount
	}
	if car.DifferentialType != "" {
		updates["differential_type"] = car.DifferentialType
	}
	if car.FrontSuspension != "" {
		updates["front_suspension"] = car.FrontSuspension
	}
	if car.RearSuspension != "" {
		updates["rear_suspension"] = car.RearSuspension
	}
	if car.FrontBrakes != "" {
		updates["front_brakes"] = car.FrontBrakes
	}
	if car.RearBrakes != "" {
		updates["rear_brakes"] = car.RearBrakes
	}
	if car.BrakeSystem != "" {
		updates["brake_system"] = car.BrakeSystem
	}
	if car.WheelSize != "" {
		updates["wheel_size"] = car.WheelSize
	}
	if car.TireSize != "" {
		updates["tire_size"] = car.TireSize
	}
	if car.WheelType != "" {
		updates["wheel_type"] = car.WheelType
	}
	if car.TireType != "" {
		updates["tire_type"] = car.TireType
	}
	if car.AirbagCount != "" {
		updates["airbag_count"] = car.AirbagCount
	}
	if car.ABS != "" {
		updates["abs"] = car.ABS
	}
	if car.ESP != "" {
		updates["esp"] = car.ESP
	}
	if car.TCS != "" {
		updates["tcs"] = car.TCS
	}
	if car.HillAssist != "" {
		updates["hill_assist"] = car.HillAssist
	}
	if car.BlindSpotMonitor != "" {
		updates["blind_spot_monitor"] = car.BlindSpotMonitor
	}
	if car.LaneDeparture != "" {
		updates["lane_departure"] = car.LaneDeparture
	}
	if car.AirConditioning != "" {
		updates["air_conditioning"] = car.AirConditioning
	}
	if car.ClimateControl != "" {
		updates["climate_control"] = car.ClimateControl
	}
	if car.SeatHeating != "" {
		updates["seat_heating"] = car.SeatHeating
	}
	if car.SeatVentilation != "" {
		updates["seat_ventilation"] = car.SeatVentilation
	}
	if car.SeatMassage != "" {
		updates["seat_massage"] = car.SeatMassage
	}
	if car.SteeringWheelHeating != "" {
		updates["steering_wheel_heating"] = car.SteeringWheelHeating
	}
	if car.Navigation != "" {
		updates["navigation"] = car.Navigation
	}
	if car.AudioSystem != "" {
		updates["audio_system"] = car.AudioSystem
	}
	if car.SpeakersCount != "" {
		updates["speakers_count"] = car.SpeakersCount
	}
	if car.Bluetooth != "" {
		updates["bluetooth"] = car.Bluetooth
	}
	if car.USB != "" {
		updates["usb"] = car.USB
	}
	if car.Aux != "" {
		updates["aux"] = car.Aux
	}
	if car.HeadlightType != "" {
		updates["headlight_type"] = car.HeadlightType
	}
	if car.FogLights != "" {
		updates["fog_lights"] = car.FogLights
	}
	if car.LEDLights != "" {
		updates["led_lights"] = car.LEDLights
	}
	if car.DaytimeRunning != "" {
		updates["daytime_running"] = car.DaytimeRunning
	}
	if car.OwnerCount > 0 {
		updates["owner_count"] = car.OwnerCount
	}
	if car.AccidentHistory != "" {
		updates["accident_history"] = car.AccidentHistory
	}
	if car.ServiceHistory != "" {
		updates["service_history"] = car.ServiceHistory
	}
	if car.WarrantyInfo != "" {
		updates["warranty_info"] = car.WarrantyInfo
	}
	if car.InspectionDate != "" {
		updates["inspection_date"] = car.InspectionDate
	}
	if car.InsuranceInfo != "" {
		updates["insurance_info"] = car.InsuranceInfo
	}
	if car.InteriorColor != "" {
		updates["interior_color"] = car.InteriorColor
	}
	if car.ExteriorColor != "" {
		updates["exterior_color"] = car.ExteriorColor
	}
	if car.Upholstery != "" {
		updates["upholstery"] = car.Upholstery
	}
	if car.Sunroof != "" {
		updates["sunroof"] = car.Sunroof
	}
	if car.PanoramicRoof != "" {
		updates["panoramic_roof"] = car.PanoramicRoof
	}
	if car.ViewCount > 0 {
		updates["view_count"] = car.ViewCount
	}
	if car.FavoriteCount > 0 {
		updates["favorite_count"] = car.FavoriteCount
	}
	if car.ContactInfo != "" {
		updates["contact_info"] = car.ContactInfo
	}
	if car.DealerInfo != "" {
		updates["dealer_info"] = car.DealerInfo
	}
	if car.Certification != "" {
		updates["certification"] = car.Certification
	}
	if car.ImageGallery != "" {
		updates["image_gallery"] = car.ImageGallery
	}
	if car.ImageCount > 0 {
		updates["image_count"] = car.ImageCount
	}
	if car.SeatCount != "" {
		updates["seat_count"] = car.SeatCount
	}
	if car.DoorCount != "" {
		updates["door_count"] = car.DoorCount
	}
	if car.TrunkVolume != "" {
		updates["trunk_volume"] = car.TrunkVolume
	}
	if car.FuelTankVolume != "" {
		updates["fuel_tank_volume"] = car.FuelTankVolume
	}
	if car.RecyclingFee != "" {
		updates["recycling_fee"] = car.RecyclingFee
	}
	if car.CustomsDuty != "" {
		updates["customs_duty"] = car.CustomsDuty
	}
	if car.CustomsFee > 0 {
		updates["customs_fee"] = car.CustomsFee
	}
	if car.RubPrice > 0 {
		updates["rub_price"] = car.RubPrice
	}
	if car.FinalPrice > 0 {
		updates["final_price"] = car.FinalPrice
	}

	// Обновляем first_registration_time - нормализуем и преобразуем в time.Time
	if car.FirstRegistrationTime != "" {
		if normalized, ok := domain.NormalizeFirstRegistrationDate(car.FirstRegistrationTime); ok {
			// Парсим нормализованную дату в time.Time для корректной записи в DATE колонку
			if parsedDate, err := time.Parse("2006-01-02", normalized); err == nil {
				updates["first_registration_time"] = parsedDate
				log.Printf("UpdateCar: first_registration_time нормализовано: '%s' -> '%s' (parsed to time.Time)", car.FirstRegistrationTime, normalized)
			} else {
				log.Printf("UpdateCar: first_registration_time не удалось распарсить в time.Time: '%s', error: %v", normalized, err)
			}
		} else {
			log.Printf("UpdateCar: first_registration_time не удалось нормализовать: '%s'", car.FirstRegistrationTime)
		}
	} else {
		log.Printf("UpdateCar: first_registration_time пустое, не обновляем")
	}

	if car.Link != "" {
		updates["link"] = car.Link
	}

	// Сохраняем mybrand_id, если он установлен (чтобы не потерять связь с брендом)
	// Если mybrand_id не установлен в car, то не обновляем его (сохраняем существующее значение)
	if car.MybrandID != nil {
		updates["mybrand_id"] = car.MybrandID
	}

	// Логируем first_registration_time ДО Updates
	if frt, ok := updates["first_registration_time"]; ok {
		log.Printf("UpdateCar: BEFORE Updates - first_registration_time='%v' (type=%T) для uuid=%s", frt, frt, car.UUID)
	}

	// Используем Table() вместо Model() чтобы избежать вызова хуков BeforeSave,
	// которые перезаписывают first_registration_time на nil
	result := r.db.WithContext(ctx).
		Table("cars").
		Where("uuid = ?", car.UUID).
		Updates(updates)
	
	if result.Error != nil {
		log.Printf("UpdateCar: ошибка при обновлении uuid=%s: %v", car.UUID, result.Error)
		return result.Error
	}
	
	log.Printf("UpdateCar: uuid=%s, rows_affected=%d, updates_count=%d", car.UUID, result.RowsAffected, len(updates))
	
	// Если first_registration_time был в updates, логируем
	if frt, ok := updates["first_registration_time"]; ok {
		log.Printf("UpdateCar: first_registration_time='%s' (type=%T) добавлен в updates для uuid=%s", frt, frt, car.UUID)
	} else {
		log.Printf("UpdateCar: first_registration_time НЕ в updates для uuid=%s", car.UUID)
	}
	
	return nil
}
