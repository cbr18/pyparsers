package usecase

import (
	"context"
	"datahub/internal/domain"
	"datahub/internal/repository"
)

// CarService — бизнес-логика для работы с машинами
type CarService struct {
	repo repository.CarRepository
}

func NewCarService(repo repository.CarRepository) *CarService {
	return &CarService{repo: repo}
}

func (s *CarService) GetCarByUUID(ctx context.Context, uuid string) (*domain.Car, error) {
	return s.repo.GetByUUID(ctx, uuid)
}

// GetCarByID - для обратной совместимости, вызывает GetByID в репозитории
func (s *CarService) GetCarByID(ctx context.Context, id int64) (*domain.Car, error) {
	return s.repo.GetByID(ctx, id)
}

func (s *CarService) ListCars(ctx context.Context, filter domain.CarFilter, page, limit int, sort string) ([]domain.Car, int, error) {
	return s.repo.List(ctx, filter, page, limit, sort)
}
