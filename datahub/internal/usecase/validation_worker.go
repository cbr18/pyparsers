package usecase

import (
	"context"
	"datahub/internal/domain"
	"datahub/internal/infrastructure/external"
	"datahub/internal/repository"
	"fmt"
	"log"
	"sync"
	"time"
)

// ValidationWorker — фоновый воркер для валидации машин (проверка актуальности)
type ValidationWorker struct {
	repo            repository.CarRepository
	dongchediClient *external.DongchediClient
	che168Client    *external.Che168Client

	isRunning          bool
	stopChan           chan struct{}
	mu                 sync.Mutex

	batchSize          int
	delayBetweenBatches time.Duration
	delayBetweenCars   time.Duration
	maxConcurrent      int
	validationInterval time.Duration
}

func NewValidationWorker(repo repository.CarRepository, dongchediClient *external.DongchediClient, che168Client *external.Che168Client) *ValidationWorker {
	return &ValidationWorker{
		repo:                repo,
		dongchediClient:     dongchediClient,
		che168Client:        che168Client,
		stopChan:            make(chan struct{}),
		batchSize:           50,                // Обрабатываем по 50 машин за раз
		delayBetweenBatches: 2 * time.Minute,   // Пауза между батчами
		delayBetweenCars:    1 * time.Second,   // Пауза между машинами
		maxConcurrent:       5,                  // Максимум 5 одновременных запросов для каждого источника
		validationInterval:  6 * time.Hour,      // Интервал между полными циклами валидации
	}
}

// Start — запускает фоновый процесс валидации машин
func (w *ValidationWorker) Start() {
	w.mu.Lock()
	if w.isRunning {
		w.mu.Unlock()
		log.Println("Validation worker already running")
		return
	}
	w.isRunning = true
	w.mu.Unlock()

	go w.run()
	log.Println("Validation worker started")
}

// Stop — останавливает фоновый процесс
func (w *ValidationWorker) Stop() {
	w.mu.Lock()
	if !w.isRunning {
		w.mu.Unlock()
		log.Println("Validation worker not running")
		return
	}
	w.isRunning = false
	close(w.stopChan)
	w.stopChan = make(chan struct{})
	w.mu.Unlock()

	log.Println("Validation worker stopped")
}

// IsRunning — проверяет, запущен ли воркер
func (w *ValidationWorker) IsRunning() bool {
	w.mu.Lock()
	defer w.mu.Unlock()
	return w.isRunning
}

// run — основной цикл воркера
func (w *ValidationWorker) run() {
	for {
		select {
		case <-w.stopChan:
			log.Println("Validation worker received stop signal")
			return
		default:
			// Обрабатываем батч
			carsFound, carsProcessed := w.processBatch(context.Background())

			if carsFound == 0 {
				// Машин не было - делаем длинную паузу перед следующей проверкой
				log.Printf("No cars to validate, waiting %v before next check...", w.validationInterval)
				select {
				case <-w.stopChan:
					log.Println("Validation worker received stop signal")
					return
				case <-time.After(w.validationInterval):
					// Продолжаем цикл после паузы
				}
			} else if carsProcessed == 0 {
				// Машины были, но все не обработались (возможны временные ошибки)
				// Делаем короткую паузу и повторяем
				log.Println("Cars found but none processed (possible service errors), retrying soon...")
				select {
				case <-w.stopChan:
					log.Println("Validation worker received stop signal")
					return
				case <-time.After(30 * time.Second):
					// Короткая пауза перед повторной попыткой
				}
			} else {
				// Машины были обработаны - пауза между батчами
				select {
				case <-w.stopChan:
					log.Println("Validation worker received stop signal")
					return
				case <-time.After(w.delayBetweenBatches):
					// Продолжаем к следующему батчу
				}
			}
		}
	}
}

// processBatch — обрабатывает один батч машин для валидации
// Возвращает (количество найденных машин, количество успешно обработанных машин)
func (w *ValidationWorker) processBatch(ctx context.Context) (int, int) {
	log.Println("Starting validation batch processing...")

	// Получаем машины с is_available = true для всех источников
	sources := []string{"dongchedi", "che168"}
	var allCars []domain.Car

	for _, source := range sources {
		cars, err := w.repo.GetCarsForValidation(ctx, source, w.batchSize/len(sources))
		if err != nil {
			log.Printf("Error getting cars for validation for %s: %v", source, err)
			continue
		}
		allCars = append(allCars, cars...)
	}

	if len(allCars) == 0 {
		log.Println("No cars to validate found")
		return 0, 0
	}

	log.Printf("Found %d cars to validate, processing...", len(allCars))

	// Обрабатываем машины с ограничением параллелизма
	sem := make(chan struct{}, w.maxConcurrent)
	var wg sync.WaitGroup
	validatedCount := 0
	var mu sync.Mutex

	for i, car := range allCars {
		wg.Add(1)
		sem <- struct{}{} // Захватываем слот

		go func(idx int, c domain.Car) {
			defer wg.Done()
			defer func() { <-sem }() // Освобождаем слот

			// Валидируем машину
			if err := w.validateSingleCar(ctx, c); err != nil {
				log.Printf("[%d/%d] Error validating car %s (source: %s, car_id: %d): %v", idx+1, len(allCars), c.UUID, c.Source, c.CarID, err)
			} else {
				mu.Lock()
				validatedCount++
				mu.Unlock()
				log.Printf("[%d/%d] Successfully validated car %s (source: %s, car_id: %d)", idx+1, len(allCars), c.UUID, c.Source, c.CarID)
			}

			// Пауза между машинами
			if idx < len(allCars)-1 {
				time.Sleep(w.delayBetweenCars)
			}
		}(i, car)
	}

	wg.Wait()
	log.Printf("Batch validation completed: validated %d out of %d cars", validatedCount, len(allCars))
	return len(allCars), validatedCount
}

