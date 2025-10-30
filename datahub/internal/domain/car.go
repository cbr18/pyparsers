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
	MybrandID         *string   `json:"mybrand_id" gorm:"type:uuid;index"`
	CreatedAt         time.Time `json:"created_at"`
	UpdatedAt         time.Time `json:"updated_at"`

	// Флаги и метаданные
	HasDetails         bool      `json:"has_details" gorm:"default:false"`
	LastDetailUpdate   time.Time `json:"last_detail_update"`

	// Дополнительные технические характеристики
	Power              string `json:"power"`                    // Мощность (л.с./кВт)
	Torque             string `json:"torque"`                   // Крутящий момент (Н·м)
	Acceleration       string `json:"acceleration"`             // Разгон до 100 км/ч (сек)
	MaxSpeed           string `json:"max_speed"`                // Максимальная скорость (км/ч)
	FuelConsumption    string `json:"fuel_consumption"`         // Расход топлива (л/100км)
	EmissionStandard   string `json:"emission_standard"`         // Экологический класс

	// Размеры и вес
	Length             string `json:"length"`                   // Длина (мм)
	Width              string `json:"width"`                    // Ширина (мм)
	Height             string `json:"height"`                   // Высота (мм)
	Wheelbase          string `json:"wheelbase"`                // Колесная база (мм)
	CurbWeight         string `json:"curb_weight"`              // Снаряженная масса (кг)
	GrossWeight        string `json:"gross_weight"`             // Полная масса (кг)

	// Двигатель и трансмиссия (для ДВС)
	EngineType         string `json:"engine_type"`              // Тип двигателя
	EngineCode         string `json:"engine_code"`              // Код двигателя
	CylinderCount      string `json:"cylinder_count"`            // Количество цилиндров
	ValveCount         string `json:"valve_count"`              // Количество клапанов
	CompressionRatio   string `json:"compression_ratio"`        // Степень сжатия
	TurboType          string `json:"turbo_type"`               // Тип турбонаддува

	// Электрические характеристики (для электромобилей)
	BatteryCapacity    string `json:"battery_capacity"`         // Емкость батареи (кВт·ч)
	ElectricRange      string `json:"electric_range"`           // Запас хода (км)
	ChargingTime       string `json:"charging_time"`            // Время зарядки
	FastChargeTime     string `json:"fast_charge_time"`        // Время быстрой зарядки
	ChargePortType     string `json:"charge_port_type"`        // Тип зарядного порта

	// Трансмиссия и привод
	TransmissionType   string `json:"transmission_type"`        // Тип коробки передач
	GearCount          string `json:"gear_count"`               // Количество передач
	DifferentialType   string `json:"differential_type"`         // Тип дифференциала

	// Подвеска и тормоза
	FrontSuspension    string `json:"front_suspension"`         // Передняя подвеска
	RearSuspension     string `json:"rear_suspension"`          // Задняя подвеска
	FrontBrakes        string `json:"front_brakes"`             // Передние тормоза
	RearBrakes         string `json:"rear_brakes"`             // Задние тормоза
	BrakeSystem        string `json:"brake_system"`             // Тормозная система

	// Колеса и шины
	WheelSize          string `json:"wheel_size"`               // Размер колес
	TireSize           string `json:"tire_size"`                // Размер шин
	WheelType          string `json:"wheel_type"`               // Тип колес
	TireType           string `json:"tire_type"`                 // Тип шин

	// Безопасность
	AirbagCount        string `json:"airbag_count"`             // Количество подушек безопасности
	ABS               string `json:"abs"`                       // АБС
	ESP               string `json:"esp"`                       // ESP
	TCS               string `json:"tcs"`                       // TCS
	HillAssist        string `json:"hill_assist"`              // Помощь при трогании на подъеме
	BlindSpotMonitor  string `json:"blind_spot_monitor"`       // Мониторинг слепых зон
	LaneDeparture     string `json:"lane_departure"`           // Система предупреждения о покидании полосы

	// Комфорт и удобство
	AirConditioning    string `json:"air_conditioning"`         // Кондиционер
	ClimateControl     string `json:"climate_control"`          // Климат-контроль
	SeatHeating        string `json:"seat_heating"`             // Подогрев сидений
	SeatVentilation    string `json:"seat_ventilation"`         // Вентиляция сидений
	SeatMassage        string `json:"seat_massage"`              // Массаж сидений
	SteeringWheelHeating string `json:"steering_wheel_heating"` // Подогрев руля

	// Мультимедиа и навигация
	Navigation         string `json:"navigation"`                // Навигация
	AudioSystem        string `json:"audio_system"`             // Аудиосистема
	SpeakersCount      string `json:"speakers_count"`           // Количество динамиков
	Bluetooth          string `json:"bluetooth"`                // Bluetooth
	USB                string `json:"usb"`                      // USB
	Aux                string `json:"aux"`                      // AUX

	// Освещение
	HeadlightType      string `json:"headlight_type"`           // Тип фар
	FogLights          string `json:"fog_lights"`               // Противотуманные фары
	LEDLights          string `json:"led_lights"`               // LED освещение
	DaytimeRunning     string `json:"daytime_running"`          // Дневные ходовые огни

	// История и состояние
	OwnerCount         int    `json:"owner_count"`              // Количество владельцев
	AccidentHistory    string `json:"accident_history"`         // История ДТП
	ServiceHistory     string `json:"service_history"`         // История обслуживания
	WarrantyInfo       string `json:"warranty_info"`             // Информация о гарантии
	InspectionDate     string `json:"inspection_date"`          // Дата техосмотра
	InsuranceInfo      string `json:"insurance_info"`           // Информация о страховке

	// Дополнительные детали
	InteriorColor      string `json:"interior_color"`            // Цвет салона
	ExteriorColor      string `json:"exterior_color"`            // Цвет кузова
	Upholstery         string `json:"upholstery"`                // Обивка салона
	Sunroof            string `json:"sunroof"`                   // Люк
	PanoramicRoof      string `json:"panoramic_roof"`           // Панорамная крыша

	// Дополнительные метаданные
	ViewCount          int    `json:"view_count"`                // Количество просмотров
	FavoriteCount      int    `json:"favorite_count"`           // Количество добавлений в избранное
	ContactInfo        string `json:"contact_info"`             // Контактная информация
	DealerInfo         string `json:"dealer_info"`              // Информация о дилере
	Certification      string `json:"certification"`            // Сертификация

	// Карусель изображений
	ImageGallery       string `json:"image_gallery"`            // Ссылки на изображения через пробел
	ImageCount         int    `json:"image_count"`              // Количество изображений

	// Дополнительные характеристики
	SeatCount          string `json:"seat_count"`               // Количество мест
	DoorCount          string `json:"door_count"`               // Количество дверей
	TrunkVolume        string `json:"trunk_volume"`              // Объем багажника
	FuelTankVolume     string `json:"fuel_tank_volume"`          // Объем топливного бака
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
