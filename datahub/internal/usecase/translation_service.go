package usecase

import (
	"context"
	"datahub/internal/domain"
	"datahub/internal/infrastructure/external"
	"log"
)

// TranslationService — сервис для перевода автомобильных данных
type TranslationService struct {
	translatorClient *external.TranslatorClient
	enabled          bool
}

// NewTranslationService создает новый сервис перевода
func NewTranslationService(translatorClient *external.TranslatorClient, enabled bool) *TranslationService {
	return &TranslationService{
		translatorClient: translatorClient,
		enabled:          enabled,
	}
}

// TranslateCar переводит данные автомобиля
func (s *TranslationService) TranslateCar(ctx context.Context, car *domain.Car) (*domain.Car, error) {
	if !s.enabled || s.translatorClient == nil {
		return car, nil
	}

	// Проверяем доступность сервиса перевода
	if err := s.translatorClient.HealthCheck(ctx); err != nil {
		log.Printf("Translation service is not available: %v", err)
		return car, nil
	}

	// Создаем карту для перевода
	carData := map[string]interface{}{
		"title":             car.Title,
		"car_name":          car.CarName,
		"brand_name":        car.BrandName,
		"series_name":       car.SeriesName,
		"city":              car.City,
		"car_source_city_name": car.CarSourceCityName,
		"description":       car.Description,
		"color":             car.Color,
		"transmission":      car.Transmission,
		"fuel_type":         car.FuelType,
		"engine_volume":     car.EngineVolume,
		"body_type":         car.BodyType,
		"drive_type":        car.DriveType,
		"condition":         car.Condition,
	}

	// Переводим данные на английский
	translatedData, err := s.translatorClient.TranslateJson(ctx, carData, "zh", "en")
	if err != nil {
		log.Printf("Failed to translate car data: %v", err)
		return car, nil
	}

	// Создаем копию автомобиля с переведенными данными
	translatedCar := *car
	translatedCar.Title = getStringValue(translatedData, "title", car.Title)
	translatedCar.CarName = getStringValue(translatedData, "car_name", car.CarName)
	translatedCar.BrandName = getStringValue(translatedData, "brand_name", car.BrandName)
	translatedCar.SeriesName = getStringValue(translatedData, "series_name", car.SeriesName)
	translatedCar.City = getStringValue(translatedData, "city", car.City)
	translatedCar.CarSourceCityName = getStringValue(translatedData, "car_source_city_name", car.CarSourceCityName)
	translatedCar.Description = getStringValue(translatedData, "description", car.Description)
	translatedCar.Color = getStringValue(translatedData, "color", car.Color)
	translatedCar.Transmission = getStringValue(translatedData, "transmission", car.Transmission)
	translatedCar.FuelType = getStringValue(translatedData, "fuel_type", car.FuelType)
	translatedCar.EngineVolume = getStringValue(translatedData, "engine_volume", car.EngineVolume)
	translatedCar.BodyType = getStringValue(translatedData, "body_type", car.BodyType)
	translatedCar.DriveType = getStringValue(translatedData, "drive_type", car.DriveType)
	translatedCar.Condition = getStringValue(translatedData, "condition", car.Condition)

	log.Printf("Successfully translated car: %s -> %s", car.CarName, translatedCar.CarName)
	return &translatedCar, nil
}

