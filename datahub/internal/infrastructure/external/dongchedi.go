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

type DongchediClient struct {
	BaseURL string
}

func NewDongchediClient(baseURL string) *DongchediClient {
	return &DongchediClient{BaseURL: baseURL}
}

// FetchAll — получает все машины с FastAPI (GET /cars/dongchedi/all)
func (c *DongchediClient) FetchAll(ctx context.Context) ([]domain.Car, error) {
	url := fmt.Sprintf("%s/cars/dongchedi/all", c.BaseURL)
	
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
	var result struct {
		Data struct {
			SearchShSkuInfoList []domain.Car `json:"search_sh_sku_info_list"`
		} `json:"data"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	return result.Data.SearchShSkuInfoList, nil
}

// FetchIncremental — получает только новые машины (POST /cars/dongchedi/incremental)
func (c *DongchediClient) FetchIncremental(ctx context.Context, lastCars []domain.Car) ([]domain.Car, error) {
	url := fmt.Sprintf("%s/cars/dongchedi/incremental", c.BaseURL)
	
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
	var result struct {
		Data struct {
			SearchShSkuInfoList []domain.Car `json:"search_sh_sku_info_list"`
		} `json:"data"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	return result.Data.SearchShSkuInfoList, nil
}

// CheckCar — проверяет машину по sku_id (GET /cars/dongchedi/car/{sku_id})
func (c *DongchediClient) CheckCar(ctx context.Context, carIDorURL string) (*domain.Car, error) {
	url := fmt.Sprintf("%s/cars/dongchedi/car/%s", c.BaseURL, carIDorURL)
	
	// Создаем HTTP запрос с контекстом
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return nil, fmt.Errorf("ошибка создания запроса: %w", err)
	}

	// Устанавливаем таймаут для клиента
	client := &http.Client{
		Timeout: 30 * time.Second, // Таймаут для проверки одной машины
	}

	// Выполняем запрос
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("ошибка выполнения запроса: %w", err)
	}
	defer resp.Body.Close()
	var car domain.Car
	b, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if err := json.Unmarshal(b, &car); err != nil {
		return nil, err
	}
	return &car, nil
}
