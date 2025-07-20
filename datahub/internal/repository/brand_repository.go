package repository

import (
	"context"
	"datahub/internal/domain"
)

// BrandRepository — интерфейс для работы с брендами
type BrandRepository interface {
	GetByOrigName(ctx context.Context, origName string) (*domain.Brand, error)
	Create(ctx context.Context, brand *domain.Brand) error
}
