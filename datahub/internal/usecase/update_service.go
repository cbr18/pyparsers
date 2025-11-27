package usecase

import (
	"context"
	"datahub/internal/domain"
	"datahub/internal/filters"
	"datahub/internal/repository"
	"fmt"
	"math"
	"strconv"
)

// ExternalSourceClient — интерфейс для клиента внешнего источника (dongchedi, che168)
type ExternalSourceClient interface {
	FetchAll(ctx context.Context) ([]domain.Car, error)
	FetchIncremental(ctx context.Context, lastCars []domain.Car) ([]domain.Car, error)
	CheckCar(ctx context.Context, carIDorURL string) (*domain.Car, error)
}

// UpdateService — сервис для обновления данных из внешних источников
// repo — репозиторий БД, client — внешний источник
// sourceName — "dongchedi" или "che168"
type UpdateService struct {
	repo              repository.CarRepository
	client            ExternalSourceClient
	sourceName        string
	translationService *TranslationService
	priceCalculator   *PriceCalculator
}

func NewUpdateService(repo repository.CarRepository, client ExternalSourceClient, sourceName string) *UpdateService {
	return &UpdateService{repo: repo, client: client, sourceName: sourceName, translationService: nil, priceCalculator: nil}
}

// NewUpdateServiceWithTranslation создает UpdateService с поддержкой перевода
func NewUpdateServiceWithTranslation(repo repository.CarRepository, client ExternalSourceClient, sourceName string, translationService *TranslationService) *UpdateService {
	return &UpdateService{repo: repo, client: client, sourceName: sourceName, translationService: translationService, priceCalculator: nil}
}

// NewUpdateServiceWithPriceCalculator создает UpdateService с поддержкой калькуляции цен
func NewUpdateServiceWithPriceCalculator(repo repository.CarRepository, client ExternalSourceClient, sourceName string, translationService *TranslationService, priceCalculator *PriceCalculator) *UpdateService {
	return &UpdateService{repo: repo, client: client, sourceName: sourceName, translationService: translationService, priceCalculator: priceCalculator}
}

// FullUpdate — полное обновление: очищает устаревшие записи без деталей/доступности и сохраняет свежие
// Возвращает количество обновленных машин
func (s *UpdateService) FullUpdate(ctx context.Context) (int, error) {
	cars, err := s.client.FetchAll(ctx)
	if err != nil {
		return 0, err
	}
	
	// Переводим данные если сервис перевода доступен
	if s.translationService != nil && s.translationService.IsEnabled() {
		translatedCars, translateErr := s.translationService.TranslateCars(ctx, cars)
		if translateErr != nil {
			// Логируем ошибку, но продолжаем с исходными данными
			fmt.Printf("Translation failed, using original data: %v\n", translateErr)
		} else {
			cars = translatedCars
		}
	}
	
	// Рассчитываем цены в рублях
	s.calculateRubPrices(ctx, cars)
	
	if err := s.repo.DeleteUnavailableCars(ctx, s.sourceName); err != nil {
		return 0, err
	}
	if err := s.repo.CreateManyWithTranslation(ctx, cars, s.translationService); err != nil {
		return 0, err
	}
	return len(cars), nil
}

// IncrementalUpdate — инкрементальное обновление: добавляет только новые
func (s *UpdateService) IncrementalUpdate(ctx context.Context, lastN int) error {
	lastCars, err := s.repo.GetBySourceAndSort(ctx, s.sourceName, lastN)
	if err != nil {
		return err
	}
	newCars, err := s.client.FetchIncremental(ctx, lastCars)
	if err != nil {
		return err
	}
	
	// Если нет новых машин, просто возвращаем nil
	if len(newCars) == 0 {
		return nil
	}
	
	// Переводим данные если сервис перевода доступен
	if s.translationService != nil && s.translationService.IsEnabled() {
		translatedCars, translateErr := s.translationService.TranslateCars(ctx, newCars)
		if translateErr != nil {
			// Логируем ошибку, но продолжаем с исходными данными
			fmt.Printf("Translation failed, using original data: %v\n", translateErr)
		} else {
			newCars = translatedCars
		}
	}
	
	// Рассчитываем цены в рублях
	s.calculateRubPrices(ctx, newCars)
	
	// Используем CreateManyWithTranslation для создания машин и брендов с переводом
	err = s.repo.CreateManyWithTranslation(ctx, newCars, s.translationService)
	if err != nil {
		// Если произошла ошибка, возвращаем ее
		return err
	}
	
	return nil
}

