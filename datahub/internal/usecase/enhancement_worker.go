package usecase

import (
	"context"
	"datahub/internal/domain"
	"datahub/internal/infrastructure/external"
	"datahub/internal/repository"
	"fmt"
	"log"
	"strings"
	"sync"
	"time"
)

// EnhancementWorker — фоновый воркер для улучшения машин детальной информацией
type EnhancementWorker struct {
	repo               repository.CarRepository
	dongchediClient    *external.DongchediClient
	che168Client       *external.Che168Client
	translationService *TranslationService
	
	isRunning          bool
	stopChan           chan struct{}
	mu                 sync.Mutex
	
	batchSize          int
	delayBetweenBatches time.Duration
	delayBetweenCars   time.Duration
	maxConcurrent      int
}

func NewEnhancementWorker(repo repository.CarRepository, dongchediClient *external.DongchediClient, che168Client *external.Che168Client, translationService *TranslationService) *EnhancementWorker {
	return &EnhancementWorker{
		repo:               repo,
		dongchediClient:    dongchediClient,
		che168Client:       che168Client,
		translationService: translationService,
		stopChan:           make(chan struct{}),
		batchSize:           10,               // Обрабатываем по 10 машин за раз
		delayBetweenBatches: 5 * time.Minute,  // Пауза между батчами
		delayBetweenCars:    2 * time.Second,  // Пауза между машинами
		maxConcurrent:       7,                // Максимум 7 одновременных запросов
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
	log.Println("Enhancement worker started")
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
	log.Println("Starting enhancement batch processing...")

	// Получаем машины без детальной информации для всех источников
	sources := []string{"dongchedi", "che168"}
	var allCars []domain.Car
	
	for _, source := range sources {
		cars, err := w.repo.GetCarsWithoutDetails(ctx, source, w.batchSize/len(sources))
		if err != nil {
			log.Printf("Error getting cars without details for %s: %v", source, err)
			continue
		}
		allCars = append(allCars, cars...)
	}

	if len(allCars) == 0 {
		log.Println("No cars without details found")
		return 0, 0
	}

	log.Printf("Found %d cars without details, processing...", len(allCars))

	// Обрабатываем машины с ограничением параллелизма
	sem := make(chan struct{}, w.maxConcurrent)
	var wg sync.WaitGroup
	enhancedCount := 0
	var mu sync.Mutex

	for i, car := range allCars {
		wg.Add(1)
		sem <- struct{}{} // Захватываем слот

		go func(idx int, c domain.Car) {
			defer wg.Done()
			defer func() { <-sem }() // Освобождаем слот

			// Улучшаем машину
			if err := w.enhanceSingleCar(ctx, c); err != nil {
				log.Printf("[%d/%d] Error enhancing car %s (source: %s, car_id: %d): %v", idx+1, len(allCars), c.UUID, c.Source, c.CarID, err)
			} else {
				mu.Lock()
				enhancedCount++
				mu.Unlock()
				log.Printf("[%d/%d] Successfully enhanced car %s (source: %s, car_id: %d)", idx+1, len(allCars), c.UUID, c.Source, c.CarID)
			}

			// Пауза между машинами
			if idx < len(allCars)-1 {
				time.Sleep(w.delayBetweenCars)
			}
		}(i, car)
	}

	wg.Wait()
	log.Printf("Batch processing completed: enhanced %d out of %d cars", enhancedCount, len(allCars))
	return len(allCars), enhancedCount
}

// enhanceSingleCar — улучшает одну машину
func (w *EnhancementWorker) enhanceSingleCar(ctx context.Context, car domain.Car) error {
	// Создаем контекст с таймаутом
	enhanceCtx, cancel := context.WithTimeout(ctx, 10*time.Minute)
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

		enhancedCar, err = w.dongchediClient.EnhanceCar(enhanceCtx, skuID, carID)
	} else if car.Source == "che168" {
		enhancedCar, err = w.che168Client.EnhanceCar(enhanceCtx, car.CarID)
	} else {
		return fmt.Errorf("источник %s не поддерживает улучшение деталей", car.Source)
	}

	if err != nil {
		return fmt.Errorf("error calling enhance API: %w", err)
	}

	// Сохраняем оригинальные поля
	enhancedCar.UUID = car.UUID
	enhancedCar.CreatedAt = car.CreatedAt
	enhancedCar.UpdatedAt = time.Now()
	// Сохраняем mybrand_id из оригинальной машины, чтобы не потерять связь с брендом
	enhancedCar.MybrandID = car.MybrandID
	
	// Проверяем, что power был успешно распарсен перед установкой has_details
	// Это дополнительная проверка на случай, если парсер вернул данные без power
	hasPower := enhancedCar.Power != "" && strings.TrimSpace(enhancedCar.Power) != ""
	if hasPower {
		enhancedCar.HasDetails = true
		enhancedCar.LastDetailUpdate = time.Now()
	} else {
		// Если power не был распарсен, не устанавливаем has_details
		enhancedCar.HasDetails = false
		// Не обновляем last_detail_update, если парсинг не удался
		log.Printf("Car %s: power not parsed, keeping has_details=false", car.UUID)
	}

	// Переводим данные если сервис перевода доступен
	if w.translationService != nil && w.translationService.IsEnabled() {
		translatedCars, translateErr := w.translationService.TranslateCars(ctx, []domain.Car{*enhancedCar})
		if translateErr != nil {
			log.Printf("Translation failed for car %s, using original data: %v", car.UUID, translateErr)
		} else if len(translatedCars) > 0 {
			enhancedCar = &translatedCars[0]
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
		"is_running":                isRunning,
		"batch_size":                w.batchSize,
		"delay_between_batches_sec": w.delayBetweenBatches.Seconds(),
		"delay_between_cars_sec":    w.delayBetweenCars.Seconds(),
		"max_concurrent":            w.maxConcurrent,
		"cars_without_details":      carsWithoutDetails,
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
	if delayBetweenCars > 0 {
		w.delayBetweenCars = delayBetweenCars
	}
	if maxConcurrent > 0 {
		w.maxConcurrent = maxConcurrent
	}

	log.Printf("Enhancement worker config updated: batch_size=%d, delay_batches=%v, delay_cars=%v, max_concurrent=%d",
		w.batchSize, w.delayBetweenBatches, w.delayBetweenCars, w.maxConcurrent)
}


