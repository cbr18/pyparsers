package repository

import (
	"context"
	"datahub/internal/domain"
)

// CarRepository — интерфейс для работы с БД
// Реализация будет в infrastructure/db

type CarRepository interface {
	List(ctx context.Context, filter domain.CarFilter, page, limit int, sort string) ([]domain.Car, int, error)
	GetByUUID(ctx context.Context, uuid string) (*domain.Car, error)
	GetByID(ctx context.Context, id int64) (*domain.Car, error)
	GetBySourceAndSort(ctx context.Context, source string, limit int) ([]domain.Car, error)
	Create(ctx context.Context, car domain.Car) error
	CreateMany(ctx context.Context, cars []domain.Car) error
	DeleteBySource(ctx context.Context, source string) error
    ReplaceBySource(ctx context.Context, source string, cars []domain.Car) error
}
