package usecase

import (
	"context"
	"datahub/internal/domain"
	"datahub/internal/repository"
	"fmt"
)

// ExternalSourceClient — интерфейс для клиента внешнего источника (dongchedi, che168)
type ExternalSourceClient interface {
	FetchAll(ctx context.Context) ([]domain.Car, error)
	FetchIncremental(ctx context.Context, lastCars []domain.Car) ([]domain.Car, error)
	CheckCar(ctx context.Context, carIDorURL string) (*domain.Car, error)
}

// UpdateService — сервис для обновления данных из внешних источников
// repo — репозиторий БД, client — внешний источник
// sourceName — "dongchedi" или "che168"
type UpdateService struct {
	repo       repository.CarRepository
	client     ExternalSourceClient
	sourceName string
}

func NewUpdateService(repo repository.CarRepository, client ExternalSourceClient, sourceName string) *UpdateService {
	return &UpdateService{repo: repo, client: client, sourceName: sourceName}
}

// FullUpdate — полное обновление: очищает старые записи, сохраняет новые
// Возвращает количество обновленных машин
func (s *UpdateService) FullUpdate(ctx context.Context) (int, error) {
	cars, err := s.client.FetchAll(ctx)
	if err != nil {
		return 0, err
	}
	if err := s.repo.DeleteBySource(ctx, s.sourceName); err != nil {
		return 0, err
	}
	if err := s.repo.CreateMany(ctx, cars); err != nil {
		return 0, err
	}
	return len(cars), nil
}

// IncrementalUpdate — инкрементальное обновление: добавляет только новые
func (s *UpdateService) IncrementalUpdate(ctx context.Context, lastN int) error {
	lastCars, err := s.repo.GetBySourceAndSort(ctx, s.sourceName, lastN)
	if err != nil {
		return err
	}
	newCars, err := s.client.FetchIncremental(ctx, lastCars)
	if err != nil {
		return err
	}
	
	// Если нет новых машин, просто возвращаем nil
	if len(newCars) == 0 {
		return nil
	}
	
	// Используем CreateMany вместо Create для каждой машины отдельно
	// Это позволит создать бренды в рамках одной транзакции
	err = s.repo.CreateMany(ctx, newCars)
	if err != nil {
		// Если произошла ошибка, возвращаем ее
		return err
	}
	
	return nil
}

// PartialUpdateError - ошибка, которая содержит информацию о частичном успехе обновления
type PartialUpdateError struct {
	OriginalError error
	SuccessCount  int
	TotalCount    int
}

// Error реализует интерфейс error
func (e *PartialUpdateError) Error() string {
	return fmt.Sprintf("частично успешное обновление: добавлено %d из %d записей, ошибка: %v", 
		e.SuccessCount, e.TotalCount, e.OriginalError)
}

// CheckCar — проверка машины по ID или URL
func (s *UpdateService) CheckCar(ctx context.Context, carIDorURL string) (*domain.Car, error) {
	return s.client.CheckCar(ctx, carIDorURL)
}

// SaveCars — сохраняет машин в БД
func (s *UpdateService) SaveCars(ctx context.Context, cars []domain.Car) error {
	if len(cars) == 0 {
		return nil
	}
	
	// Устанавливаем source для всех машин
	for i := range cars {
		cars[i].Source = s.sourceName
	}
	
	return s.repo.CreateMany(ctx, cars)
}

// ClearSource — удалить все записи по источнику (для полного обновления)
func (s *UpdateService) ClearSource(ctx context.Context) error {
    return s.repo.DeleteBySource(ctx, s.sourceName)
}

// RepoGetBySourceAndSort — прокси к репозиторию для получения последних N машин по источнику
func (s *UpdateService) RepoGetBySourceAndSort(ctx context.Context, source string, limit int) ([]domain.Car, error) {
    // игнорируем входной source и используем конфигурированный для сервиса, чтобы не смешивать источники
    return s.repo.GetBySourceAndSort(ctx, s.sourceName, limit)
}

// ReplaceSource — атомарно заменяет все записи источника на новые
func (s *UpdateService) ReplaceSource(ctx context.Context, cars []domain.Car) error {
    // Нормализуем source на всякий
    for i := range cars {
        cars[i].Source = s.sourceName
    }
    return s.repo.ReplaceBySource(ctx, s.sourceName, cars)
}

// AppendIncremental — добавляет новые записи с корректным sort_number
func (s *UpdateService) AppendIncremental(ctx context.Context, cars []domain.Car) error {
    if len(cars) == 0 {
        return nil
    }
    // Получим текущий максимум sort_number по источнику
    last, err := s.repo.GetBySourceAndSort(ctx, s.sourceName, 1)
    if err != nil {
        return err
    }
    currentMax := 0
    if len(last) == 1 {
        currentMax = last[0].SortNumber
    }
    for i := range cars {
        cars[i].Source = s.sourceName
        cars[i].SortNumber = currentMax + i + 1
    }
    return s.repo.CreateMany(ctx, cars)
}
