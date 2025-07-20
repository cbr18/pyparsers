package external

import (
	"bytes"
	"context"
	"datahub/internal/domain"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
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

// ToCar преобразует Che168Car в domain.Car
func (c *Che168Car) ToCar() domain.Car {
	var tagsV2Str string
	if c.TagsV2 != nil {
		if tagsStr, ok := c.TagsV2.(string); ok {
			tagsV2Str = tagsStr
		}
	}

	return domain.Car{
		Source:            "che168",
		CarID:             c.CarID,
		Title:             c.Title,
		CarName:           c.CarName,
		Year:              c.CarYear,
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
		Timeout: time.Hour, // Увеличиваем таймаут до 25 минут
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
