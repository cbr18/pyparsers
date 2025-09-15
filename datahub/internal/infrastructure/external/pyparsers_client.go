package external

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

type PyparsersClient struct {
	baseURL    string
	httpClient *http.Client
}

type CreateTaskRequest struct {
	Source string `json:"source"`
}

type CreateTaskResponse struct {
	TaskID string `json:"task_id"`
	Error  string `json:"error,omitempty"`
}

func NewPyparsersClient(baseURL string) *PyparsersClient {
	return &PyparsersClient{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: 10 * time.Second, // Короткий таймаут для создания задачи
		},
	}
}

func (c *PyparsersClient) CreateTask(ctx context.Context, source string) (*CreateTaskResponse, error) {
	reqBody := CreateTaskRequest{
		Source: source,
	}
	
	jsonData, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %w", err)
	}
	
	url := fmt.Sprintf("%s/tasks", c.baseURL)
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
	
	var response CreateTaskResponse
	if err := json.NewDecoder(resp.Body).Decode(&response); err != nil {
		return nil, fmt.Errorf("failed to decode response: %w", err)
	}
	
	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("pyparsers returned error: %s", response.Error)
	}
	
	return &response, nil
}

