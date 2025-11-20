package usecase

import (
	"context"
	"encoding/csv"
	"errors"
	"io"
	"log"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"unicode"
	"unicode/utf8"

	"datahub/internal/domain"
	"datahub/internal/infrastructure/external"
)

// TranslationService — сервис для перевода автомобильных данных
type TranslationService struct {
	translatorClient *external.TranslatorClient
	enabled          bool
	knownBrands      []brandEntry
}

type brandEntry struct {
	canonical string
	lower     string
}

// NewTranslationService создает новый сервис перевода
func NewTranslationService(translatorClient *external.TranslatorClient, enabled bool, brandsFilePath string) *TranslationService {
	service := &TranslationService{
		translatorClient: translatorClient,
		enabled:          enabled,
	}

	if brandsFilePath != "" {
		if err := service.loadKnownBrands(brandsFilePath); err != nil && !errors.Is(err, os.ErrNotExist) {
			log.Printf("Failed to load known brands from %s: %v", brandsFilePath, err)
		}
	}

	return service
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
		"title":                  car.Title,
		"car_name":               car.CarName,
		"brand_name":             car.BrandName,
		"series_name":            car.SeriesName,
		"city":                   car.City,
		"car_source_city_name":  car.CarSourceCityName,
		"description":            car.Description,
		"color":                  car.Color,
		"transmission":           car.Transmission,
		"fuel_type":              car.FuelType,
		"engine_volume":         car.EngineVolume,
		"body_type":              car.BodyType,
		"drive_type":             car.DriveType,
		"condition":              car.Condition,
		// Дополнительные технические характеристики
		"emission_standard":      car.EmissionStandard,
		"engine_type":            car.EngineType,
		"engine_code":           car.EngineCode,
		"turbo_type":            car.TurboType,
		"transmission_type":     car.TransmissionType,
		"differential_type":     car.DifferentialType,
		// Подвеска и тормоза
		"front_suspension":       car.FrontSuspension,
		"rear_suspension":        car.RearSuspension,
		"front_brakes":           car.FrontBrakes,
		"rear_brakes":           car.RearBrakes,
		"brake_system":          car.BrakeSystem,
		// Колеса и шины
		"wheel_type":            car.WheelType,
		"tire_type":             car.TireType,
		// Безопасность
		"abs":                   car.ABS,
		"esp":                   car.ESP,
		"tcs":                   car.TCS,
		"hill_assist":           car.HillAssist,
		"blind_spot_monitor":    car.BlindSpotMonitor,
		"lane_departure":        car.LaneDeparture,
		// Комфорт
		"air_conditioning":      car.AirConditioning,
		"climate_control":       car.ClimateControl,
		"seat_heating":          car.SeatHeating,
		"seat_ventilation":      car.SeatVentilation,
		"seat_massage":          car.SeatMassage,
		"steering_wheel_heating": car.SteeringWheelHeating,
		// Мультимедиа
		"navigation":            car.Navigation,
		"audio_system":          car.AudioSystem,
		"bluetooth":             car.Bluetooth,
		"usb":                   car.USB,
		"aux":                   car.Aux,
		// Освещение
		"headlight_type":        car.HeadlightType,
		"fog_lights":            car.FogLights,
		"led_lights":            car.LEDLights,
		"daytime_running":       car.DaytimeRunning,
		// История
		"accident_history":      car.AccidentHistory,
		"service_history":       car.ServiceHistory,
		"warranty_info":         car.WarrantyInfo,
		"insurance_info":        car.InsuranceInfo,
		// Детали
		"interior_color":         car.InteriorColor,
		"exterior_color":         car.ExteriorColor,
		"upholstery":            car.Upholstery,
		"sunroof":               car.Sunroof,
		"panoramic_roof":         car.PanoramicRoof,
		// Метаданные
		"contact_info":          car.ContactInfo,
		"dealer_info":           car.DealerInfo,
		"certification":         car.Certification,
		// Электрические характеристики
		"charge_port_type":      car.ChargePortType,
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
	translatedCar.BrandName = s.normalizeBrand(getStringValue(translatedData, "brand_name", car.BrandName))
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
	// Дополнительные технические характеристики
	translatedCar.EmissionStandard = getStringValue(translatedData, "emission_standard", car.EmissionStandard)
	translatedCar.EngineType = getStringValue(translatedData, "engine_type", car.EngineType)
	translatedCar.EngineCode = getStringValue(translatedData, "engine_code", car.EngineCode)
	translatedCar.TurboType = getStringValue(translatedData, "turbo_type", car.TurboType)
	translatedCar.TransmissionType = getStringValue(translatedData, "transmission_type", car.TransmissionType)
	translatedCar.DifferentialType = getStringValue(translatedData, "differential_type", car.DifferentialType)
	// Подвеска и тормоза
	translatedCar.FrontSuspension = getStringValue(translatedData, "front_suspension", car.FrontSuspension)
	translatedCar.RearSuspension = getStringValue(translatedData, "rear_suspension", car.RearSuspension)
	translatedCar.FrontBrakes = getStringValue(translatedData, "front_brakes", car.FrontBrakes)
	translatedCar.RearBrakes = getStringValue(translatedData, "rear_brakes", car.RearBrakes)
	translatedCar.BrakeSystem = getStringValue(translatedData, "brake_system", car.BrakeSystem)
	// Колеса и шины
	translatedCar.WheelType = getStringValue(translatedData, "wheel_type", car.WheelType)
	translatedCar.TireType = getStringValue(translatedData, "tire_type", car.TireType)
	// Безопасность
	translatedCar.ABS = getStringValue(translatedData, "abs", car.ABS)
	translatedCar.ESP = getStringValue(translatedData, "esp", car.ESP)
	translatedCar.TCS = getStringValue(translatedData, "tcs", car.TCS)
	translatedCar.HillAssist = getStringValue(translatedData, "hill_assist", car.HillAssist)
	translatedCar.BlindSpotMonitor = getStringValue(translatedData, "blind_spot_monitor", car.BlindSpotMonitor)
	translatedCar.LaneDeparture = getStringValue(translatedData, "lane_departure", car.LaneDeparture)
	// Комфорт
	translatedCar.AirConditioning = getStringValue(translatedData, "air_conditioning", car.AirConditioning)
	translatedCar.ClimateControl = getStringValue(translatedData, "climate_control", car.ClimateControl)
	translatedCar.SeatHeating = getStringValue(translatedData, "seat_heating", car.SeatHeating)
	translatedCar.SeatVentilation = getStringValue(translatedData, "seat_ventilation", car.SeatVentilation)
	translatedCar.SeatMassage = getStringValue(translatedData, "seat_massage", car.SeatMassage)
	translatedCar.SteeringWheelHeating = getStringValue(translatedData, "steering_wheel_heating", car.SteeringWheelHeating)
	// Мультимедиа
	translatedCar.Navigation = getStringValue(translatedData, "navigation", car.Navigation)
	translatedCar.AudioSystem = getStringValue(translatedData, "audio_system", car.AudioSystem)
	translatedCar.Bluetooth = getStringValue(translatedData, "bluetooth", car.Bluetooth)
	translatedCar.USB = getStringValue(translatedData, "usb", car.USB)
	translatedCar.Aux = getStringValue(translatedData, "aux", car.Aux)
	// Освещение
	translatedCar.HeadlightType = getStringValue(translatedData, "headlight_type", car.HeadlightType)
	translatedCar.FogLights = getStringValue(translatedData, "fog_lights", car.FogLights)
	translatedCar.LEDLights = getStringValue(translatedData, "led_lights", car.LEDLights)
	translatedCar.DaytimeRunning = getStringValue(translatedData, "daytime_running", car.DaytimeRunning)
	// История
	translatedCar.AccidentHistory = getStringValue(translatedData, "accident_history", car.AccidentHistory)
	translatedCar.ServiceHistory = getStringValue(translatedData, "service_history", car.ServiceHistory)
	translatedCar.WarrantyInfo = getStringValue(translatedData, "warranty_info", car.WarrantyInfo)
	translatedCar.InsuranceInfo = getStringValue(translatedData, "insurance_info", car.InsuranceInfo)
	// Детали
	translatedCar.InteriorColor = getStringValue(translatedData, "interior_color", car.InteriorColor)
	translatedCar.ExteriorColor = getStringValue(translatedData, "exterior_color", car.ExteriorColor)
	translatedCar.Upholstery = getStringValue(translatedData, "upholstery", car.Upholstery)
	translatedCar.Sunroof = getStringValue(translatedData, "sunroof", car.Sunroof)
	translatedCar.PanoramicRoof = getStringValue(translatedData, "panoramic_roof", car.PanoramicRoof)
	// Метаданные
	translatedCar.ContactInfo = getStringValue(translatedData, "contact_info", car.ContactInfo)
	translatedCar.DealerInfo = getStringValue(translatedData, "dealer_info", car.DealerInfo)
	translatedCar.Certification = getStringValue(translatedData, "certification", car.Certification)
	// Электрические характеристики
	translatedCar.ChargePortType = getStringValue(translatedData, "charge_port_type", car.ChargePortType)

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
			"title":                  car.Title,
			"car_name":               car.CarName,
			"brand_name":             car.BrandName,
			"series_name":            car.SeriesName,
			"city":                   car.City,
			"car_source_city_name":  car.CarSourceCityName,
			"description":            car.Description,
			"color":                  car.Color,
			"transmission":           car.Transmission,
			"fuel_type":              car.FuelType,
			"engine_volume":         car.EngineVolume,
			"body_type":              car.BodyType,
			"drive_type":             car.DriveType,
			"condition":              car.Condition,
			// Дополнительные технические характеристики
			"emission_standard":      car.EmissionStandard,
			"engine_type":            car.EngineType,
			"engine_code":           car.EngineCode,
			"turbo_type":            car.TurboType,
			"transmission_type":     car.TransmissionType,
			"differential_type":     car.DifferentialType,
			// Подвеска и тормоза
			"front_suspension":       car.FrontSuspension,
			"rear_suspension":        car.RearSuspension,
			"front_brakes":           car.FrontBrakes,
			"rear_brakes":           car.RearBrakes,
			"brake_system":          car.BrakeSystem,
			// Колеса и шины
			"wheel_type":            car.WheelType,
			"tire_type":             car.TireType,
			// Безопасность
			"abs":                   car.ABS,
			"esp":                   car.ESP,
			"tcs":                   car.TCS,
			"hill_assist":           car.HillAssist,
			"blind_spot_monitor":    car.BlindSpotMonitor,
			"lane_departure":        car.LaneDeparture,
			// Комфорт
			"air_conditioning":      car.AirConditioning,
			"climate_control":       car.ClimateControl,
			"seat_heating":          car.SeatHeating,
			"seat_ventilation":      car.SeatVentilation,
			"seat_massage":          car.SeatMassage,
			"steering_wheel_heating": car.SteeringWheelHeating,
			// Мультимедиа
			"navigation":            car.Navigation,
			"audio_system":          car.AudioSystem,
			"bluetooth":             car.Bluetooth,
			"usb":                   car.USB,
			"aux":                   car.Aux,
			// Освещение
			"headlight_type":        car.HeadlightType,
			"fog_lights":            car.FogLights,
			"led_lights":            car.LEDLights,
			"daytime_running":       car.DaytimeRunning,
			// История
			"accident_history":      car.AccidentHistory,
			"service_history":       car.ServiceHistory,
			"warranty_info":          car.WarrantyInfo,
			"insurance_info":         car.InsuranceInfo,
			// Детали
			"interior_color":         car.InteriorColor,
			"exterior_color":         car.ExteriorColor,
			"upholstery":            car.Upholstery,
			"sunroof":               car.Sunroof,
			"panoramic_roof":         car.PanoramicRoof,
			// Метаданные
			"contact_info":          car.ContactInfo,
			"dealer_info":           car.DealerInfo,
			"certification":         car.Certification,
			// Электрические характеристики
			"charge_port_type":      car.ChargePortType,
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
			translatedCars[i].BrandName = s.normalizeBrand(getStringValue(record, "brand_name", car.BrandName))
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
			// Дополнительные технические характеристики
			translatedCars[i].EmissionStandard = getStringValue(record, "emission_standard", car.EmissionStandard)
			translatedCars[i].EngineType = getStringValue(record, "engine_type", car.EngineType)
			translatedCars[i].EngineCode = getStringValue(record, "engine_code", car.EngineCode)
			translatedCars[i].TurboType = getStringValue(record, "turbo_type", car.TurboType)
			translatedCars[i].TransmissionType = getStringValue(record, "transmission_type", car.TransmissionType)
			translatedCars[i].DifferentialType = getStringValue(record, "differential_type", car.DifferentialType)
			// Подвеска и тормоза
			translatedCars[i].FrontSuspension = getStringValue(record, "front_suspension", car.FrontSuspension)
			translatedCars[i].RearSuspension = getStringValue(record, "rear_suspension", car.RearSuspension)
			translatedCars[i].FrontBrakes = getStringValue(record, "front_brakes", car.FrontBrakes)
			translatedCars[i].RearBrakes = getStringValue(record, "rear_brakes", car.RearBrakes)
			translatedCars[i].BrakeSystem = getStringValue(record, "brake_system", car.BrakeSystem)
			// Колеса и шины
			translatedCars[i].WheelType = getStringValue(record, "wheel_type", car.WheelType)
			translatedCars[i].TireType = getStringValue(record, "tire_type", car.TireType)
			// Безопасность
			translatedCars[i].ABS = getStringValue(record, "abs", car.ABS)
			translatedCars[i].ESP = getStringValue(record, "esp", car.ESP)
			translatedCars[i].TCS = getStringValue(record, "tcs", car.TCS)
			translatedCars[i].HillAssist = getStringValue(record, "hill_assist", car.HillAssist)
			translatedCars[i].BlindSpotMonitor = getStringValue(record, "blind_spot_monitor", car.BlindSpotMonitor)
			translatedCars[i].LaneDeparture = getStringValue(record, "lane_departure", car.LaneDeparture)
			// Комфорт
			translatedCars[i].AirConditioning = getStringValue(record, "air_conditioning", car.AirConditioning)
			translatedCars[i].ClimateControl = getStringValue(record, "climate_control", car.ClimateControl)
			translatedCars[i].SeatHeating = getStringValue(record, "seat_heating", car.SeatHeating)
			translatedCars[i].SeatVentilation = getStringValue(record, "seat_ventilation", car.SeatVentilation)
			translatedCars[i].SeatMassage = getStringValue(record, "seat_massage", car.SeatMassage)
			translatedCars[i].SteeringWheelHeating = getStringValue(record, "steering_wheel_heating", car.SteeringWheelHeating)
			// Мультимедиа
			translatedCars[i].Navigation = getStringValue(record, "navigation", car.Navigation)
			translatedCars[i].AudioSystem = getStringValue(record, "audio_system", car.AudioSystem)
			translatedCars[i].Bluetooth = getStringValue(record, "bluetooth", car.Bluetooth)
			translatedCars[i].USB = getStringValue(record, "usb", car.USB)
			translatedCars[i].Aux = getStringValue(record, "aux", car.Aux)
			// Освещение
			translatedCars[i].HeadlightType = getStringValue(record, "headlight_type", car.HeadlightType)
			translatedCars[i].FogLights = getStringValue(record, "fog_lights", car.FogLights)
			translatedCars[i].LEDLights = getStringValue(record, "led_lights", car.LEDLights)
			translatedCars[i].DaytimeRunning = getStringValue(record, "daytime_running", car.DaytimeRunning)
			// История
			translatedCars[i].AccidentHistory = getStringValue(record, "accident_history", car.AccidentHistory)
			translatedCars[i].ServiceHistory = getStringValue(record, "service_history", car.ServiceHistory)
			translatedCars[i].WarrantyInfo = getStringValue(record, "warranty_info", car.WarrantyInfo)
			translatedCars[i].InsuranceInfo = getStringValue(record, "insurance_info", car.InsuranceInfo)
			// Детали
			translatedCars[i].InteriorColor = getStringValue(record, "interior_color", car.InteriorColor)
			translatedCars[i].ExteriorColor = getStringValue(record, "exterior_color", car.ExteriorColor)
			translatedCars[i].Upholstery = getStringValue(record, "upholstery", car.Upholstery)
			translatedCars[i].Sunroof = getStringValue(record, "sunroof", car.Sunroof)
			translatedCars[i].PanoramicRoof = getStringValue(record, "panoramic_roof", car.PanoramicRoof)
			// Метаданные
			translatedCars[i].ContactInfo = getStringValue(record, "contact_info", car.ContactInfo)
			translatedCars[i].DealerInfo = getStringValue(record, "dealer_info", car.DealerInfo)
			translatedCars[i].Certification = getStringValue(record, "certification", car.Certification)
			// Электрические характеристики
			translatedCars[i].ChargePortType = getStringValue(record, "charge_port_type", car.ChargePortType)
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
	return s.normalizeBrand(translatedBrandName), nil
}

