package usecase

import (
	"context"
	"datahub/internal/domain"
	"encoding/json"
	"fmt"
	"sync"
	"time"

	"github.com/google/uuid"
)

// TaskService — сервис для управления задачами обновления
type TaskService struct {
	tasks map[string]*domain.Task
	mutex sync.RWMutex
}

// NewTaskService создает новый сервис задач
func NewTaskService() *TaskService {
	return &TaskService{
		tasks: make(map[string]*domain.Task),
	}
}

// CreateTask создает новую задачу
func (s *TaskService) CreateTask(source, taskType string) (*domain.Task, error) {
	// Валидация входных параметров
	if !domain.IsValidSource(source) {
		return nil, fmt.Errorf("invalid source: %s", source)
	}
	if !domain.IsValidType(taskType) {
		return nil, fmt.Errorf("invalid task type: %s", taskType)
	}

	// Генерируем UUID для задачи
	taskID := uuid.New().String()
	
	now := time.Now()
	task := &domain.Task{
		ID:        taskID,
		Source:    source,
		Type:      taskType,
		Status:    string(domain.TaskStatusPending),
		CreatedAt: now,
		UpdatedAt: now,
	}

	s.mutex.Lock()
	defer s.mutex.Unlock()
	
	s.tasks[taskID] = task
	return task, nil
}

// GetTask получает задачу по ID
func (s *TaskService) GetTask(taskID string) (*domain.Task, bool) {
	s.mutex.RLock()
	defer s.mutex.RUnlock()
	
	task, exists := s.tasks[taskID]
	return task, exists
}

// GetAllTasks возвращает все задачи
func (s *TaskService) GetAllTasks() []*domain.Task {
	s.mutex.RLock()
	defer s.mutex.RUnlock()
	
	tasks := make([]*domain.Task, 0, len(s.tasks))
	for _, task := range s.tasks {
		tasks = append(tasks, task)
	}
	return tasks
}

// UpdateTaskStatus обновляет статус задачи
func (s *TaskService) UpdateTaskStatus(taskID string, status string, result *domain.TaskResult, err error) error {
	if !domain.IsValidStatus(status) {
		return fmt.Errorf("invalid status: %s", status)
	}

	s.mutex.Lock()
	defer s.mutex.Unlock()
	
	task, exists := s.tasks[taskID]
	if !exists {
		return fmt.Errorf("task not found: %s", taskID)
	}

	task.Status = status
	task.UpdatedAt = time.Now()

	if err != nil {
		task.Error = err.Error()
		task.Result = nil
	} else if result != nil {
		resultJSON, jsonErr := json.Marshal(result)
		if jsonErr != nil {
			task.Error = fmt.Sprintf("failed to marshal result: %v", jsonErr)
		} else {
			task.Result = resultJSON
		}
	}

	return nil
}

// ExecuteTask выполняет задачу в фоне
func (s *TaskService) ExecuteTask(ctx context.Context, taskID string, updateService *UpdateService) {
	// Обновляем статус на "in_progress"
	s.UpdateTaskStatus(taskID, string(domain.TaskStatusInProgress), nil, nil)

	var result *domain.TaskResult
	var err error

	// Выполняем задачу в зависимости от типа
	task, exists := s.GetTask(taskID)
	if !exists {
		s.UpdateTaskStatus(taskID, string(domain.TaskStatusFailed), nil, fmt.Errorf("task not found"))
		return
	}

	switch task.Type {
	case string(domain.TaskTypeFull):
		count, updateErr := updateService.FullUpdate(ctx)
		if updateErr != nil {
			err = updateErr
		} else {
			result = &domain.TaskResult{
				Count:   count,
				Message: fmt.Sprintf("Successfully updated %d cars", count),
			}
		}

	case string(domain.TaskTypeIncremental):
		// Для инкрементального обновления используем значение по умолчанию
		updateErr := updateService.IncrementalUpdate(ctx, 5)
		if updateErr != nil {
			err = updateErr
		} else {
			result = &domain.TaskResult{
				Message: "Incremental update completed successfully",
			}
		}

	default:
		err = fmt.Errorf("unknown task type: %s", task.Type)
	}

	// Обновляем финальный статус задачи
	if err != nil {
		s.UpdateTaskStatus(taskID, string(domain.TaskStatusFailed), nil, err)
	} else {
		s.UpdateTaskStatus(taskID, string(domain.TaskStatusDone), result, nil)
	}
}
