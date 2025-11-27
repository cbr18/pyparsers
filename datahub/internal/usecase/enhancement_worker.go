package usecase

import (
	"context"
	"datahub/internal/domain"
	"datahub/internal/infrastructure/external"
	"datahub/internal/repository"
	"fmt"
	"log"
	"math"
	"strconv"
	"strings"
	"sync"
	"time"
)

const (
	maxConcurrentPerSource = 5              // Максимум 5 машин одновременно для каждого источника
	delayBetweenSends      = 700 * time.Millisecond // 0.5-1 сек между отправками
	enhanceTimeout         = 5 * time.Minute        // Таймаут на улучшение одной машины
)

// EnhancementWorker — фоновый воркер для улучшения машин детальной информацией
type EnhancementWorker struct {
	repo               repository.CarRepository
	dongchediClient    *external.DongchediClient
	che168Client       *external.Che168Client
	translationService *TranslationService
	priceCalculator    *PriceCalculator
	
	isRunning          bool
	stopChan           chan struct{}
	mu                 sync.Mutex
	
	batchSize          int
	delayBetweenBatches time.Duration
	
	// Семафоры для ограничения параллельных запросов по источникам
	dongchediSemaphore chan struct{}
	che168Semaphore    chan struct{}
}

func NewEnhancementWorker(repo repository.CarRepository, dongchediClient *external.DongchediClient, che168Client *external.Che168Client, translationService *TranslationService, priceCalculator *PriceCalculator) *EnhancementWorker {
	return &EnhancementWorker{
		repo:               repo,
		dongchediClient:    dongchediClient,
		che168Client:       che168Client,
		translationService: translationService,
		priceCalculator:    priceCalculator,
		stopChan:           make(chan struct{}),
		batchSize:          10,               // Обрабатываем по 10 машин за раз (5+5)
		delayBetweenBatches: 1 * time.Minute,  // Пауза между батчами
		dongchediSemaphore: make(chan struct{}, maxConcurrentPerSource),
		che168Semaphore:    make(chan struct{}, maxConcurrentPerSource),
	}
}

// Start — запускает фоновый процесс улучшения машин
func (w *EnhancementWorker) Start() {
	w.mu.Lock()
	if w.isRunning {
		w.mu.Unlock()
		log.Println("Enhancement worker already running")
		return
	}
	w.isRunning = true
	w.mu.Unlock()

	go w.run()
	log.Println("Enhancement worker started (parallel mode: 5+5 concurrent)")
}

// Stop — останавливает фоновый процесс
func (w *EnhancementWorker) Stop() {
	w.mu.Lock()
	if !w.isRunning {
		w.mu.Unlock()
		log.Println("Enhancement worker not running")
		return
	}
	w.isRunning = false
	close(w.stopChan)
	w.stopChan = make(chan struct{})
	w.mu.Unlock()

	log.Println("Enhancement worker stopped")
}

// IsRunning — проверяет, запущен ли воркер
func (w *EnhancementWorker) IsRunning() bool {
	w.mu.Lock()
	defer w.mu.Unlock()
	return w.isRunning
}

// run — основной цикл воркера
func (w *EnhancementWorker) run() {
	for {
		select {
		case <-w.stopChan:
			log.Println("Enhancement worker received stop signal")
			return
		default:
			// Обрабатываем батч
			carsFound, carsProcessed := w.processBatch(context.Background())
			
			if carsFound == 0 {
				// Машин не было - делаем длинную паузу перед следующей проверкой
				log.Println("No cars found, waiting before next check...")
				select {
				case <-w.stopChan:
					log.Println("Enhancement worker received stop signal")
					return
				case <-time.After(w.delayBetweenBatches):
					// Продолжаем цикл после паузы
				}
			} else if carsProcessed == 0 {
				// Машины были, но все не обработались (возможны временные ошибки)
				// Делаем короткую паузу и повторяем
				log.Println("Cars found but none processed (possible service errors), retrying soon...")
				select {
				case <-w.stopChan:
					log.Println("Enhancement worker received stop signal")
					return
				case <-time.After(30 * time.Second):
					// Короткая пауза перед повторной попыткой
				}
			} else {
				// Машины были обработаны - сразу переходим к следующему батчу
			}
		}
	}
}

