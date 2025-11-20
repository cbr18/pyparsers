package external

import (
	"context"
	"encoding/xml"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"

	"golang.org/x/text/encoding/charmap"
	"golang.org/x/text/transform"
)

// CBRClient — клиент для получения курсов валют от Центрального Банка РФ
type CBRClient struct {
	BaseURL    string
	cnyRate    float64
	lastUpdate time.Time
	mu         sync.RWMutex
	updateInterval time.Duration
}

// ValCurs — структура для парсинга XML от ЦБ РФ
type ValCurs struct {
	XMLName xml.Name `xml:"ValCurs"`
	Date    string   `xml:"Date,attr"`
	Name    string   `xml:"name,attr"`
	Valutes []Valute `xml:"Valute"`
}

// Valute — структура валюты
type Valute struct {
	ID       string `xml:"ID,attr"`
	NumCode  string `xml:"NumCode"`
	CharCode string `xml:"CharCode"`
	Nominal  string `xml:"Nominal"`
	Name     string `xml:"Name"`
	Value    string `xml:"Value"`
	VunitRate string `xml:"VunitRate"`
}

// NewCBRClient создает новый клиент для работы с ЦБ РФ
func NewCBRClient(baseURL string) *CBRClient {
	if baseURL == "" {
		baseURL = "https://www.cbr.ru/scripts/XML_daily.asp"
	}
	return &CBRClient{
		BaseURL:        baseURL,
		updateInterval: 12 * time.Hour,
	}
}

// GetCNYRate получает курс юаня (CNY) к рублю
func (c *CBRClient) GetCNYRate(ctx context.Context) (float64, error) {
	c.mu.RLock()
	// Проверяем, нужно ли обновить курс
	if c.cnyRate > 0 && time.Since(c.lastUpdate) < c.updateInterval {
		rate := c.cnyRate
		c.mu.RUnlock()
		return rate, nil
	}
	c.mu.RUnlock()

	// Обновляем курс
	c.mu.Lock()
	defer c.mu.Unlock()

	// Двойная проверка (double-check locking)
	if c.cnyRate > 0 && time.Since(c.lastUpdate) < c.updateInterval {
		return c.cnyRate, nil
	}

	// Получаем курс от ЦБ РФ
	rate, err := c.fetchCNYRate(ctx)
	if err != nil {
		// Если ошибка, но есть старый курс - возвращаем его
		if c.cnyRate > 0 {
			return c.cnyRate, nil
		}
		return 0, err
	}

	c.cnyRate = rate
	c.lastUpdate = time.Now()
	return rate, nil
}

// fetchCNYRate получает курс юаня с сайта ЦБ РФ
func (c *CBRClient) fetchCNYRate(ctx context.Context) (float64, error) {
	req, err := http.NewRequestWithContext(ctx, "GET", c.BaseURL, nil)
	if err != nil {
		return 0, fmt.Errorf("ошибка создания запроса: %w", err)
	}

	client := &http.Client{
		Timeout: 10 * time.Second,
	}

	resp, err := client.Do(req)
	if err != nil {
		return 0, fmt.Errorf("ошибка выполнения запроса: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return 0, fmt.Errorf("неожиданный статус ответа: %d", resp.StatusCode)
	}

	// Создаем XML декодер с поддержкой windows-1251
	decoder := xml.NewDecoder(resp.Body)
	decoder.CharsetReader = func(charset string, input io.Reader) (io.Reader, error) {
		if charset == "windows-1251" {
			return transform.NewReader(input, charmap.Windows1251.NewDecoder()), nil
		}
		return input, nil
	}

	var valCurs ValCurs
	if err := decoder.Decode(&valCurs); err != nil {
		return 0, fmt.Errorf("ошибка парсинга XML: %w", err)
	}

	// Ищем юань (CNY) по CharCode
	for _, valute := range valCurs.Valutes {
		if valute.CharCode == "CNY" {
			// Заменяем запятую на точку для парсинга
			valueStr := strings.Replace(valute.Value, ",", ".", 1)
			rate, err := strconv.ParseFloat(valueStr, 64)
			if err != nil {
				return 0, fmt.Errorf("ошибка парсинга курса юаня: %w", err)
			}
			return rate, nil
		}
	}

	return 0, fmt.Errorf("курс юаня (CNY) не найден в ответе ЦБ РФ")
}

// ForceUpdate принудительно обновляет курс валют
func (c *CBRClient) ForceUpdate(ctx context.Context) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	rate, err := c.fetchCNYRate(ctx)
	if err != nil {
		return err
	}

	c.cnyRate = rate
	c.lastUpdate = time.Now()
	return nil
}

// GetLastUpdateTime возвращает время последнего обновления курса
func (c *CBRClient) GetLastUpdateTime() time.Time {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.lastUpdate
}