// TranslateCars переводит массив автомобилей
func (s *TranslationService) TranslateCars(ctx context.Context, cars []domain.Car) ([]domain.Car, error) {
	if !s.enabled || s.translatorClient == nil || len(cars) == 0 {
		return cars, nil
	}

	// Проверяем доступность сервиса перевода
	if err := s.translatorClient.HealthCheck(ctx); err != nil {
		log.Printf("Translation service is not available: %v", err)
		return cars, nil
	}

	// Конвертируем автомобили в карты для батчевого перевода
	records := make([]map[string]interface{}, len(cars))
	for i, car := range cars {
		records[i] = map[string]interface{}{
			"title":             car.Title,
			"car_name":          car.CarName,
			"brand_name":        car.BrandName,
			"series_name":       car.SeriesName,
			"city":              car.City,
			"car_source_city_name": car.CarSourceCityName,
			"description":       car.Description,
			"color":             car.Color,
			"transmission":      car.Transmission,
			"fuel_type":         car.FuelType,
			"engine_volume":     car.EngineVolume,
			"body_type":         car.BodyType,
			"drive_type":        car.DriveType,
			"condition":         car.Condition,
		}
	}

	// Переводим данные батчем на английский
	translatedRecords, err := s.translatorClient.TranslateDatabase(ctx, records, "zh", "en")
	if err != nil {
		log.Printf("Failed to translate cars batch: %v", err)
		return cars, nil
	}

	// Создаем переведенные автомобили
	translatedCars := make([]domain.Car, len(cars))
	for i, car := range cars {
		translatedCars[i] = car
		if i < len(translatedRecords) {
			record := translatedRecords[i]
			translatedCars[i].Title = getStringValue(record, "title", car.Title)
			translatedCars[i].CarName = getStringValue(record, "car_name", car.CarName)
			translatedCars[i].BrandName = getStringValue(record, "brand_name", car.BrandName)
			translatedCars[i].SeriesName = getStringValue(record, "series_name", car.SeriesName)
			translatedCars[i].City = getStringValue(record, "city", car.City)
			translatedCars[i].CarSourceCityName = getStringValue(record, "car_source_city_name", car.CarSourceCityName)
			translatedCars[i].Description = getStringValue(record, "description", car.Description)
			translatedCars[i].Color = getStringValue(record, "color", car.Color)
			translatedCars[i].Transmission = getStringValue(record, "transmission", car.Transmission)
			translatedCars[i].FuelType = getStringValue(record, "fuel_type", car.FuelType)
			translatedCars[i].EngineVolume = getStringValue(record, "engine_volume", car.EngineVolume)
			translatedCars[i].BodyType = getStringValue(record, "body_type", car.BodyType)
			translatedCars[i].DriveType = getStringValue(record, "drive_type", car.DriveType)
			translatedCars[i].Condition = getStringValue(record, "condition", car.Condition)
		}
	}

	log.Printf("Successfully translated %d cars", len(translatedCars))
	return translatedCars, nil
}

// getStringValue извлекает строковое значение из карты с fallback
func getStringValue(data map[string]interface{}, key, fallback string) string {
	if value, exists := data[key]; exists {
		if str, ok := value.(string); ok {
			return str
		}
	}
	return fallback
}

// IsEnabled возвращает статус включения перевода
func (s *TranslationService) IsEnabled() bool {
	return s.enabled
}

// SetEnabled устанавливает статус включения перевода
func (s *TranslationService) SetEnabled(enabled bool) {
	s.enabled = enabled
}

// TranslateBrandName переводит название бренда на английский
func (s *TranslationService) TranslateBrandName(ctx context.Context, brandName string) (string, error) {
	if !s.enabled || s.translatorClient == nil || brandName == "" {
		return brandName, nil
	}

	// Проверяем доступность сервиса перевода
	if err := s.translatorClient.HealthCheck(ctx); err != nil {
		log.Printf("Translation service is not available for brand translation: %v", err)
		return brandName, nil
	}

	// Создаем карту для перевода только названия бренда
	brandData := map[string]interface{}{
		"brand_name": brandName,
	}

	// Переводим на английский
	translatedData, err := s.translatorClient.TranslateJson(ctx, brandData, "zh", "en")
	if err != nil {
		log.Printf("Failed to translate brand name: %v", err)
		return brandName, nil
	}

	translatedBrandName := getStringValue(translatedData, "brand_name", brandName)
	log.Printf("Successfully translated brand: %s -> %s", brandName, translatedBrandName)
	return translatedBrandName, nil
}