// processBatch — обрабатывает один батч машин без деталей
// Возвращает (количество найденных машин, количество успешно обработанных машин)
func (w *EnhancementWorker) processBatch(ctx context.Context) (int, int) {
	log.Println("Starting enhancement batch processing (parallel mode)...")

	// Получаем машины без детальной информации для всех источников
	sources := []string{"dongchedi", "che168"}
	carsBySource := make(map[string][]domain.Car)
	totalCars := 0
	
	for _, source := range sources {
		cars, err := w.repo.GetCarsWithoutDetails(ctx, source, w.batchSize/len(sources))
		if err != nil {
			log.Printf("Error getting cars without details for %s: %v", source, err)
			continue
		}
		log.Printf("Found %d cars without details for source %s", len(cars), source)
		carsBySource[source] = cars
		totalCars += len(cars)
	}

	if totalCars == 0 {
		log.Println("No cars without details found")
		return 0, 0
	}

	log.Printf("Found %d cars without details, processing in parallel (max %d per source)...", 
		totalCars, maxConcurrentPerSource)

	// Канал для сбора результатов
	type result struct {
		car     domain.Car
		success bool
		err     error
	}
	resultsChan := make(chan result, totalCars)

	// WaitGroup для ожидания завершения всех горутин
	var wg sync.WaitGroup

	// Запускаем обработку для каждого источника
	for source, cars := range carsBySource {
		for i, car := range cars {
			wg.Add(1)
			
			// Выбираем соответствующий семафор
			var semaphore chan struct{}
			if source == "dongchedi" {
				semaphore = w.dongchediSemaphore
			} else {
				semaphore = w.che168Semaphore
			}
			
			// Задержка между отправками (0.5-1 сек)
			if i > 0 {
				time.Sleep(delayBetweenSends)
			}
			
			go func(car domain.Car, sem chan struct{}) {
				defer wg.Done()
				
				// Захватываем слот в семафоре (блокируется если уже 5 активных)
				sem <- struct{}{}
				defer func() { <-sem }() // Освобождаем слот при завершении
				
				log.Printf("Processing car %s (source: %s, car_id: %d) - semaphore acquired", 
					car.UUID, car.Source, car.CarID)
				
				err := w.enhanceSingleCar(ctx, car)
				resultsChan <- result{car: car, success: err == nil, err: err}
			}(car, semaphore)
		}
	}

	// Ждем завершения всех горутин в отдельной горутине
	go func() {
		wg.Wait()
		close(resultsChan)
	}()

	// Собираем результаты
	enhancedCount := 0
	processedCount := 0
	for res := range resultsChan {
		processedCount++
		if res.success {
			enhancedCount++
			log.Printf("[%d/%d] Successfully enhanced car %s (source: %s)", 
				processedCount, totalCars, res.car.UUID, res.car.Source)
		} else {
			log.Printf("[%d/%d] Error enhancing car %s (source: %s): %v", 
				processedCount, totalCars, res.car.UUID, res.car.Source, res.err)
		}
	}

	log.Printf("Batch processing completed: enhanced %d out of %d cars", enhancedCount, totalCars)
	return totalCars, enhancedCount
}