// PartialUpdateError - ошибка, которая содержит информацию о частичном успехе обновления
type PartialUpdateError struct {
	OriginalError error
	SuccessCount  int
	TotalCount    int
}

// Error реализует интерфейс error
func (e *PartialUpdateError) Error() string {
	return fmt.Sprintf("частично успешное обновление: добавлено %d из %d записей, ошибка: %v", 
		e.SuccessCount, e.TotalCount, e.OriginalError)
}

// CheckCar — проверка машины по ID или URL
func (s *UpdateService) CheckCar(ctx context.Context, carIDorURL string) (*domain.Car, error) {
	return s.client.CheckCar(ctx, carIDorURL)
}

// SaveCars — сохраняет машин в БД
func (s *UpdateService) SaveCars(ctx context.Context, cars []domain.Car) error {
	if len(cars) == 0 {
		return nil
	}
	
	// Устанавливаем source для всех машин
	for i := range cars {
		cars[i].Source = s.sourceName
		// Применяем фильтр как дополнительную проверку (AND логика):
		// если парсер установил is_available=false, оставляем false
		// если парсер установил is_available=true, дополнительно проверяем фильтром
		// Это позволяет фильтровать пикапы/электрокары, но сохранять информацию от парсера о проданных машинах
		if cars[i].IsAvailable {
			cars[i].IsAvailable = filters.ShouldKeepCar(cars[i])
		}
	}
	
	// Рассчитываем цены в рублях
	s.calculateRubPrices(ctx, cars)
	
	return s.repo.CreateManyWithTranslation(ctx, cars, s.translationService)
}

// ClearSource — удалить все записи по источнику (для полного обновления)
func (s *UpdateService) ClearSource(ctx context.Context) error {
    return s.repo.DeleteBySource(ctx, s.sourceName)
}

// RepoGetBySourceAndSort — прокси к репозиторию для получения последних N машин по источнику
func (s *UpdateService) RepoGetBySourceAndSort(ctx context.Context, source string, limit int) ([]domain.Car, error) {
    // игнорируем входной source и используем конфигурированный для сервиса, чтобы не смешивать источники
    return s.repo.GetBySourceAndSort(ctx, s.sourceName, limit)
}

// ReplaceSource — атомарно заменяет все записи источника на новые
func (s *UpdateService) ReplaceSource(ctx context.Context, cars []domain.Car) error {
    // Переводим данные если сервис перевода доступен
    if s.translationService != nil && s.translationService.IsEnabled() {
        translatedCars, translateErr := s.translationService.TranslateCars(ctx, cars)
        if translateErr != nil {
            // Логируем ошибку, но продолжаем с исходными данными
            fmt.Printf("Translation failed, using original data: %v\n", translateErr)
        } else {
            cars = translatedCars
        }
    }
    
    // Нормализуем source на всякий
    for i := range cars {
        cars[i].Source = s.sourceName
    }
	// Рассчитываем цены в рублях
	s.calculateRubPrices(ctx, cars)
	
    return s.repo.ReplaceBySourceWithTranslation(ctx, s.sourceName, cars, s.translationService)
}


