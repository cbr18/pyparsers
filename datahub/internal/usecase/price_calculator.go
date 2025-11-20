package usecase

import (
	"context"
	"datahub/internal/infrastructure/external"
	"fmt"
	"log"
	"math"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"
)

// PriceCalculator — сервис для калькуляции цен в рублях
type PriceCalculator struct {
	cbrClient      *external.CBRClient
	cnyRate        float64
	lastUpdate     time.Time
	mu             sync.RWMutex
	updateInterval time.Duration
}

// NewPriceCalculator создает новый сервис калькуляции цен
func NewPriceCalculator(cbrClient *external.CBRClient) *PriceCalculator {
	return &PriceCalculator{
		cbrClient:      cbrClient,
		updateInterval: 12 * time.Hour,
	}
}

// Start запускает фоновое обновление курса валют
func (pc *PriceCalculator) Start(ctx context.Context) {
	// Первоначальная загрузка курса
	if err := pc.updateCNYRate(ctx); err != nil {
		log.Printf("Ошибка первоначальной загрузки курса юаня: %v", err)
	}

	// Запускаем периодическое обновление
	go pc.run(ctx)
}

// run — фоновый процесс обновления курса
func (pc *PriceCalculator) run(ctx context.Context) {
	ticker := time.NewTicker(pc.updateInterval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			if err := pc.updateCNYRate(ctx); err != nil {
				log.Printf("Ошибка обновления курса юаня: %v", err)
			}
		}
	}
}

// updateCNYRate обновляет курс юаня
func (pc *PriceCalculator) updateCNYRate(ctx context.Context) error {
	rate, err := pc.cbrClient.GetCNYRate(ctx)
	if err != nil {
		return err
	}

	pc.mu.Lock()
	pc.cnyRate = rate
	pc.lastUpdate = time.Now()
	pc.mu.Unlock()

	log.Printf("Курс юаня обновлен: %.4f руб за 1 юань", rate)
	return nil
}

// CalculateRubPrice вычисляет цену в рублях из цены в wan юаней (万元)
// priceStr может содержать цену в формате "12.5" (означает 12.5万 = 125,000 юаней)
func (pc *PriceCalculator) CalculateRubPrice(ctx context.Context, priceStr string) (float64, error) {
	if priceStr == "" {
		log.Printf("[CalculateRubPrice] Цена пустая, возвращаем 0")
		return 0, nil
	}

	log.Printf("[CalculateRubPrice] Начинаем расчет для цены: '%s'", priceStr)

	// Получаем актуальный курс
	pc.mu.RLock()
	cnyRate := pc.cnyRate
	pc.mu.RUnlock()

	log.Printf("[CalculateRubPrice] Текущий курс CNY: %.4f", cnyRate)

	// Если курс не загружен, пытаемся загрузить
	if cnyRate == 0 {
		log.Printf("[CalculateRubPrice] Курс CNY не загружен, пытаемся загрузить...")
		if err := pc.updateCNYRate(ctx); err != nil {
			log.Printf("[CalculateRubPrice] ОШИБКА загрузки курса: %v", err)
			return 0, fmt.Errorf("не удалось получить курс юаня: %w", err)
		}
		pc.mu.RLock()
		cnyRate = pc.cnyRate
		pc.mu.RUnlock()
		log.Printf("[CalculateRubPrice] Курс CNY загружен: %.4f", cnyRate)
	}

	// Парсим цену из строки
	priceInMillionYuan, err := pc.parsePriceFromString(priceStr)
	if err != nil {
		log.Printf("[CalculateRubPrice] ОШИБКА парсинга цены '%s': %v", priceStr, err)
		return 0, fmt.Errorf("ошибка парсинга цены: %w", err)
	}

	log.Printf("[CalculateRubPrice] Цена в млн юаней: %.6f", priceInMillionYuan)

	if priceInMillionYuan == 0 {
		log.Printf("[CalculateRubPrice] Цена в млн юаней = 0, возвращаем 0")
		return 0, nil
	}

	// Вычисляем цену в рублях: курс * цена_в_wan_юаней * 10_000
	// В Китае цены указываются в 万 (wan) = 10,000 юаней
	rubPrice := cnyRate * priceInMillionYuan * 10000
	
	// Применяем рыночный множитель (покупаем не по курсу ЦБ)
	rubPrice = rubPrice * 1.117
	
	// Округляем до целых
	rubPrice = math.Round(rubPrice)

	log.Printf("[CalculateRubPrice] Итоговая цена в рублях: %.0f (курс %.4f * цена %.6f wan * 10000 * 1.117)", rubPrice, cnyRate, priceInMillionYuan)

	return rubPrice, nil
}

