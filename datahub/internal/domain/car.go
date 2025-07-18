package domain

import "time"

// Car — доменная модель автомобиля
// (можно расширять по мере необходимости)
type Car struct {
	UUID              string    `json:"uuid" gorm:"primaryKey"`
	Source            string    `json:"source"`
	CarID             int64     `json:"car_id"`
	SkuID             string    `json:"sku_id"`
	Title             string    `json:"title"`
	CarName           string    `json:"car_name"`
	Year              int       `json:"year"`
	Mileage           int32     `json:"mileage"`
	Price             string    `json:"price"`
	Image             string    `json:"image"`
	Link              string    `json:"link"`
	BrandName         string    `json:"brand_name"`
	SeriesName        string    `json:"series_name"`
	City              string    `json:"city"`
	ShopID            string    `json:"shop_id"`
	Tags              string    `json:"tags"`
	IsAvailable       bool      `json:"is_available"`
	SortNumber        int       `json:"sort_number"`
	BrandID           int       `json:"brand_id"`
	SeriesID          int       `json:"series_id"`
	CarSourceCityName string    `json:"car_source_city_name"`
	TagsV2            string    `json:"tags_v2"`
	Description       string    `json:"description"`
	Color             string    `json:"color"`
	Transmission      string    `json:"transmission"`
	FuelType          string    `json:"fuel_type"`
	EngineVolume      string    `json:"engine_volume"`
	BodyType          string    `json:"body_type"`
	DriveType         string    `json:"drive_type"`
	Condition         string    `json:"condition"`
	CreatedAt         time.Time `json:"created_at"`
	UpdatedAt         time.Time `json:"updated_at"`
}

// CarFilter — фильтры для поиска/выбора машин
type CarFilter struct {
	Source      *string
	BrandName   *string
	City        *string
	Year        *string
	IsAvailable *bool
	Search      *string // Поиск по названию/описанию
}
