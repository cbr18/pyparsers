package external

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

// TranslatorClient — клиент для сервиса перевода
type TranslatorClient struct {
	baseURL    string
	httpClient *http.Client
}

// TextTranslateRequest — запрос на перевод текста
type TextTranslateRequest struct {
	Text        string `json:"text"`
	SourceLang  string `json:"source_lang"`
	TargetLang  string `json:"target_lang"`
}

// TextTranslateResponse — ответ с переводом текста
type TextTranslateResponse struct {
	OriginalText    string `json:"original_text"`
	TranslatedText  string `json:"translated_text"`
	SourceLang      string `json:"source_lang"`
	TargetLang      string `json:"target_lang"`
}

// JsonTranslateRequest — запрос на перевод JSON
type JsonTranslateRequest struct {
	Data       map[string]interface{} `json:"data"`
	SourceLang string                 `json:"source_lang"`
	TargetLang string                 `json:"target_lang"`
}

// JsonTranslateResponse — ответ с переводом JSON
type JsonTranslateResponse struct {
	OriginalData    map[string]interface{} `json:"original_data"`
	TranslatedData  map[string]interface{} `json:"translated_data"`
	SourceLang      string                 `json:"source_lang"`
	TargetLang      string                 `json:"target_lang"`
}

// DatabaseTranslateRequest — запрос на перевод базы данных
type DatabaseTranslateRequest struct {
	Records    []map[string]interface{} `json:"records"`
	SourceLang string                   `json:"source_lang"`
	TargetLang string                   `json:"target_lang"`
}

// DatabaseTranslateResponse — ответ с переводом базы данных
type DatabaseTranslateResponse struct {
	TotalRecords      int                      `json:"total_records"`
	TranslatedRecords []map[string]interface{} `json:"translated_records"`
	SourceLang        string                   `json:"source_lang"`
	TargetLang        string                   `json:"target_lang"`
}

// NewTranslatorClient создает новый клиент для сервиса перевода
func NewTranslatorClient(baseURL string) *TranslatorClient {
	return &TranslatorClient{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// TranslateText переводит одиночный текст
func (c *TranslatorClient) TranslateText(ctx context.Context, text, sourceLang, targetLang string) (string, error) {
	reqBody := TextTranslateRequest{
		Text:       text,
		SourceLang: sourceLang,
		TargetLang: targetLang,
	}

	jsonData, err := json.Marshal(reqBody)
	if err != nil {
		return "", fmt.Errorf("failed to marshal request: %w", err)
	}

	url := fmt.Sprintf("%s/translate/text", c.baseURL)
	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return "", fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("translator service returned error: %d", resp.StatusCode)
	}

	var response TextTranslateResponse
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return "", fmt.Errorf("failed to decode response: %w", err)
	}

	return response.TranslatedText, nil
}

// TranslateJson переводит JSON объект
func (c *TranslatorClient) TranslateJson(ctx context.Context, data map[string]interface{}, sourceLang, targetLang string) (map[string]interface{}, error) {
	reqBody := JsonTranslateRequest{
		Data:       data,
		SourceLang: sourceLang,
		TargetLang: targetLang,
	}

	jsonData, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	url := fmt.Sprintf("%s/translate/json", c.baseURL)
	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("translator service returned error: %d", resp.StatusCode)
	}

	var response JsonTranslateResponse
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return response.TranslatedData, nil
}

// TranslateDatabase переводит батч записей из базы данных
func (c *TranslatorClient) TranslateDatabase(ctx context.Context, records []map[string]interface{}, sourceLang, targetLang string) ([]map[string]interface{}, error) {
	reqBody := DatabaseTranslateRequest{
		Records:    records,
		SourceLang: sourceLang,
		TargetLang: targetLang,
	}

	jsonData, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}

	url := fmt.Sprintf("%s/translate/db", c.baseURL)
	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("translator service returned error: %d", resp.StatusCode)
	}

	var response DatabaseTranslateResponse
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}

	return response.TranslatedRecords, nil
}

// HealthCheck проверяет доступность сервиса перевода
func (c *TranslatorClient) HealthCheck(ctx context.Context) error {
	url := fmt.Sprintf("%s/translate/health", c.baseURL)
	req, err := http.NewRequestWithContext(ctx, "GET", url, nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("translator service is not healthy: %d", resp.StatusCode)
	}

	return nil
}