// parsePriceFromString парсит цену из строки
// Поддерживает форматы: "12.5" (в wan/万), "12.5万", числа интерпретируются как wan (10,000 юаней)
func (pc *PriceCalculator) parsePriceFromString(priceStr string) (float64, error) {
	originalPriceStr := priceStr
	priceStr = strings.TrimSpace(priceStr)
	if priceStr == "" {
		log.Printf("[parsePriceFromString] Пустая строка цены")
		return 0, nil
	}

	log.Printf("[parsePriceFromString] Парсим цену: '%s'", originalPriceStr)

	// Проверяем наличие индикаторов миллионов
	isMillion := false
	indicators := []string{"mln", "млн", "万", "million", "million yuan", "mln youan"}
	priceLower := strings.ToLower(priceStr)
	
	for _, indicator := range indicators {
		if strings.Contains(priceLower, strings.ToLower(indicator)) {
			isMillion = true
			log.Printf("[parsePriceFromString] Найден индикатор миллионов: '%s'", indicator)
			break
		}
	}

	// Извлекаем число из строки
	// Ищем число (может быть с точкой)
	re := regexp.MustCompile(`(\d+\.?\d*)`)
	matches := re.FindStringSubmatch(priceStr)
	if len(matches) < 2 {
		log.Printf("[parsePriceFromString] ОШИБКА: не удалось извлечь число из строки: '%s'", priceStr)
		return 0, fmt.Errorf("не удалось извлечь число из строки: %s", priceStr)
	}

	log.Printf("[parsePriceFromString] Извлечено число: '%s'", matches[1])

	price, err := strconv.ParseFloat(matches[1], 64)
	if err != nil {
		log.Printf("[parsePriceFromString] ОШИБКА парсинга числа '%s': %v", matches[1], err)
		return 0, fmt.Errorf("ошибка парсинга числа: %w", err)
	}

	log.Printf("[parsePriceFromString] Распарсенное число: %.6f, isMillion=%v", price, isMillion)

	// Если это не миллионы, но есть иероглиф "万" (10 тысяч), умножаем на 0.1
	if strings.Contains(priceStr, "万") && !isMillion {
		price = price * 0.1 // 万 = 10,000, значит 1万 = 0.1 млн
		isMillion = true
		log.Printf("[parsePriceFromString] Обнаружен иероглиф 万, цена после преобразования: %.6f млн", price)
	}

	// Если не миллионы, но число большое (> 1000), возможно это уже в юанях, делим на 1_000_000
	if !isMillion && price > 1000 {
		originalPrice := price
		price = price / 1000000
		isMillion = true
		log.Printf("[parsePriceFromString] Число > 1000, предполагаем что это юани. Преобразуем %.0f -> %.6f млн", originalPrice, price)
	}

	log.Printf("[parsePriceFromString] Итоговая цена: %.6f млн юаней", price)

	return price, nil
}

// GetCNYRate возвращает текущий курс юаня
func (pc *PriceCalculator) GetCNYRate() float64 {
	pc.mu.RLock()
	defer pc.mu.RUnlock()
	return pc.cnyRate
}

// GetLastUpdateTime возвращает время последнего обновления курса
func (pc *PriceCalculator) GetLastUpdateTime() time.Time {
	pc.mu.RLock()
	defer pc.mu.RUnlock()
	return pc.lastUpdate
}