func (s *TranslationService) loadKnownBrands(brandsFilePath string) error {
	absPath, err := filepath.Abs(brandsFilePath)
	if err != nil {
		return err
	}

	file, err := os.Open(absPath)
	if err != nil {
		return err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	var entries []brandEntry
	for {
		record, err := reader.Read()
		if err != nil {
			if errors.Is(err, io.EOF) {
				break
			}
			return err
		}

		if len(record) == 0 {
			continue
		}

		canonical := strings.TrimSpace(record[0])
		if canonical == "" || strings.EqualFold(canonical, "brand") {
			continue
		}

		entry := brandEntry{
			canonical: canonical,
			lower:     strings.ToLower(canonical),
		}
		entries = append(entries, entry)
	}

	if len(entries) == 0 {
		log.Printf("Known brands list is empty (%s)", absPath)
	}

	s.knownBrands = sortBrandEntries(entries)
	log.Printf("Loaded %d known brands from %s", len(s.knownBrands), absPath)
	return nil
}

func (s *TranslationService) normalizeBrand(translated string) string {
	if translated == "" || len(s.knownBrands) == 0 {
		return translated
	}

	normalized := strings.ToLower(strings.TrimSpace(translated))
	if normalized == "" {
		return translated
	}

	// Сначала проверяем точное совпадение
	for _, entry := range s.knownBrands {
		if normalized == entry.lower {
			return entry.canonical
		}
	}

	// Проверяем, начинается ли строка с известного бренда (для случаев типа "audi a4")
	for _, entry := range s.knownBrands {
		if strings.HasPrefix(normalized, entry.lower) {
			remainder := normalized[len(entry.lower):]
			if remainder == "" {
				return entry.canonical
			}

			// Проверяем, что после бренда идет разделитель (пробел, цифра, дефис и т.д.)
			r, _ := utf8.DecodeRuneInString(remainder)
			if unicode.IsSpace(r) || unicode.IsDigit(r) || isDelimiterRune(r) {
				return entry.canonical
			}
		}
	}

	// Если строка содержит несколько слов, проверяем каждое слово на наличие в списке брендов
	parts := strings.Fields(normalized)
	if len(parts) > 1 {
		for _, part := range parts {
			partLower := strings.ToLower(strings.TrimSpace(part))
			if partLower == "" {
				continue
			}
			
			// Проверяем точное совпадение слова с брендом
			for _, entry := range s.knownBrands {
				if partLower == entry.lower {
					return entry.canonical
				}
			}
		}
	}

	return translated
}

func sortBrandEntries(entries []brandEntry) []brandEntry {
	sort.SliceStable(entries, func(i, j int) bool {
		return utf8.RuneCountInString(entries[i].lower) > utf8.RuneCountInString(entries[j].lower)
	})
	return entries
}

func isDelimiterRune(r rune) bool {
	switch r {
	case '-', '/', '_', '(', '[', '{', '.', ',':
		return true
	default:
		return false
	}
}