// ValidationWorkerConfig описывает параметры конфигурации воркера
type ValidationWorkerConfig struct {
	BatchSize             *int
	DelayBetweenBatches   *time.Duration
	DelayBetweenCars      *time.Duration
	MaxConcurrent         *int
	ValidationInterval    *time.Duration
}

// SetConfig — обновляет конфигурацию воркера
func (w *ValidationWorker) SetConfig(cfg ValidationWorkerConfig) {
	w.mu.Lock()
	defer w.mu.Unlock()

	if cfg.BatchSize != nil && *cfg.BatchSize > 0 {
		w.batchSize = *cfg.BatchSize
	}
	if cfg.DelayBetweenBatches != nil && *cfg.DelayBetweenBatches >= 0 {
		w.delayBetweenBatches = *cfg.DelayBetweenBatches
	}
	if cfg.DelayBetweenCars != nil && *cfg.DelayBetweenCars >= 0 {
		w.delayBetweenCars = *cfg.DelayBetweenCars
	}
	if cfg.MaxConcurrent != nil && *cfg.MaxConcurrent > 0 {
		w.maxConcurrent = *cfg.MaxConcurrent
	}
	if cfg.ValidationInterval != nil && *cfg.ValidationInterval >= 0 {
		w.validationInterval = *cfg.ValidationInterval
	}

	log.Printf("Validation worker config updated: batch_size=%d, delay_batches=%v, delay_cars=%v, max_concurrent=%d, validation_interval=%v",
		w.batchSize, w.delayBetweenBatches, w.delayBetweenCars, w.maxConcurrent, w.validationInterval)
}

// validateSingleCar — валидирует одну машину
func (w *ValidationWorker) validateSingleCar(ctx context.Context, car domain.Car) error {
	// Создаем контекст с таймаутом
	validateCtx, cancel := context.WithTimeout(ctx, 2*time.Minute)
	defer cancel()

	var checkedCar *domain.Car
	var err error

	// Проверяем машину в зависимости от источника
	if car.Source == "dongchedi" {
		skuID := car.SkuID
		if skuID == "" {
			skuID = fmt.Sprintf("%d", car.CarID)
		}
		checkedCar, err = w.dongchediClient.CheckCar(validateCtx, skuID)
	} else if car.Source == "che168" {
		// Для che168 используем car_id для формирования URL
		carURL := fmt.Sprintf("https://m.che168.com/cardetail/index?infoid=%d", car.CarID)
		checkedCar, err = w.che168Client.CheckCar(validateCtx, carURL)
	} else {
		return fmt.Errorf("источник %s не поддерживает валидацию", car.Source)
	}

	// Если произошла ошибка сети/таймаут - НЕ меняем статус машины
	// Это могла быть временная проблема, машина может быть доступна
	if err != nil {
		log.Printf("Car %s (source: %s, car_id: %d): ошибка при проверке, статус НЕ изменён: %v", car.UUID, car.Source, car.CarID, err)
		return fmt.Errorf("временная ошибка при проверке: %w", err)
	}

	// Если checkedCar == nil без ошибки - странная ситуация, логируем но не меняем статус
	if checkedCar == nil {
		log.Printf("Car %s (source: %s, car_id: %d): получен nil без ошибки, статус НЕ изменён", car.UUID, car.Source, car.CarID)
		return nil
	}

	// Если машина найдена, но помечена как продана (is_available=false от парсера) - помечаем как недоступную
	if !checkedCar.IsAvailable {
		car.IsAvailable = false
		car.UpdatedAt = time.Now()
		if err := w.repo.UpdateCar(ctx, car); err != nil {
			return fmt.Errorf("error updating car in DB: %w", err)
		}
		log.Printf("Car %s (source: %s, car_id: %d) marked as unavailable (sold - парсер вернул is_available=false)", car.UUID, car.Source, car.CarID)
		return nil
	}

	// Машина доступна - обновляем updated_at чтобы показать что проверка прошла
	car.UpdatedAt = time.Now()
	if err := w.repo.UpdateCar(ctx, car); err != nil {
		return fmt.Errorf("error updating car timestamp: %w", err)
	}
	return nil
}

// GetStatus — возвращает статус воркера
func (w *ValidationWorker) GetStatus(ctx context.Context) (map[string]interface{}, error) {
	w.mu.Lock()
	defer w.mu.Unlock()

	// Подсчитываем количество машин для валидации
	dongchediCount, _ := w.repo.CountCarsForValidation(ctx, "dongchedi")
	che168Count, _ := w.repo.CountCarsForValidation(ctx, "che168")

	return map[string]interface{}{
		"is_running":        w.isRunning,
		"batch_size":        w.batchSize,
		"delay_between_batches_sec": int(w.delayBetweenBatches.Seconds()),
		"delay_between_cars_sec":    int(w.delayBetweenCars.Seconds()),
		"max_concurrent":    w.maxConcurrent,
		"validation_interval_hours": int(w.validationInterval.Hours()),
		"cars_to_validate": map[string]int{
			"dongchedi": int(dongchediCount),
			"che168":    int(che168Count),
			"total":     int(dongchediCount + che168Count),
		},
	}, nil
}