// FeeData — структура для хранения тарифов одной категории
type FeeData struct {
	HorseMin, HorseMax   int
	FeeBeforeDec2025Young, FeeBeforeDec2025Old float64
	FeeAfterDec2025Young, FeeAfterDec2025Old   float64
	FeeAfterJan2026Young, FeeAfterJan2026Old   float64
}

var (
	fees1to2L = []FeeData{
		{0, 160, 667400, 1174000, 667400, 1174000, 800800, 1408800},
		{160, 190, 667400, 1174000, 750000, 1244000, 900000, 1492000},
		{190, 220, 667400, 1174000, 794000, 1320000, 952800, 1584000},
		{220, 250, 667400, 1174000, 842000, 1398000, 1010400, 1677600},
		{250, 280, 667400, 1174000, 952000, 1532000, 1142000, 1828000},
		{280, 310, 667400, 1174000, 1076000, 1676000, 1291200, 2001200},
		{310, 340, 667400, 1174000, 1216000, 1836000, 1459200, 2203200},
	}

	fees2to3L = []FeeData{
		{0, 160, 1875400, 2839400, 1875400, 2839400, 2250400, 3407200},
		{160, 190, 1875400, 2839400, 1922000, 2888000, 2308600, 3456200},
		{190, 220, 1875400, 2839400, 1970000, 2960000, 2397000, 3552000},
		{220, 250, 1875400, 2839400, 2000000, 3020000, 2420400, 3552000},
		{250, 280, 1875400, 2839400, 2052000, 3123000, 2520600, 3724000},
		{280, 310, 1875400, 2839400, 2184000, 3200000, 2628600, 3744000},
		{310, 340, 1875400, 2839400, 2272000, 3228000, 2724600, 3873200},
		{340, 370, 1875400, 2839400, 2362000, 3318000, 2843400, 3918600},
		{370, 400, 1875400, 2839400, 2452000, 3412000, 2945600, 3975600},
		{400, 9999, 1875400, 2839400, 2874000, 3810000, 3448800, 4572000},
	}
)

// GetUtilizationFee рассчитывает утильсбор по объёму, мощности, возрасту и дате
func GetUtilizationFee(engineVolume float64, horsePower, ageYears int, date time.Time) float64 {
	var group []FeeData

	// Определяем группу по объёму двигателя
	switch {
	case engineVolume >= 1.0 && engineVolume < 2.0:
		group = fees1to2L
	case engineVolume >= 2.0 && engineVolume <= 3.0:
		group = fees2to3L
	default:
		return 0 // для простоты, вне диапазона пока не обрабатываем
	}

	// Определяем период
	beforeDec2025, _ := time.Parse("2006-01-02", "2025-12-01")
	afterJan2026, _ := time.Parse("2006-01-02", "2026-01-01")

	isOld := ageYears > 3
	var fee float64

	for _, f := range group {
		if horsePower >= f.HorseMin && horsePower < f.HorseMax {
			switch {
			case date.Before(beforeDec2025):
				if isOld {
					fee = f.FeeBeforeDec2025Old
				} else {
					fee = f.FeeBeforeDec2025Young
				}
			case date.Before(afterJan2026):
				if isOld {
					fee = f.FeeAfterDec2025Old
				} else {
					fee = f.FeeAfterDec2025Young
				}
			default:
				if isOld {
					fee = f.FeeAfterJan2026Old
				} else {
					fee = f.FeeAfterJan2026Young
				}
			}
			break
		}
	}

	return fee
}

