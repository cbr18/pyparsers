package usecase

import (
	"context"
	"datahub/internal/domain"
	"datahub/internal/infrastructure/external"
	"datahub/internal/repository"
	"fmt"
	"log"
	"strconv"
	"time"
)

// EnhancementService — сервис для улучшения машин детальной информацией
type EnhancementService struct {
	repo              repository.CarRepository
	dongchediClient   *external.DongchediClient
	che168Client      *external.Che168Client
	translationService *TranslationService
}

func NewEnhancementService(repo repository.CarRepository, dongchediClient *external.DongchediClient, che168Client *external.Che168Client, translationService *TranslationService) *EnhancementService {
	return &EnhancementService{
		repo:              repo,
		dongchediClient:   dongchediClient,
		che168Client:      che168Client,
		translationService: translationService,
	}
}

// EnhanceCarsWithoutDetails — улучшает все машины без детальной информации
func (s *EnhancementService) EnhanceCarsWithoutDetails(ctx context.Context, source string, batchSize int) (int, error) {
	// Получаем машины без детальной информации
	cars, err := s.repo.GetCarsWithoutDetails(ctx, source, batchSize)
	if err != nil {
		return 0, fmt.Errorf("ошибка получения машин без деталей: %w", err)
	}

	if len(cars) == 0 {
		log.Printf("Нет машин без детальной информации для источника %s", source)
		return 0, nil
	}

	log.Printf("Найдено %d машин без детальной информации для источника %s", len(cars), source)

	enhancedCount := 0
	for _, car := range cars {
		// Пропускаем машины без sku_id или car_id
		if car.SkuID == "" && car.CarID == 0 {
			log.Printf("Пропускаем машину %s без sku_id и car_id", car.UUID)
			continue
		}

		// Улучшаем машину в зависимости от источника
		enhancedCar, err := s.enhanceSingleCar(ctx, car)
		if err != nil {
			log.Printf("Ошибка улучшения машины %s: %v", car.UUID, err)
			continue
		}

		// Переводим данные если сервис перевода доступен
		if s.translationService != nil && s.translationService.IsEnabled() {
			translatedCars, translateErr := s.translationService.TranslateCars(ctx, []domain.Car{*enhancedCar})
			if translateErr != nil {
				log.Printf("Ошибка перевода машины %s: %v", car.UUID, translateErr)
			} else if len(translatedCars) > 0 {
				enhancedCar = &translatedCars[0]
			}
		}

		// Обновляем машину в БД
		if err := s.repo.UpdateCar(ctx, *enhancedCar); err != nil {
			log.Printf("Ошибка обновления машины %s: %v", car.UUID, err)
			continue
		}

		enhancedCount++
		log.Printf("Успешно улучшена машина %s (%d/%d)", car.UUID, enhancedCount, len(cars))

		// Небольшая пауза между запросами
		time.Sleep(1 * time.Second)
	}

	log.Printf("Улучшено %d из %d машин для источника %s", enhancedCount, len(cars), source)
	return enhancedCount, nil
}

// enhanceSingleCar — улучшает одну машину
func (s *EnhancementService) enhanceSingleCar(ctx context.Context, car domain.Car) (*domain.Car, error) {
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

		enhancedCar, err = s.dongchediClient.EnhanceCar(enhanceCtx, skuID, carID)
	} else if car.Source == "che168" {
		enhancedCar, err = s.che168Client.EnhanceCar(enhanceCtx, car.CarID)
	} else {
		return nil, fmt.Errorf("источник %s не поддерживает улучшение деталей", car.Source)
	}

	if err != nil {
		return nil, fmt.Errorf("ошибка улучшения машины %s: %w", car.UUID, err)
	}

	// Сохраняем оригинальные поля
	enhancedCar.UUID = car.UUID
	enhancedCar.CreatedAt = car.CreatedAt
	enhancedCar.UpdatedAt = time.Now()
	// Сохраняем mybrand_id из оригинальной машины, чтобы не потерять связь с брендом
	enhancedCar.MybrandID = car.MybrandID

	return enhancedCar, nil
}

// BatchEnhanceCars — массовое улучшение машин
func (s *EnhancementService) BatchEnhanceCars(ctx context.Context, source string, carMappings map[string]string) (int, error) {
	var enhancedCars []domain.Car
	var err error

	// Вызываем массовое улучшение в зависимости от источника
	if source == "dongchedi" {
		enhancedCars, err = s.dongchediClient.BatchEnhanceCars(ctx, carMappings)
	} else if source == "che168" {
		// Преобразуем carMappings в carIDs для che168
		var carIDs []int64
		for _, carIDStr := range carMappings {
			if carID, parseErr := strconv.ParseInt(carIDStr, 10, 64); parseErr == nil {
				carIDs = append(carIDs, carID)
			}
		}
		enhancedCars, err = s.che168Client.BatchEnhanceCars(ctx, carIDs)
	} else {
		return 0, fmt.Errorf("источник %s не поддерживает массовое улучшение", source)
	}

	if err != nil {
		return 0, fmt.Errorf("ошибка массового улучшения: %w", err)
	}

	// Переводим данные если сервис перевода доступен
	if s.translationService != nil && s.translationService.IsEnabled() {
		translatedCars, translateErr := s.translationService.TranslateCars(ctx, enhancedCars)
		if translateErr != nil {
			log.Printf("Ошибка перевода при массовом улучшении: %v", translateErr)
		} else {
			enhancedCars = translatedCars
		}
	}

	// Обновляем машины в БД
	updatedCount := 0
	for _, car := range enhancedCars {
		if err := s.repo.UpdateCar(ctx, car); err != nil {
			log.Printf("Ошибка обновления машины %s: %v", car.UUID, err)
			continue
		}
		updatedCount++
	}

	log.Printf("Массово улучшено %d машин для источника %s", updatedCount, source)
	return updatedCount, nil
}