// AppendIncremental — добавляет новые записи с корректным sort_number
func (s *UpdateService) AppendIncremental(ctx context.Context, cars []domain.Car) error {
    if len(cars) == 0 {
        return nil
    }
    
    // Переводим данные если сервис перевода доступен
    if s.translationService != nil && s.translationService.IsEnabled() {
        translatedCars, translateErr := s.translationService.TranslateCars(ctx, cars)
        if translateErr != nil {
            // Логируем ошибку, но продолжаем с исходными данными
            fmt.Printf("Translation failed, using original data: %v\n", translateErr)
        } else {
            cars = translatedCars
        }
    }
    
    // Получим текущий максимум sort_number по источнику
    last, err := s.repo.GetBySourceAndSort(ctx, s.sourceName, 1)
    if err != nil {
        return err
    }
    currentMax := 0
    if len(last) == 1 {
        currentMax = last[0].SortNumber
    }
    for i := range cars {
        cars[i].Source = s.sourceName
        cars[i].SortNumber = currentMax + i + 1
    }
	// Рассчитываем цены в рублях
	s.calculateRubPrices(ctx, cars)
	
    return s.repo.CreateManyWithTranslation(ctx, cars, s.translationService)
}

// calculateRubPrices рассчитывает цены в рублях для всех машин
func (s *UpdateService) calculateRubPrices(ctx context.Context, cars []domain.Car) {
	if s.priceCalculator == nil {
		return
	}
	
	for i := range cars {
		if cars[i].Price != "" {
			rubPrice, err := s.priceCalculator.CalculateRubPrice(ctx, cars[i].Price)
			if err != nil {
				// Логируем ошибку, но продолжаем
				fmt.Printf("Ошибка расчета цены в рублях для машины %s: %v\n", cars[i].UUID, err)
			} else {
				cars[i].RubPrice = rubPrice
				cars[i].FinalPrice = rubPrice

				if cars[i].Power != "" && cars[i].EngineVolume != "" && (cars[i].Year > 0 || cars[i].FirstRegistrationTime != "") {
					totalPriceWithUtil, utilizationFee, utilErr := s.priceCalculator.CalculateUtilizationFeeAndAddToPrice(
						ctx,
						rubPrice,
						cars[i].Power,
						cars[i].EngineVolume,
						cars[i].Year,
						cars[i].FirstRegistrationTime,
					)
					if utilErr != nil {
						fmt.Printf("Ошибка расчета утильсбора для машины %s: %v\n", cars[i].UUID, utilErr)
					} else if utilizationFee > 0 {
						cars[i].FinalPrice = totalPriceWithUtil
						cars[i].RecyclingFee = strconv.FormatFloat(utilizationFee, 'f', 0, 64)
					}
				}

				if cars[i].EngineVolume != "" && (cars[i].Year > 0 || cars[i].FirstRegistrationTime != "") {
					customsDuty, dutyErr := s.priceCalculator.CalculateCustomsDuty(
						ctx,
						rubPrice,
						cars[i].EngineVolume,
						cars[i].Year,
						cars[i].FirstRegistrationTime,
					)
					if dutyErr != nil {
						fmt.Printf("Ошибка расчета таможенной пошлины для машины %s: %v\n", cars[i].UUID, dutyErr)
					} else if customsDuty > 0 {
						cars[i].FinalPrice = math.Round(cars[i].FinalPrice + customsDuty)
						cars[i].CustomsDuty = strconv.FormatFloat(customsDuty, 'f', 0, 64)
					}
				}

				// Рассчитываем таможенный сбор по rub_price
				customsFee, feeErr := s.priceCalculator.CalculateCustomsFee(ctx, rubPrice)
				if feeErr != nil {
					fmt.Printf("Ошибка расчета таможенного сбора для машины %s: %v\n", cars[i].UUID, feeErr)
				} else if customsFee > 0 {
					cars[i].CustomsFee = customsFee
					cars[i].FinalPrice = math.Round(cars[i].FinalPrice + customsFee)
					fmt.Printf("Car %s: добавлен таможенный сбор %.0f руб\n", cars[i].UUID, customsFee)
				}

				// Добавляем фиксированные надбавки: 80000 + 80000 = 160000 руб
				cars[i].FinalPrice = math.Round(cars[i].FinalPrice + 160000)
				fmt.Printf("Car %s: добавлены фиксированные надбавки 160000 руб, итоговая цена=%.0f\n", cars[i].UUID, cars[i].FinalPrice)
			}
		}
	}
}