// ParseHorsePowerFromString парсит мощность в лошадиных силах из строки
// Поддерживает форматы: "125(170Ps)", "170Ps", "170 л.с.", "170 HP"
func ParseHorsePowerFromString(powerStr string) (int, error) {
	powerStr = strings.TrimSpace(powerStr)
	if powerStr == "" {
		return 0, fmt.Errorf("пустая строка мощности")
	}

	// Ищем значение в скобках, например "125(170Ps)" -> 170
	reBrackets := regexp.MustCompile(`\((\d+)\s*[Pp][Ss]?\)`)
	matches := reBrackets.FindStringSubmatch(powerStr)
	if len(matches) >= 2 {
		hp, err := strconv.Atoi(matches[1])
		if err == nil {
			return hp, nil
		}
	}

	// Ищем значение с "Ps" или "PS" в конце
	rePs := regexp.MustCompile(`(\d+)\s*[Pp][Ss]?`)
	matches = rePs.FindStringSubmatch(powerStr)
	if len(matches) >= 2 {
		hp, err := strconv.Atoi(matches[1])
		if err == nil {
			return hp, nil
		}
	}

	// Ищем значение с "л.с." или "HP"
	reHp := regexp.MustCompile(`(\d+)\s*(?:л\.с\.|HP|hp)`)
	matches = reHp.FindStringSubmatch(powerStr)
	if len(matches) >= 2 {
		hp, err := strconv.Atoi(matches[1])
		if err == nil {
			return hp, nil
		}
	}

	// Если ничего не найдено, пытаемся извлечь первое число
	reNumber := regexp.MustCompile(`(\d+)`)
	matches = reNumber.FindStringSubmatch(powerStr)
	if len(matches) >= 2 {
		hp, err := strconv.Atoi(matches[1])
		if err == nil {
			return hp, nil
		}
	}

	return 0, fmt.Errorf("не удалось извлечь мощность из строки: %s", powerStr)
}

// ParseEngineVolumeFromString парсит объем двигателя из строки
// Поддерживает форматы: "1.8L", "1.8 л", "1800cc", "1.8"
func ParseEngineVolumeFromString(volumeStr string) (float64, error) {
	volumeStr = strings.TrimSpace(volumeStr)
	if volumeStr == "" {
		return 0, fmt.Errorf("пустая строка объема")
	}

	// Ищем число с точкой или запятой
	re := regexp.MustCompile(`(\d+[.,]?\d*)\s*(?:[Ll]|л|cc|см³|cm³)?`)
	matches := re.FindStringSubmatch(volumeStr)
	if len(matches) < 2 {
		return 0, fmt.Errorf("не удалось извлечь объем из строки: %s", volumeStr)
	}

	// Заменяем запятую на точку
	volumeStr = strings.Replace(matches[1], ",", ".", 1)
	volume, err := strconv.ParseFloat(volumeStr, 64)
	if err != nil {
		return 0, fmt.Errorf("ошибка парсинга объема: %w", err)
	}

	// Если число большое (> 100), возможно это в см³, делим на 1000
	if volume > 100 {
		volume = volume / 1000
	}

	return volume, nil
}

// CalculateUtilizationFeeAndAddToPrice рассчитывает утильсбор и добавляет его к цене в рублях
func (pc *PriceCalculator) CalculateUtilizationFeeAndAddToPrice(ctx context.Context, rubPrice float64, powerStr, engineVolumeStr string, carYear int) (float64, error) {
	if rubPrice <= 0 {
		return rubPrice, nil
	}

	// Парсим мощность
	horsePower, err := ParseHorsePowerFromString(powerStr)
	if err != nil {
		log.Printf("Не удалось распарсить мощность '%s': %v", powerStr, err)
		return rubPrice, nil // Возвращаем цену без утильсбора, если не удалось распарсить
	}

	// Парсим объем двигателя
	engineVolume, err := ParseEngineVolumeFromString(engineVolumeStr)
	if err != nil {
		log.Printf("Не удалось распарсить объем двигателя '%s': %v", engineVolumeStr, err)
		return rubPrice, nil // Возвращаем цену без утильсбора, если не удалось распарсить
	}

	// Рассчитываем возраст машины
	currentYear := time.Now().Year()
	ageYears := currentYear - carYear
	if ageYears < 0 {
		ageYears = 0
	}

	// Рассчитываем утильсбор
	utilizationFee := GetUtilizationFee(engineVolume, horsePower, ageYears, time.Now())

	// Добавляем утильсбор к цене и округляем
	totalPrice := math.Round(rubPrice + utilizationFee)

	log.Printf("Утильсбор: объем=%.2f л, мощность=%d л.с., возраст=%d лет, сбор=%.0f руб, итоговая цена=%.0f руб", 
		engineVolume, horsePower, ageYears, utilizationFee, totalPrice)

	return totalPrice, nil
}

