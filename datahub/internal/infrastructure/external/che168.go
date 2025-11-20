package external

import (
    "bytes"
    "context"
    "datahub/internal/domain"
    "encoding/json"
    "fmt"
    "io"
    "net/http"
    "regexp"
    "strconv"
    "strings"
    "time"
)

// Che168Car представляет структуру данных автомобиля из che168
type Che168Car struct {
	Title             string      `json:"title"`
	ShPrice           string      `json:"sh_price"`
	Image             string      `json:"image"`
	Link              string      `json:"link"`
	CarName           string      `json:"car_name"`
	CarYear           int         `json:"car_year"`
	CarMileage        string      `json:"car_mileage"`
	CarSourceCityName string      `json:"car_source_city_name"`
	BrandName         string      `json:"brand_name"`
	SeriesName        string      `json:"series_name"`
	BrandID           int         `json:"brand_id"`
	SeriesID          int         `json:"series_id"`
	ShopID            string      `json:"shop_id"`
	CarID             int64       `json:"car_id"`
	TagsV2            interface{} `json:"tags_v2"`
}

// parseMileageToKm converts che168 mileage strings like "3.5万公里" or "5600公里" to kilometers
func parseMileageToKm(s string) int32 {
    s = strings.TrimSpace(s)
    if s == "" {
        return 0
    }
    numRe := regexp.MustCompile(`(?i)[0-9]+(?:\.[0-9]+)?`)
    num := numRe.FindString(s)
    if num == "" {
        return 0
    }
    // Detect "万" (ten-thousands) units
    if strings.Contains(s, "万") {
        f, err := strconv.ParseFloat(num, 64)
        if err != nil {
            return 0
        }
        // 万公里 -> multiply by 10,000 km
        km := int32(f * 10000.0)
        if km < 0 {
            return 0
        }
        return km
    }
    // Otherwise treat as kilometers
    v, err := strconv.ParseInt(num, 10, 32)
    if err != nil || v < 0 {
        return 0
    }
    return int32(v)
}

// extractYear tries to pull a reasonable year from a title when API field is 0
func extractYear(title string) int {
    title = strings.TrimSpace(title)
    if title == "" {
        return 0
    }
    // Find a 4-digit year between 1990 and 2030
    yearRe := regexp.MustCompile(`(19|20)\d{2}`)
    m := yearRe.FindString(title)
    if m == "" {
        return 0
    }
    y, err := strconv.Atoi(m)
    if err != nil {
        return 0
    }
    if y < 1990 || y > 2030 {
        return 0
    }
    return y
}

// ToCar преобразует Che168Car в domain.Car
func (c *Che168Car) ToCar() domain.Car {
	var tagsV2Str string
	if c.TagsV2 != nil {
		if tagsStr, ok := c.TagsV2.(string); ok {
			tagsV2Str = tagsStr
		}
	}

    // Normalize fields to match domain.Car used by frontend
    year := c.CarYear
    if year == 0 {
        year = extractYear(c.Title)
    }

    mileage := parseMileageToKm(c.CarMileage)

	return domain.Car{
		Source:            "che168",
		CarID:             c.CarID,
		Title:             c.Title,
		CarName:           c.CarName,
        Year:              year,
        Price:             c.ShPrice,
		Image:             c.Image,
		Link:              c.Link,
		BrandName:         c.BrandName,
		SeriesName:        c.SeriesName,
        City:              c.CarSourceCityName,
		ShopID:            c.ShopID,
		BrandID:           c.BrandID,
		SeriesID:          c.SeriesID,
		CarSourceCityName: c.CarSourceCityName,
		TagsV2:            tagsV2Str,
        Mileage:           mileage,
	}
}

type Che168Client struct {
	BaseURL string
}

func NewChe168Client(baseURL string) *Che168Client {
	return &Che168Client{BaseURL: baseURL}
}

