package domain

import (
	"encoding/json"
	"time"
)

// TaskStatus представляет статус задачи
type TaskStatus string

const (
	TaskStatusPending    TaskStatus = "pending"
	TaskStatusInProgress TaskStatus = "in_progress"
	TaskStatusDone       TaskStatus = "done"
	TaskStatusFailed     TaskStatus = "failed"
)

// TaskType представляет тип задачи
type TaskType string

const (
	TaskTypeFull        TaskType = "full"
	TaskTypeIncremental TaskType = "incremental"
)

// TaskSource представляет источник задачи
type TaskSource string

const (
	TaskSourceDongchedi TaskSource = "dongchedi"
	TaskSourceChe168    TaskSource = "che168"
)

// Task — доменная модель задачи обновления
type Task struct {
	ID        string          `json:"id"`
	Source    string          `json:"source"`
	Type      string          `json:"type"`
	Status    string          `json:"status"`
	Result    json.RawMessage `json:"result,omitempty"`
	Error     string          `json:"error,omitempty"`
	CreatedAt time.Time       `json:"created_at"`
	UpdatedAt time.Time       `json:"updated_at"`
}

// TaskResult представляет результат выполнения задачи
type TaskResult struct {
	Count     int    `json:"count,omitempty"`
	Message   string `json:"message,omitempty"`
	Details   string `json:"details,omitempty"`
}

// IsValidSource проверяет, является ли источник валидным
func IsValidSource(source string) bool {
	return source == string(TaskSourceDongchedi) || source == string(TaskSourceChe168)
}

// IsValidType проверяет, является ли тип задачи валидным
func IsValidType(taskType string) bool {
	return taskType == string(TaskTypeFull) || taskType == string(TaskTypeIncremental)
}

// IsValidStatus проверяет, является ли статус валидным
func IsValidStatus(status string) bool {
	switch status {
	case string(TaskStatusPending), string(TaskStatusInProgress), 
		 string(TaskStatusDone), string(TaskStatusFailed):
		return true
	default:
		return false
	}
}