// enhanceSingleCar — улучшает одну машину
func (w *EnhancementWorker) enhanceSingleCar(ctx context.Context, car domain.Car) error {
	// Создаем контекст с таймаутом 5 минут
	enhanceCtx, cancel := context.WithTimeout(ctx, enhanceTimeout)
	defer cancel()

	var enhancedCar *domain.Car
	var err error

	// Определяем клиент в зависимости от источника
	if car.Source == "dongchedi" {
		skuID := car.SkuID
		if skuID == "" {
			skuID = fmt.Sprintf("%d", car.CarID)
		}

		carID := ""
		if car.CarID != 0 {
			carID = fmt.Sprintf("%d", car.CarID)
		}

		log.Printf("Enhancing dongchedi car: sku_id=%s, car_id=%s", skuID, carID)
		enhancedCar, err = w.dongchediClient.EnhanceCar(enhanceCtx, skuID, carID)
	} else if car.Source == "che168" {
		log.Printf("Enhancing che168 car: car_id=%d", car.CarID)
		enhancedCar, err = w.che168Client.EnhanceCar(enhanceCtx, car.CarID)
	} else {
		return fmt.Errorf("источник %s не поддерживает улучшение деталей", car.Source)
	}

	if err != nil {
		log.Printf("Error calling enhance API for car %s (source: %s, car_id: %d): %v", car.UUID, car.Source, car.CarID, err)
		
		// Увеличиваем счетчик неудачных попыток
		car.FailedEnhancementAttempts++
		
		// Если достигли лимита (3 попытки), помечаем машину как недоступную
		if car.FailedEnhancementAttempts >= 3 {
			car.IsAvailable = false
			log.Printf("Car %s: достигнут лимит неудачных попыток (%d), помечаем как недоступную", car.UUID, car.FailedEnhancementAttempts)
		} else {
			log.Printf("Car %s: неудачная попытка улучшения (%d/3), продолжаем попытки", car.UUID, car.FailedEnhancementAttempts)
		}
		
		// Обновляем машину в БД с новым счетчиком и статусом
		car.UpdatedAt = time.Now()
		if updateErr := w.repo.UpdateCar(ctx, car); updateErr != nil {
			log.Printf("Error updating car %s after failed enhancement: %v", car.UUID, updateErr)
		}
		
		return fmt.Errorf("error calling enhance API: %w", err)
	}
	
	// Успешное улучшение - сбрасываем счетчик неудачных попыток
	enhancedCar.FailedEnhancementAttempts = 0
	
	// Проверяем, если pyparsers вернул информацию о недоступности машины
	// (например, машина продана или удалена - pyparsers вернул is_available=false)
	if !enhancedCar.IsAvailable {
		log.Printf("Car %s: pyparsers сообщил, что машина недоступна, помечаем is_available=false", car.UUID)
		// Сбрасываем счетчик, так как это не ошибка парсинга, а реальная недоступность
		enhancedCar.FailedEnhancementAttempts = 0
	}

	// Сохраняем оригинальные поля
	enhancedCar.UUID = car.UUID
	enhancedCar.CreatedAt = car.CreatedAt
	enhancedCar.UpdatedAt = time.Now()
	// Сохраняем mybrand_id из оригинальной машины, чтобы не потерять связь с брендом
	enhancedCar.MybrandID = car.MybrandID
	
	// Сохраняем оригинальную цену, если enhancedCar не имеет цены
	if enhancedCar.Price == "" && car.Price != "" {
		enhancedCar.Price = car.Price
		log.Printf("Car %s: восстановлена оригинальная цена '%s'", car.UUID, car.Price)
	}
	
	// Сохраняем оригинальный год, если enhancedCar не имеет года или год = 0
	if enhancedCar.Year == 0 && car.Year > 0 {
		enhancedCar.Year = car.Year
		log.Printf("Car %s: восстановлен оригинальный год %d", car.UUID, car.Year)
	}
	
	// Восстанавливаем оригинальные названия, если они были потеряны
	if enhancedCar.Title == "" && car.Title != "" {
		enhancedCar.Title = car.Title
		log.Printf("Car %s: восстановлен оригинальный title", car.UUID)
	}
	
	// Если title все еще пустой, формируем из brand_name + series_name
	if enhancedCar.Title == "" && enhancedCar.BrandName != "" && enhancedCar.SeriesName != "" {
		enhancedCar.Title = enhancedCar.BrandName + " " + enhancedCar.SeriesName
		log.Printf("Car %s: сформирован title из brand + series: '%s'", car.UUID, enhancedCar.Title)
	}
	
	if enhancedCar.CarName == "" && car.CarName != "" {
		enhancedCar.CarName = car.CarName
		log.Printf("Car %s: восстановлен оригинальный car_name", car.UUID)
	}
	
	// Если car_name пустой, используем series_name
	if enhancedCar.CarName == "" && enhancedCar.SeriesName != "" {
		enhancedCar.CarName = enhancedCar.SeriesName
		log.Printf("Car %s: car_name установлен из series_name: '%s'", car.UUID, enhancedCar.CarName)
	}
	
	if enhancedCar.BrandName == "" && car.BrandName != "" {
		enhancedCar.BrandName = car.BrandName
		log.Printf("Car %s: восстановлен оригинальный brand_name", car.UUID)
	}
	
	if enhancedCar.SeriesName == "" && car.SeriesName != "" {
		enhancedCar.SeriesName = car.SeriesName
		log.Printf("Car %s: восстановлен оригинальный series_name", car.UUID)
	}
	
	if enhancedCar.Image == "" && car.Image != "" {
		enhancedCar.Image = car.Image
	}
	
	if enhancedCar.Link == "" && car.Link != "" {
		enhancedCar.Link = car.Link
	}
	
	if enhancedCar.City == "" && car.City != "" {
		enhancedCar.City = car.City
	}
	
	if enhancedCar.Mileage == 0 && car.Mileage > 0 {
		enhancedCar.Mileage = car.Mileage
	}
	
	// Проверяем, что были успешно распарсены детальные данные
	// КРИТИЧНО: Power должен быть обязательно спарсен для has_details=true
	hasPower := enhancedCar.Power != "" && strings.TrimSpace(enhancedCar.Power) != ""
	
	if !hasPower {
		// Если Power не спарсился - has_details=false, даже если есть другие поля
		enhancedCar.HasDetails = false
		log.Printf("Car %s: Power не найден, has_details=false (другие поля игнорируются)", car.UUID)
	} else {
		// Power есть, проверяем что есть хотя бы еще одно значимое поле
		hasOtherDetails := (enhancedCar.EngineVolume != "" && strings.TrimSpace(enhancedCar.EngineVolume) != "") ||
		                   (enhancedCar.Transmission != "" && strings.TrimSpace(enhancedCar.Transmission) != "") ||
		                   (enhancedCar.FuelType != "" && strings.TrimSpace(enhancedCar.FuelType) != "") ||
		                   (enhancedCar.EngineType != "" && strings.TrimSpace(enhancedCar.EngineType) != "") ||
		                   (enhancedCar.DriveType != "" && strings.TrimSpace(enhancedCar.DriveType) != "") ||
		                   (enhancedCar.EmissionStandard != "" && strings.TrimSpace(enhancedCar.EmissionStandard) != "")
		
		if hasOtherDetails {
			enhancedCar.HasDetails = true
			enhancedCar.LastDetailUpdate = time.Now()
			log.Printf("Car %s: Power найден + другие детали, has_details=true", car.UUID)
		} else {
			enhancedCar.HasDetails = false
			log.Printf("Car %s: только Power, но нет других деталей, has_details=false", car.UUID)
		}
	}

	// Переводим данные если сервис перевода доступен
	if w.translationService != nil && w.translationService.IsEnabled() {
		translatedCars, translateErr := w.translationService.TranslateCars(ctx, []domain.Car{*enhancedCar})
		if translateErr != nil {
			log.Printf("Translation failed for car %s, using original data: %v", car.UUID, translateErr)
		} else if len(translatedCars) > 0 {
			enhancedCar = &translatedCars[0]
			// Восстанавливаем цену после перевода, если она была потеряна
			if enhancedCar.Price == "" && car.Price != "" {
				enhancedCar.Price = car.Price
				log.Printf("Car %s: восстановлена цена после перевода '%s'", car.UUID, car.Price)
			}
		}
	}

	// Рассчитываем цену в рублях, если есть цена
	// Используем цену из enhancedCar, если она есть, иначе из оригинальной машины
	priceToUse := enhancedCar.Price
	if priceToUse == "" {
		priceToUse = car.Price
		// Если использовали оригинальную цену, сохраняем её в enhancedCar
		if priceToUse != "" {
			enhancedCar.Price = priceToUse
			log.Printf("Car %s: использована оригинальная цена '%s'", car.UUID, priceToUse)
		}
	}
	
	if w.priceCalculator != nil && priceToUse != "" {
		log.Printf("Car %s: расчет цены в рублях, исходная цена='%s'", car.UUID, priceToUse)
		rubPrice, err := w.priceCalculator.CalculateRubPrice(ctx, priceToUse)
		if err != nil {
			log.Printf("Ошибка расчета цены в рублях для машины %s: %v", car.UUID, err)
		} else {
			log.Printf("Car %s: рассчитана цена в рублях=%.2f", car.UUID, rubPrice)
			enhancedCar.RubPrice = rubPrice
			enhancedCar.FinalPrice = rubPrice
			
			// Добавляем утильсбор к цене, если есть мощность и объем двигателя
			// Возраст машины рассчитывается из first_registration_time (приоритет) или year
			if enhancedCar.Power != "" && enhancedCar.EngineVolume != "" && (enhancedCar.Year > 0 || enhancedCar.FirstRegistrationTime != "") {
				totalPrice, utilizationFee, err := w.priceCalculator.CalculateUtilizationFeeAndAddToPrice(
					ctx,
					rubPrice,
					enhancedCar.Power,
					enhancedCar.EngineVolume,
					enhancedCar.Year,
					enhancedCar.FirstRegistrationTime,
				)
				if err != nil {
					log.Printf("Ошибка расчета утильсбора для машины %s: %v", car.UUID, err)
				} else {
					log.Printf("Car %s: итоговая цена с утильсбором=%.2f", car.UUID, totalPrice)
					enhancedCar.FinalPrice = totalPrice
					if utilizationFee > 0 {
						enhancedCar.RecyclingFee = strconv.FormatFloat(utilizationFee, 'f', 0, 64)
					}
				}
			}

			// Рассчитываем таможенную пошлину
			// Возраст машины рассчитывается из first_registration_time (приоритет) или year
			if enhancedCar.EngineVolume != "" && (enhancedCar.Year > 0 || enhancedCar.FirstRegistrationTime != "") {
				customsDuty, dutyErr := w.priceCalculator.CalculateCustomsDuty(
					ctx,
					rubPrice,
					enhancedCar.EngineVolume,
					enhancedCar.Year,
					enhancedCar.FirstRegistrationTime,
				)
				if dutyErr != nil {
					log.Printf("Ошибка расчета таможенной пошлины для машины %s: %v", car.UUID, dutyErr)
				} else if customsDuty > 0 {
					enhancedCar.FinalPrice = math.Round(enhancedCar.FinalPrice + customsDuty)
					enhancedCar.CustomsDuty = strconv.FormatFloat(customsDuty, 'f', 0, 64)
					log.Printf("Car %s: добавлена таможенная пошлина %.0f руб", car.UUID, customsDuty)
				}
			}

			// Рассчитываем таможенный сбор по rub_price
			customsFee, feeErr := w.priceCalculator.CalculateCustomsFee(ctx, rubPrice)
			if feeErr != nil {
				log.Printf("Ошибка расчета таможенного сбора для машины %s: %v", car.UUID, feeErr)
			} else if customsFee > 0 {
				enhancedCar.CustomsFee = customsFee
				enhancedCar.FinalPrice = math.Round(enhancedCar.FinalPrice + customsFee)
				log.Printf("Car %s: добавлен таможенный сбор %.0f руб", car.UUID, customsFee)
			}

			// Добавляем фиксированные надбавки: 80000 + 80000 = 160000 руб
			enhancedCar.FinalPrice = math.Round(enhancedCar.FinalPrice + 160000)
			log.Printf("Car %s: добавлены фиксированные надбавки 160000 руб, итоговая цена=%.0f", car.UUID, enhancedCar.FinalPrice)
		}
	} else {
		if w.priceCalculator == nil {
			log.Printf("Car %s: пропуск расчета цены - priceCalculator не инициализирован", car.UUID)
		} else if priceToUse == "" {
			log.Printf("Car %s: пропуск расчета цены - цена пустая (enhancedCar.Price='%s', car.Price='%s')", 
				car.UUID, enhancedCar.Price, car.Price)
		}
	}

	// Обновляем машину в БД
	if err := w.repo.UpdateCar(ctx, *enhancedCar); err != nil {
		return fmt.Errorf("error updating car in DB: %w", err)
	}

	return nil
}