// FetchAll — получает все машины с FastAPI (GET /cars/che168/all)
// Использует специальный эндпоинт, который парсит все страницы
func (c *Che168Client) FetchAll(ctx context.Context) ([]domain.Car, error) {
	// Используем эндпоинт /cars/che168/all, который уже реализует парсинг всех страниц
	url := fmt.Sprintf("%s/cars/che168/all", c.BaseURL)

	// Создаем HTTP запрос с контекстом
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("ошибка создания запроса: %w", err)
	}

	// Устанавливаем увеличенный таймаут для клиента, так как парсинг всех страниц может занять время
	client := &http.Client{
		Timeout: 2 * time.Hour, // Увеличиваем таймаут до 2 часов для полного парсинга
	}

	// Выполняем запрос
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("ошибка выполнения запроса: %w", err)
	}
	defer resp.Body.Close()

	// Проверяем код ответа
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("неверный код ответа: %d, тело: %s", resp.StatusCode, string(body))
	}

	// Декодируем ответ
	var result struct {
		Data struct {
			SearchShSkuInfoList []Che168Car `json:"search_sh_sku_info_list"`
			Total               int         `json:"total"`
		} `json:"data"`
		Message string `json:"message"`
		Status  int    `json:"status"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("ошибка декодирования ответа: %w", err)
	}

	// Проверяем статус ответа
	if result.Status != 200 {
		return nil, fmt.Errorf("ошибка API: %s (код: %d)", result.Message, result.Status)
	}

	// Проверяем, что получили данные
	if len(result.Data.SearchShSkuInfoList) == 0 {
		return []domain.Car{}, nil // Возвращаем пустой слайс, а не nil
	}

	// Преобразуем Che168Car в domain.Car
	cars := make([]domain.Car, len(result.Data.SearchShSkuInfoList))
	for i, car := range result.Data.SearchShSkuInfoList {
		cars[i] = car.ToCar()
	}

	return cars, nil
}

// FetchIncremental — получает только новые машины (POST /cars/che168/incremental)
func (c *Che168Client) FetchIncremental(ctx context.Context, lastCars []domain.Car) ([]domain.Car, error) {
	url := fmt.Sprintf("%s/cars/che168/incremental", c.BaseURL)

	// Сериализуем данные для запроса
	body, err := json.Marshal(lastCars)
	if err != nil {
		return nil, fmt.Errorf("ошибка сериализации данных: %w", err)
	}

	// Создаем HTTP запрос с контекстом
	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("ошибка создания запроса: %w", err)
	}

	// Устанавливаем заголовок Content-Type
	req.Header.Set("Content-Type", "application/json")

	// Устанавливаем увеличенный таймаут для клиента
	client := &http.Client{
		Timeout: 3 * time.Minute, // Увеличиваем таймаут до 3 минут
	}

	// Выполняем запрос
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("ошибка выполнения запроса: %w", err)
	}
	defer resp.Body.Close()

	// Проверяем код ответа
	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("неверный код ответа: %d, тело: %s", resp.StatusCode, string(body))
	}

	// Декодируем ответ
	var result struct {
		Data struct {
			SearchShSkuInfoList []Che168Car `json:"search_sh_sku_info_list"`
			Total               int         `json:"total"`
			PagesChecked        int         `json:"pages_checked"`
		} `json:"data"`
		Message string `json:"message"`
		Status  int    `json:"status"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, fmt.Errorf("ошибка декодирования ответа: %w", err)
	}

	// Проверяем статус ответа
	if result.Status != 200 {
		return nil, fmt.Errorf("ошибка API: %s (код: %d)", result.Message, result.Status)
	}

	// Проверяем, что получили данные
	if len(result.Data.SearchShSkuInfoList) == 0 {
		return []domain.Car{}, nil // Возвращаем пустой слайс, а не nil
	}

	// Преобразуем Che168Car в domain.Car
	cars := make([]domain.Car, len(result.Data.SearchShSkuInfoList))
	for i, car := range result.Data.SearchShSkuInfoList {
		cars[i] = car.ToCar()
	}

	return cars, nil
}

