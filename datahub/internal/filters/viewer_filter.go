package filters

import (
	"strings"

	"datahub/internal/domain"
	"gorm.io/gorm"
)

const (
	MinViewerYear = 2017
)

var (
	pickupPatterns = []string{"%pickup%", "%пикап%", "%皮卡%"}
)

const (
	pickupConditionTemplate = "body_type ILIKE ? OR body_type ILIKE ? OR body_type LIKE ?"
)

// ApplyViewerFilters применяет фильтры для отображения пользователям
// Фильтрует: год < 2017, пикапы, электромобили (только ДВС и гибриды показываем)
func ApplyViewerFilters(query *gorm.DB) *gorm.DB {
	// Фильтр по году
	query = query.Where("(year IS NULL OR year = 0 OR year >= ?)", MinViewerYear)

	// Фильтр по типу кузова (исключаем пикапы)
	query = query.Where("(body_type IS NULL OR TRIM(body_type) = '' OR NOT ("+pickupConditionTemplate+"))",
		stringSliceToInterface(pickupPatterns)...)

	// Фильтр по типу силовой установки - показываем только ДВС и гибриды
	// powertrain_type: ice, hybrid, phev - показываем
	// powertrain_type: electric - НЕ показываем
	// powertrain_type: unknown или пустой - показываем (пока не определено)
	query = query.Where("(powertrain_type IS NULL OR powertrain_type = '' OR powertrain_type != ?)", PowertrainElectric)

	return query
}

// ShouldKeepCar проверяет, должна ли машина быть показана пользователям
// Используется при импорте для предварительной фильтрации
func ShouldKeepCar(car domain.Car) bool {
	// Фильтр по году
	if car.Year != 0 && car.Year < MinViewerYear {
		return false
	}

	// Фильтр по типу кузова (исключаем пикапы)
	if matchesAnyKeyword(car.BodyType, pickupPatterns) {
		return false
	}

	// НЕ фильтруем по powertrain_type здесь - это делается позже после enhance
	// когда известен точный тип силовой установки

	return true
}

func stringSliceToInterface(values []string) []interface{} {
	out := make([]interface{}, len(values))
	for i, v := range values {
		out[i] = v
	}
	return out
}

func matchesAnyKeyword(value string, keywords []string) bool {
	lower := strings.ToLower(strings.TrimSpace(value))
	if lower == "" {
		return false
	}
	for _, keyword := range keywords {
		if strings.Contains(lower, strings.ToLower(strings.Trim(keyword, "%"))) {
			return true
		}
	}
	return false
}

