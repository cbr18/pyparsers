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
		// Ищем по полю name или orig_name
		err := tx.Where("name = ? OR orig_name = ?", car.BrandName, car.BrandName).First(&brand).Error

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
			err := tx.Where("name = ? OR orig_name = ?", filtered[i].BrandName, filtered[i].BrandName).First(&brand).Error
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
            err := tx.Where("name = ? OR orig_name = ?", dedup[i].BrandName, dedup[i].BrandName).First(&brand).Error
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

		// Обрабатываем бренд если есть
		if cars[i].BrandName != "" {
			var brand domain.Brand
			// Ищем по полю name или orig_name
			err := tx.Where("name = ? OR orig_name = ?", cars[i].BrandName, cars[i].BrandName).First(&brand).Error

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

	// Вставляем все машины батчами
	// С учетом 117+ полей, максимальный батч: 65535 / 117 ≈ 560
	const batchSize = 500
	for i := 0; i < len(cars); i += batchSize {
		end := i + batchSize
		if end > len(cars) {
			end = len(cars)
		}
		batch := cars[i:end]
		if err := tx.Clauses(clause.OnConflict{DoNothing: true}).CreateInBatches(&batch, batchSize).Error; err != nil {
			tx.Rollback()
			return err
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
func (r *CarRepository) UpdateCar(ctx context.Context, car domain.Car) error {
	car.UpdatedAt = time.Now()
	
	// Используем Updates вместо Save, чтобы обновить только указанные поля
	// и не трогать индексированные поля source и car_id
	return r.db.WithContext(ctx).
		Model(&domain.Car{}).
		Where("uuid = ?", car.UUID).
		Updates(map[string]interface{}{
			"has_details":           car.HasDetails,
			"last_detail_update":    car.LastDetailUpdate,
			"power":                 car.Power,
			"torque":                car.Torque,
			"acceleration":          car.Acceleration,
			"max_speed":             car.MaxSpeed,
			"fuel_consumption":      car.FuelConsumption,
			"emission_standard":     car.EmissionStandard,
			"length":                car.Length,
			"width":                 car.Width,
			"height":                car.Height,
			"wheelbase":             car.Wheelbase,
			"curb_weight":           car.CurbWeight,
			"gross_weight":          car.GrossWeight,
			"engine_type":           car.EngineType,
			"engine_code":           car.EngineCode,
			"cylinder_count":        car.CylinderCount,
			"valve_count":           car.ValveCount,
			"compression_ratio":     car.CompressionRatio,
			"turbo_type":            car.TurboType,
			"battery_capacity":      car.BatteryCapacity,
			"electric_range":        car.ElectricRange,
			"charging_time":         car.ChargingTime,
			"fast_charge_time":      car.FastChargeTime,
			"charge_port_type":      car.ChargePortType,
			"transmission_type":     car.TransmissionType,
			"gear_count":            car.GearCount,
			"differential_type":     car.DifferentialType,
			"front_suspension":      car.FrontSuspension,
			"rear_suspension":       car.RearSuspension,
			"front_brakes":          car.FrontBrakes,
			"rear_brakes":           car.RearBrakes,
			"brake_system":          car.BrakeSystem,
			"wheel_size":            car.WheelSize,
			"tire_size":             car.TireSize,
			"wheel_type":            car.WheelType,
			"tire_type":             car.TireType,
			"airbag_count":          car.AirbagCount,
			"abs":                   car.ABS,
			"esp":                   car.ESP,
			"tcs":                   car.TCS,
			"hill_assist":           car.HillAssist,
			"blind_spot_monitor":    car.BlindSpotMonitor,
			"lane_departure":        car.LaneDeparture,
			"air_conditioning":      car.AirConditioning,
			"climate_control":       car.ClimateControl,
			"seat_heating":          car.SeatHeating,
			"seat_ventilation":      car.SeatVentilation,
			"seat_massage":          car.SeatMassage,
			"steering_wheel_heating": car.SteeringWheelHeating,
			"navigation":            car.Navigation,
			"audio_system":          car.AudioSystem,
			"speakers_count":        car.SpeakersCount,
			"bluetooth":             car.Bluetooth,
			"usb":                   car.USB,
			"aux":                   car.Aux,
			"headlight_type":        car.HeadlightType,
			"fog_lights":            car.FogLights,
			"led_lights":            car.LEDLights,
			"daytime_running":       car.DaytimeRunning,
			"owner_count":           car.OwnerCount,
			"accident_history":      car.AccidentHistory,
			"service_history":       car.ServiceHistory,
			"warranty_info":         car.WarrantyInfo,
			"inspection_date":       car.InspectionDate,
			"insurance_info":        car.InsuranceInfo,
			"interior_color":        car.InteriorColor,
			"exterior_color":        car.ExteriorColor,
			"upholstery":            car.Upholstery,
			"sunroof":               car.Sunroof,
			"panoramic_roof":        car.PanoramicRoof,
			"view_count":            car.ViewCount,
			"favorite_count":        car.FavoriteCount,
			"contact_info":          car.ContactInfo,
			"dealer_info":           car.DealerInfo,
			"certification":         car.Certification,
			"image_gallery":         car.ImageGallery,
			"image_count":           car.ImageCount,
			"seat_count":            car.SeatCount,
			"door_count":            car.DoorCount,
			"trunk_volume":          car.TrunkVolume,
			"fuel_tank_volume":      car.FuelTankVolume,
			"updated_at":            car.UpdatedAt,
		}).Error
}
