package benchmark

import (
	"context"
	"datahub/internal/domain"
	"datahub/internal/infrastructure/database"
	"datahub/internal/infrastructure/db"
	"datahub/internal/infrastructure/repository"
	"fmt"
	"testing"
	"time"

	"github.com/google/uuid"
)

// BenchmarkSQLList измеряет производительность получения списка Car с использованием прямых SQL-запросов
func BenchmarkSQLList(b *testing.B) {
	// Получаем соединение с базой данных
	sqlDB, err := database.DB.DB()
	if err != nil {
		b.Fatalf("Failed to get SQL DB: %v", err)
	}

	carPostgres := db.NewCarPostgres(sqlDB)
	ctx := context.Background()
	defer cleanupTestData()

	// Создаем тестовые машины
	cars := createTestCars(100)
	repo := repository.NewCarRepository()
	if err := repo.CreateMany(ctx, cars); err != nil {
		b.Fatalf("Failed to create cars: %v", err)
	}

	source := "benchmark"
	filter := domain.CarFilter{
		Source: &source,
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _, err := carPostgres.List(ctx, filter, 1, 10, "sort_number DESC")
		if err != nil {
			b.Fatalf("Failed to list cars: %v", err)
		}
	}
}

// BenchmarkSQLGetByUUID измеряет производительность получения Car по UUID с использованием прямых SQL-запросов
func BenchmarkSQLGetByUUID(b *testing.B) {
	// Получаем соединение с базой данных
	sqlDB, err := database.DB.DB()
	if err != nil {
		b.Fatalf("Failed to get SQL DB: %v", err)
	}

	carPostgres := db.NewCarPostgres(sqlDB)
	ctx := context.Background()
	defer cleanupTestData()

	// Создаем тестовую машину
	car := createTestCar()
	repo := repository.NewCarRepository()
	if err := repo.Create(ctx, &car); err != nil {
		b.Fatalf("Failed to create car: %v", err)
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := carPostgres.GetByUUID(ctx, car.UUID)
		if err != nil {
			b.Fatalf("Failed to get car: %v", err)
		}
	}
}

// BenchmarkSQLCreateMany измеряет производительность создания множества записей Car с использованием прямых SQL-запросов
func BenchmarkSQLCreateMany(b *testing.B) {
	// Получаем соединение с базой данных
	sqlDB, err := database.DB.DB()
	if err != nil {
		b.Fatalf("Failed to get SQL DB: %v", err)
	}

	carPostgres := db.NewCarPostgres(sqlDB)
	ctx := context.Background()
	defer cleanupTestData()

	batchSizes := []int{10, 50, 100}
	for _, size := range batchSizes {
		b.Run(fmt.Sprintf("BatchSize_%d", size), func(b *testing.B) {
			b.ResetTimer()
			for i := 0; i < b.N; i++ {
				// Для каждой итерации создаем новые машины с уникальными UUID
				cars := make([]domain.Car, size)
				for j := 0; j < size; j++ {
					cars[j] = createTestCar()
					cars[j].UUID = uuid.New().String() // Гарантируем уникальность UUID
				}

				if err := carPostgres.CreateMany(ctx, cars); err != nil {
					b.Fatalf("Failed to create cars: %v", err)
				}
			}
		})
	}
}

// BenchmarkSQLGetBySourceAndSort измеряет производительность получения Car по источнику и сортировке с использованием прямых SQL-запросов
func BenchmarkSQLGetBySourceAndSort(b *testing.B) {
	// Получаем соединение с базой данных
	sqlDB, err := database.DB.DB()
	if err != nil {
		b.Fatalf("Failed to get SQL DB: %v", err)
	}

	carPostgres := db.NewCarPostgres(sqlDB)
	ctx := context.Background()
	defer cleanupTestData()

	// Создаем тестовые машины
	cars := createTestCars(100)
	repo := repository.NewCarRepository()
	if err := repo.CreateMany(ctx, cars); err != nil {
		b.Fatalf("Failed to create cars: %v", err)
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := carPostgres.GetBySourceAndSort(ctx, "benchmark", 10)
		if err != nil {
			b.Fatalf("Failed to get cars: %v", err)
		}
	}
}

// TestSQLvsGORMPerformance сравнивает производительность SQL и GORM
func TestSQLvsGORMPerformance(t *testing.T) {
	// Получаем соединение с базой данных
	sqlDB, err := database.DB.DB()
	if err != nil {
		t.Fatalf("Failed to get SQL DB: %v", err)
	}

	carPostgres := db.NewCarPostgres(sqlDB)
	repo := repository.NewCarRepository()
	ctx := context.Background()
	defer cleanupTestData()

	// Создаем тестовые машины
	cars := createTestCars(100)
	if err := repo.CreateMany(ctx, cars); err != nil {
		t.Fatalf("Failed to create cars: %v", err)
	}

	source := "benchmark"
	filter := domain.CarFilter{
		Source: &source,
	}
	gormFilter := &domain.CarFilter{
		Source: &source,
	}

	// Тестируем SQL
	sqlStart := time.Now()
	iterations := 100
	for i := 0; i < iterations; i++ {
		_, _, err := carPostgres.List(ctx, filter, 1, 10, "sort_number DESC")
		if err != nil {
			t.Fatalf("Failed to list cars with SQL: %v", err)
		}
	}
	sqlElapsed := time.Since(sqlStart)

	// Тестируем GORM
	gormStart := time.Now()
	for i := 0; i < iterations; i++ {
		_, _, err := repo.List(ctx, gormFilter, 0, 10)
		if err != nil {
			t.Fatalf("Failed to list cars with GORM: %v", err)
		}
	}
	gormElapsed := time.Since(gormStart)

	t.Logf("SQL: %d iterations took %v (avg: %v per iteration)",
		iterations, sqlElapsed, sqlElapsed/time.Duration(iterations))
	t.Logf("GORM: %d iterations took %v (avg: %v per iteration)",
		iterations, gormElapsed, gormElapsed/time.Duration(iterations))
	t.Logf("Difference: GORM is %.2f times slower than SQL",
		float64(gormElapsed)/float64(sqlElapsed))
}