// GetStatus — возвращает статус воркера
func (w *EnhancementWorker) GetStatus(ctx context.Context) (map[string]interface{}, error) {
	w.mu.Lock()
	isRunning := w.isRunning
	w.mu.Unlock()

	// Получаем количество машин без деталей для всех источников
	sources := []string{"dongchedi", "che168"}
	carsWithoutDetails := make(map[string]int)
	
	for _, source := range sources {
		cars, err := w.repo.GetCarsWithoutDetails(ctx, source, 1000)
		if err == nil {
			carsWithoutDetails[source] = len(cars)
		} else {
			carsWithoutDetails[source] = 0
		}
	}

	return map[string]interface{}{
		"is_running":                 isRunning,
		"batch_size":                 w.batchSize,
		"delay_between_batches_sec":  w.delayBetweenBatches.Seconds(),
		"max_concurrent_per_source":  maxConcurrentPerSource,
		"enhance_timeout_sec":        enhanceTimeout.Seconds(),
		"delay_between_sends_ms":     delayBetweenSends.Milliseconds(),
		"dongchedi_active":           len(w.dongchediSemaphore),
		"che168_active":              len(w.che168Semaphore),
		"cars_without_details":       carsWithoutDetails,
	}, nil
}

// SetConfig — обновляет конфигурацию воркера
func (w *EnhancementWorker) SetConfig(batchSize int, delayBetweenBatches time.Duration, delayBetweenCars time.Duration, maxConcurrent int) {
	w.mu.Lock()
	defer w.mu.Unlock()

	if batchSize > 0 {
		w.batchSize = batchSize
	}
	if delayBetweenBatches > 0 {
		w.delayBetweenBatches = delayBetweenBatches
	}
	// delayBetweenCars и maxConcurrent теперь константы, игнорируем

	log.Printf("Enhancement worker config updated: batch_size=%d, delay_batches=%v, max_concurrent_per_source=%d",
		w.batchSize, w.delayBetweenBatches, maxConcurrentPerSource)
}
