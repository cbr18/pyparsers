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
	pickupPatterns      = []string{"%pickup%", "%пикап%", "%皮卡%"}
	electricFuelPatterns = []string{"%电动%", "%纯电%", "%electric%"}
)

const (
	pickupConditionTemplate   = "body_type ILIKE ? OR body_type ILIKE ? OR body_type LIKE ?"
	electricConditionTemplate = "fuel_type ILIKE ? OR fuel_type ILIKE ? OR fuel_type ILIKE ?"
)

func ApplyViewerFilters(query *gorm.DB) *gorm.DB {
	query = query.Where("(year IS NULL OR year = 0 OR year >= ?)", MinViewerYear)

	query = query.Where("(body_type IS NULL OR TRIM(body_type) = '' OR NOT ("+pickupConditionTemplate+"))",
		stringSliceToInterface(pickupPatterns)...)

	query = query.Where("(fuel_type IS NULL OR TRIM(fuel_type) = '' OR NOT ("+electricConditionTemplate+"))",
		stringSliceToInterface(electricFuelPatterns)...)
	query = query.Where("(battery_capacity IS NULL OR TRIM(battery_capacity) = '')")
	query = query.Where("(electric_range IS NULL OR TRIM(electric_range) = '')")

	return query
}

func ShouldKeepCar(car domain.Car) bool {
	if car.Year != 0 && car.Year < MinViewerYear {
		return false
	}

	if matchesAnyKeyword(car.BodyType, pickupPatterns) {
		return false
	}

	if matchesAnyKeyword(car.FuelType, electricFuelPatterns) {
		return false
	}

	if strings.TrimSpace(car.BatteryCapacity) != "" {
		return false
	}

	if strings.TrimSpace(car.ElectricRange) != "" {
		return false
	}

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

