package usecase

import (
	"context"
	"datahub/internal/domain"
	"datahub/internal/repository"
)

type BrandService struct {
	repo repository.BrandRepository
}

func NewBrandService(repo repository.BrandRepository) *BrandService {
	return &BrandService{repo: repo}
}

func (s *BrandService) ListAllBrands(ctx context.Context) ([]domain.Brand, error) {
	return s.repo.ListAll(ctx)
} 