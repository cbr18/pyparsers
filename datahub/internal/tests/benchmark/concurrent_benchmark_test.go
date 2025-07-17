package benchmark

import (
	"context"
	"datahub/internal/domain"
	"datahub/internal/infrastructure/database"
	"datahub/internal/infrastructure/repository"
	"fmt"
	"sync"
	"testing"
	"time"
)

// BenchmarkConcurrentGetByUUID измеряет производительность конкурентного получения Car по UUID
func BenchmarkConcurrentGetByUUID(b *testing.B) {
	repo := repository.NewCarRepository()
	ctx := context.Background()
	defer cleanupTestData()

	// Создаем тестовые машины
	cars := createTestCars(100)
	if err := repo.CreateMany(ctx, cars); err != nil {
		b.Fatalf("Failed to create cars: %v", err)
	}

	// Получаем UUID всех созданных машин
	uuids := make([]string, len(cars))
	for i, car := range cars {
		uuids[i] = car.UUID
	}

	concurrencyLevels := []int{1, 5, 10, 20, 50}
	for _, concurrency := range concurrencyLevels {
		b.Run(fmt.Sprintf("Concurrency_%d", concurrency), func(b *testing.B) {
			b.ResetTimer()
			for i := 0; i < b.N; i++ {
				var wg sync.WaitGroup
				wg.Add(concurrency)

				for j := 0; j < concurrency; j++ {
					go func(idx int) {
						defer wg.Done()
						uuid := uuids[idx%len(uuids)]
						_, err := repo.GetByUUID(ctx, uuid)
						if err != nil {
							b.Errorf("Failed to get car: %v", err)
						}
					}(j)
				}

				wg.Wait()
			}
		})
	}
}

// BenchmarkConcurrentList измеряет производительность конкурентного получения списка Car
func BenchmarkConcurrentList(b *testing.B) {
	repo := repository.NewCarRepository()
	ctx := context.Background()
	defer cleanupTestData()

	// Создаем тестовые машины
	cars := createTestCars(100)
	if err := repo.CreateMany(ctx, cars); err != nil {
		b.Fatalf("Failed to create cars: %v", err)
	}

	source := "benchmark"
	filter := &domain.CarFilter{
		Source: &source,
	}

	concurrencyLevels := []int{1, 5, 10, 20, 50}
	for _, concurrency := range concurrencyLevels {
		b.Run(fmt.Sprintf("Concurrency_%d", concurrency), func(b *testing.B) {
			b.ResetTimer()
			for i := 0; i < b.N; i++ {
				var wg sync.WaitGroup
				wg.Add(concurrency)

				for j := 0; j < concurrency; j++ {
					go func() {
						defer wg.Done()
						_, _, err := repo.List(ctx, filter, 0, 10)
						if err != nil {
							b.Errorf("Failed to list cars: %v", err)
						}
					}()
				}

				wg.Wait()
			}
		})
	}
}

// BenchmarkConcurrentCreateMany измеряет производительность конкурентного создания множества записей Car
func BenchmarkConcurrentCreateMany(b *testing.B) {
	repo := repository.NewCarRepository()
	ctx := context.Background()
	defer cleanupTestData()

	concurrencyLevels := []int{1, 5, 10}
	for _, concurrency := range concurrencyLevels {
		b.Run(fmt.Sprintf("Concurrency_%d", concurrency), func(b *testing.B) {
			b.ResetTimer()
			for i := 0; i < b.N; i++ {
				var wg sync.WaitGroup
				wg.Add(concurrency)

				for j := 0; j < concurrency; j++ {
					go func(idx int) {
						defer wg.Done()
						// Создаем уникальные машины для каждой горутины
						cars := createTestCars(10)
						for k := range cars {
							cars[k].Source = fmt.Sprintf("benchmark_%d", idx)
						}
						err := repo.CreateMany(ctx, cars)
						if err != nil {
							b.Errorf("Failed to create cars: %v", err)
						}
					}(j)
				}

				wg.Wait()
			}
		})
	}
}

// TestConnectionPooling измеряет влияние размера пула соединений на производительность
func TestConnectionPooling(t *testing.T) {
	repo := repository.NewCarRepository()
	ctx := context.Background()
	defer cleanupTestData()

	// Создаем тестовые машины
	cars := createTestCars(100)
	if err := repo.CreateMany(ctx, cars); err != nil {
		t.Fatalf("Failed to create cars: %v", err)
	}

	source := "benchmark"
	filter := &domain.CarFilter{
		Source: &source,
	}

	// Получаем соединение с базой данных для настройки пула
	sqlDB, err := database.DB.DB()
	if err != nil {
		t.Fatalf("Failed to get SQL DB: %v", err)
	}

	// Тестируем разные размеры пула соединений
	poolSizes := []int{5, 10, 20, 50}
	concurrency := 20
	iterations := 50

	for _, poolSize := range poolSizes {
		// Настраиваем размер пула
		sqlDB.SetMaxOpenConns(poolSize)
		sqlDB.SetMaxIdleConns(poolSize)
		sqlDB.SetConnMaxLifetime(time.Minute)

		t.Logf("Testing with pool size: %d", poolSize)

		start := time.Now()
		var wg sync.WaitGroup
		wg.Add(concurrency)

		for j := 0; j < concurrency; j++ {
			go func() {
				defer wg.Done()
				for k := 0; k < iterations; k++ {
					_, _, err := repo.List(ctx, filter, 0, 10)
					if err != nil {
						t.Errorf("Failed to list cars: %v", err)
					}
				}
			}()
		}

		wg.Wait()
		elapsed := time.Since(start)

		t.Logf("Pool size %d: %d concurrent clients, %d iterations each, took %v (avg: %v per request)",
			poolSize, concurrency, iterations, elapsed, elapsed/time.Duration(concurrency*iterations))
	}
}
