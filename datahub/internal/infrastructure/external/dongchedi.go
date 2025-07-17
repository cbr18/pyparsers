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

type DongchediClient struct {
	BaseURL string
}

func NewDongchediClient(baseURL string) *DongchediClient {
	return &DongchediClient{BaseURL: baseURL}
}

// FetchAll — получает все машины с FastAPI (GET /cars/dongchedi/all)
func (c *DongchediClient) FetchAll(ctx context.Context) ([]domain.Car, error) {
	url := fmt.Sprintf("%s/cars/dongchedi/all", c.BaseURL)
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

// FetchIncremental — получает только новые машины (POST /cars/dongchedi/incremental)
func (c *DongchediClient) FetchIncremental(ctx context.Context, lastCars []domain.Car) ([]domain.Car, error) {
	url := fmt.Sprintf("%s/cars/dongchedi/incremental", c.BaseURL)
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

// CheckCar — проверяет машину по sku_id (GET /cars/dongchedi/car/{sku_id})
func (c *DongchediClient) CheckCar(ctx context.Context, carIDorURL string) (*domain.Car, error) {
	url := fmt.Sprintf("%s/cars/dongchedi/car/%s", c.BaseURL, carIDorURL)
	resp, err := http.Get(url)
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
