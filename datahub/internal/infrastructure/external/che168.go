package external

import (
	"bytes"
	"context"
	"datahub/internal/domain"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
)

type Che168Client struct {
	BaseURL string
}

func NewChe168Client(baseURL string) *Che168Client {
	return &Che168Client{BaseURL: baseURL}
}

// FetchAll — получает все машины с FastAPI (GET /cars/che168/all)
func (c *Che168Client) FetchAll(ctx context.Context) ([]domain.Car, error) {
	url := fmt.Sprintf("%s/cars/che168/all", c.BaseURL)
	resp, err := http.Get(url)
	if err != nil {
		return nil, err
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

// FetchIncremental — получает только новые машины (POST /cars/che168/incremental)
func (c *Che168Client) FetchIncremental(ctx context.Context, lastCars []domain.Car) ([]domain.Car, error) {
	url := fmt.Sprintf("%s/cars/che168/incremental", c.BaseURL)
	body, err := json.Marshal(lastCars)
	if err != nil {
		return nil, err
	}
	resp, err := http.Post(url, "application/json", bytes.NewReader(body))
	if err != nil {
		return nil, err
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
