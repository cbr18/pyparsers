package filters

import (
	"strings"

	"datahub/internal/domain"
)

// Типы силовых установок
const (
	PowertrainICE     = "ice"     // ДВС (Internal Combustion Engine)
	PowertrainElectric = "electric" // Электромобиль
	PowertrainHybrid   = "hybrid"   // Гибрид (мягкий гибрид, обычный гибрид)
	PowertrainPHEV     = "phev"     // Плагин-гибрид (заряжается от сети)
	PowertrainUnknown  = "unknown"  // Не определён
)

// Ключевые слова для определения типа
var (
	electricKeywords = []string{
		"电动", "纯电", "纯电动", "electric", "ev", "bev",
		"pure electric", "全电动", "电驱动",
	}
	hybridKeywords = []string{
		"混动", "混合动力", "hybrid", "hev", "油电混合",
		"轻混", "48v", "微混", "弱混",
	}
	phevKeywords = []string{
		"插电混动", "插电式", "插混", "plug-in", "phev",
		"插电式混合动力", "可外接充电",
	}
)

// DeterminePowertrainType определяет тип силовой установки на основе всех доступных данных
func DeterminePowertrainType(car *domain.Car) string {
	// Признаки электромобиля
	hasBattery := strings.TrimSpace(car.BatteryCapacity) != ""
	hasElectricRange := strings.TrimSpace(car.ElectricRange) != ""
	hasChargingTime := strings.TrimSpace(car.ChargingTime) != ""
	
	// Признаки ДВС
	hasEngine := strings.TrimSpace(car.EngineVolume) != "" || strings.TrimSpace(car.EngineVolumeML) != ""
	hasFuelTank := strings.TrimSpace(car.FuelTankVolume) != ""
	hasFuelConsumption := strings.TrimSpace(car.FuelConsumption) != ""
	hasCylinders := strings.TrimSpace(car.CylinderCount) != ""
	hasEmission := strings.TrimSpace(car.EmissionStandard) != ""
	hasEngineCode := strings.TrimSpace(car.EngineCode) != ""
	
	hasICEsigns := hasEngine || hasFuelTank || hasFuelConsumption || hasCylinders || hasEmission || hasEngineCode
	hasEVsigns := hasBattery || hasElectricRange || hasChargingTime
	
	// Проверяем fuel_type на ключевые слова
	fuelType := strings.ToLower(strings.TrimSpace(car.FuelType))
	
	// 1. Проверяем на PHEV (плагин-гибрид) - приоритет высший
	if containsAny(fuelType, phevKeywords) {
		return PowertrainPHEV
	}
	
	// 2. Проверяем на гибрид
	if containsAny(fuelType, hybridKeywords) {
		return PowertrainHybrid
	}
	
	// 3. Проверяем на электромобиль по fuel_type
	if containsAny(fuelType, electricKeywords) {
		return PowertrainElectric
	}
	
	// 4. Анализируем по наличию характеристик
	if hasEVsigns && hasICEsigns {
		// Есть и батарея, и двигатель - это гибрид или PHEV
		// Если есть electric_range И charging_time - скорее PHEV
		if hasElectricRange && hasChargingTime {
			return PowertrainPHEV
		}
		return PowertrainHybrid
	}
	
	if hasEVsigns && !hasICEsigns {
		// Только электрические характеристики - электромобиль
		return PowertrainElectric
	}
	
	if hasICEsigns && !hasEVsigns {
		// Только ДВС характеристики - обычный автомобиль
		return PowertrainICE
	}
	
	// 5. Дополнительные проверки по engine_type
	engineType := strings.ToLower(strings.TrimSpace(car.EngineType))
	if containsAny(engineType, electricKeywords) {
		return PowertrainElectric
	}
	if containsAny(engineType, phevKeywords) {
		return PowertrainPHEV
	}
	if containsAny(engineType, hybridKeywords) {
		return PowertrainHybrid
	}
	
	// Если есть power но ничего не определили - скорее всего ДВС
	if strings.TrimSpace(car.Power) != "" {
		return PowertrainICE
	}
	
	return PowertrainUnknown
}

// containsAny проверяет, содержит ли строка любое из ключевых слов
func containsAny(s string, keywords []string) bool {
	for _, kw := range keywords {
		if strings.Contains(s, strings.ToLower(kw)) {
			return true
		}
	}
	return false
}

// IsICE проверяет, является ли машина с ДВС
func IsICE(car *domain.Car) bool {
	return car.PowertrainType == PowertrainICE
}

// IsElectric проверяет, является ли машина электромобилем
func IsElectric(car *domain.Car) bool {
	return car.PowertrainType == PowertrainElectric
}

// IsHybrid проверяет, является ли машина гибридом (любого типа)
func IsHybrid(car *domain.Car) bool {
	return car.PowertrainType == PowertrainHybrid || car.PowertrainType == PowertrainPHEV
}


