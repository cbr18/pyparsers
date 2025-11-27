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
	"time"
)

// EnhancementService — сервис для улучшения машин детальной информацией
type EnhancementService struct {
	repo              repository.CarRepository
	dongchediClient   *external.DongchediClient
	che168Client      *external.Che168Client
	translationService *TranslationService
	priceCalculator   *PriceCalculator
}

func NewEnhancementService(repo repository.CarRepository, dongchediClient *external.DongchediClient, che168Client *external.Che168Client, translationService *TranslationService, priceCalculator *PriceCalculator) *EnhancementService {
	return &EnhancementService{
		repo:              repo,
		dongchediClient:   dongchediClient,
		che168Client:      che168Client,
		translationService: translationService,
		priceCalculator:   priceCalculator,
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
		
		if s.priceCalculator != nil && priceToUse != "" {
			log.Printf("Car %s: расчет цены в рублях, исходная цена='%s'", car.UUID, priceToUse)
			rubPrice, err := s.priceCalculator.CalculateRubPrice(ctx, priceToUse)
			if err != nil {
				log.Printf("Ошибка расчета цены в рублях для машины %s: %v", car.UUID, err)
			} else {
				log.Printf("Car %s: рассчитана цена в рублях=%.2f", car.UUID, rubPrice)
				enhancedCar.RubPrice = rubPrice
				enhancedCar.FinalPrice = rubPrice
				
				// Добавляем утильсбор к цене, если есть мощность и объем двигателя
				// Возраст машины рассчитывается из first_registration_time (приоритет) или year
				if enhancedCar.Power != "" && enhancedCar.EngineVolume != "" && (enhancedCar.Year > 0 || enhancedCar.FirstRegistrationTime != "") {
					totalPrice, utilizationFee, err := s.priceCalculator.CalculateUtilizationFeeAndAddToPrice(
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

			// Возраст машины рассчитывается из first_registration_time (приоритет) или year
			if enhancedCar.EngineVolume != "" && (enhancedCar.Year > 0 || enhancedCar.FirstRegistrationTime != "") {
				customsDuty, dutyErr := s.priceCalculator.CalculateCustomsDuty(
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
			customsFee, feeErr := s.priceCalculator.CalculateCustomsFee(ctx, rubPrice)
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
			if s.priceCalculator == nil {
				log.Printf("Car %s: пропуск расчета цены - priceCalculator не инициализирован", car.UUID)
			} else if priceToUse == "" {
				log.Printf("Car %s: пропуск расчета цены - цена пустая (enhancedCar.Price='%s', car.Price='%s')", 
					car.UUID, enhancedCar.Price, car.Price)
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
	// Сохраняем оригинальную цену, если enhancedCar не имеет цены
	if enhancedCar.Price == "" && car.Price != "" {
		enhancedCar.Price = car.Price
		log.Printf("Car %s: восстановлена оригинальная цена '%s'", car.UUID, car.Price)
	}
	
	// Восстанавливаем остальные важные поля
	if enhancedCar.Year == 0 && car.Year > 0 {
		enhancedCar.Year = car.Year
	}
	
	if enhancedCar.Title == "" && car.Title != "" {
		enhancedCar.Title = car.Title
	}
	
	if enhancedCar.CarName == "" && car.CarName != "" {
		enhancedCar.CarName = car.CarName
	}
	
	if enhancedCar.BrandName == "" && car.BrandName != "" {
		enhancedCar.BrandName = car.BrandName
	}
	
	if enhancedCar.SeriesName == "" && car.SeriesName != "" {
		enhancedCar.SeriesName = car.SeriesName
	}
	
	if enhancedCar.Image == "" && car.Image != "" {
		enhancedCar.Image = car.Image
	}
	
	if enhancedCar.Link == "" && car.Link != "" {
		enhancedCar.Link = car.Link
	}

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

	// Рассчитываем цены в рублях для всех машин
	if s.priceCalculator != nil {
		for i := range enhancedCars {
			if enhancedCars[i].Price != "" {
				rubPrice, err := s.priceCalculator.CalculateRubPrice(ctx, enhancedCars[i].Price)
				if err != nil {
					log.Printf("Ошибка расчета цены в рублях для машины %s: %v", enhancedCars[i].UUID, err)
				} else {
					enhancedCars[i].RubPrice = rubPrice
					enhancedCars[i].FinalPrice = rubPrice
					
					// Добавляем утильсбор к цене, если есть мощность и объем двигателя
					// Возраст машины рассчитывается из first_registration_time (приоритет) или year
					if enhancedCars[i].Power != "" && enhancedCars[i].EngineVolume != "" && (enhancedCars[i].Year > 0 || enhancedCars[i].FirstRegistrationTime != "") {
						totalPrice, utilizationFee, err := s.priceCalculator.CalculateUtilizationFeeAndAddToPrice(
							ctx,
							rubPrice,
							enhancedCars[i].Power,
							enhancedCars[i].EngineVolume,
							enhancedCars[i].Year,
							enhancedCars[i].FirstRegistrationTime,
						)
						if err != nil {
							log.Printf("Ошибка расчета утильсбора для машины %s: %v", enhancedCars[i].UUID, err)
						} else {
							enhancedCars[i].FinalPrice = totalPrice
							if utilizationFee > 0 {
								enhancedCars[i].RecyclingFee = strconv.FormatFloat(utilizationFee, 'f', 0, 64)
							}
						}
					}
				}

				// Возраст машины рассчитывается из first_registration_time (приоритет) или year
				if enhancedCars[i].EngineVolume != "" && (enhancedCars[i].Year > 0 || enhancedCars[i].FirstRegistrationTime != "") {
					customsDuty, dutyErr := s.priceCalculator.CalculateCustomsDuty(
						ctx,
						rubPrice,
						enhancedCars[i].EngineVolume,
						enhancedCars[i].Year,
						enhancedCars[i].FirstRegistrationTime,
					)
					if dutyErr != nil {
						log.Printf("Ошибка расчета таможенной пошлины для машины %s: %v", enhancedCars[i].UUID, dutyErr)
					} else if customsDuty > 0 {
						enhancedCars[i].FinalPrice = math.Round(enhancedCars[i].FinalPrice + customsDuty)
						enhancedCars[i].CustomsDuty = strconv.FormatFloat(customsDuty, 'f', 0, 64)
						log.Printf("Car %s: добавлена таможенная пошлина %.0f руб", enhancedCars[i].UUID, customsDuty)
					}
				}

				// Рассчитываем таможенный сбор по rub_price
				customsFee, feeErr := s.priceCalculator.CalculateCustomsFee(ctx, rubPrice)
				if feeErr != nil {
					log.Printf("Ошибка расчета таможенного сбора для машины %s: %v", enhancedCars[i].UUID, feeErr)
				} else if customsFee > 0 {
					enhancedCars[i].CustomsFee = customsFee
					enhancedCars[i].FinalPrice = math.Round(enhancedCars[i].FinalPrice + customsFee)
					log.Printf("Car %s: добавлен таможенный сбор %.0f руб", enhancedCars[i].UUID, customsFee)
				}

				// Добавляем фиксированные надбавки: 80000 + 80000 = 160000 руб
				enhancedCars[i].FinalPrice = math.Round(enhancedCars[i].FinalPrice + 160000)
				log.Printf("Car %s: добавлены фиксированные надбавки 160000 руб, итоговая цена=%.0f", enhancedCars[i].UUID, enhancedCars[i].FinalPrice)
			}
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