// CheckCar — проверяет машину по URL (POST /cars/che168/car)
func (c *Che168Client) CheckCar(ctx context.Context, carIDorURL string) (*domain.Car, error) {
	url := fmt.Sprintf("%s/cars/che168/car", c.BaseURL)
	body, err := json.Marshal(map[string]string{"car_url": carIDorURL})
	if err != nil {
		return nil, err
	}
	resp, err := http.Post(url, "application/json", bytes.NewReader(body))
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	b, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}

	var che168Car Che168Car
	if err := json.Unmarshal(b, &che168Car); err != nil {
		return nil, err
	}

	car := che168Car.ToCar()
	return &car, nil
}

// EnhanceCar — улучшает машину детальной информацией (POST /cars/che168/detailed/parse)
func (c *Che168Client) EnhanceCar(ctx context.Context, carID int64) (*domain.Car, error) {
	url := fmt.Sprintf("%s/che168/detailed/parse", c.BaseURL)
	
	requestBody := map[string]interface{}{
		"car_id":       carID,
		"force_update": true,
	}

	jsonData, err := json.Marshal(requestBody)
	if err != nil {
		return nil, fmt.Errorf("ошибка сериализации запроса: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("ошибка создания запроса: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")

	// Устанавливаем увеличенный таймаут для клиента (парсинг деталей может занять время)
	client := &http.Client{
		Timeout: 10 * time.Minute, // Увеличенный таймаут для парсинга деталей
	}

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("ошибка выполнения запроса: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("ошибка чтения ответа: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("ошибка API: статус %d, тело: %s", resp.StatusCode, string(body))
	}

	var response struct {
		Success bool        `json:"success"`
		CarID   int64       `json:"car_id"`
		Data    *domain.Car `json:"data"`
		Error   string      `json:"error,omitempty"`
	}

	if err := json.Unmarshal(body, &response); err != nil {
		return nil, fmt.Errorf("ошибка десериализации ответа: %w", err)
	}

	if !response.Success {
		return nil, fmt.Errorf("ошибка парсинга: %s", response.Error)
	}

	if response.Data == nil {
		return nil, fmt.Errorf("данные не получены")
	}

	// НЕ устанавливаем HasDetails здесь - это делает enhancement_worker.go
	// на основе проверки значимых полей
	
	return response.Data, nil
}

// BatchEnhanceCars — массовое улучшение машин детальной информацией
func (c *Che168Client) BatchEnhanceCars(ctx context.Context, carIDs []int64) ([]domain.Car, error) {
	url := fmt.Sprintf("%s/che168/detailed/parse-batch", c.BaseURL)
	
	requestBody := map[string]interface{}{
		"car_ids":      carIDs,
		"force_update": true,
	}

	jsonData, err := json.Marshal(requestBody)
	if err != nil {
		return nil, fmt.Errorf("ошибка сериализации запроса: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("ошибка создания запроса: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")

	// Устанавливаем увеличенный таймаут для клиента
	client := &http.Client{
		Timeout: 30 * time.Minute, // Увеличенный таймаут для массового парсинга
	}

	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("ошибка выполнения запроса: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("ошибка чтения ответа: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("ошибка API: статус %d, тело: %s", resp.StatusCode, string(body))
	}

	var response struct {
		Success    bool                      `json:"success"`
		Processed  int                       `json:"processed"`
		Successful int                       `json:"successful"`
		Failed     int                       `json:"failed"`
		Results    []struct {
			Success bool        `json:"success"`
			CarID   int64       `json:"car_id"`
			Data    *domain.Car `json:"data"`
			Error   string      `json:"error,omitempty"`
		} `json:"results"`
	}

	if err := json.Unmarshal(body, &response); err != nil {
		return nil, fmt.Errorf("ошибка десериализации ответа: %w", err)
	}

	// Извлекаем только успешно обработанные машины
	var cars []domain.Car
	for _, result := range response.Results {
		if result.Success && result.Data != nil {
			car := *result.Data
			car.HasDetails = true
			car.LastDetailUpdate = time.Now()
			cars = append(cars, car)
		}
	}

	return cars, nil
}
