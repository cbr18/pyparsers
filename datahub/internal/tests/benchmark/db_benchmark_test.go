package benchmark

import (
	"context"
	"datahub/internal/domain"
	"datahub/internal/infrastructure/database"
	"datahub/internal/infrastructure/repository"
	"fmt"
	"os"
	"runtime"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/joho/godotenv"
)

// Инициализация тестов
func init() {
	// Загружаем переменные окружения из .env файла
	if err := godotenv.Load("../../../.env"); err != nil {
		fmt.Printf("Warning: .env file not found: %v\n", err)
	}

	// Инициализируем подключение к базе данных
	dsn := os.Getenv("DATABASE_URL")
	if dsn == "" {
		dsn = "host=localhost user=postgres password=postgres dbname=datahub port=5432 sslmode=disable"
	}
	_, err := database.InitDB(dsn)
	if err != nil {
		fmt.Printf("Error initializing database: %v\n", err)
		os.Exit(1)
	}
}

// Создает тестовую машину с уникальным UUID
func createTestCar() domain.Car {
	now := time.Now()
	return domain.Car{
		UUID:              uuid.New().String(),
		Source:            "benchmark",
		CarID:             999999998,
		SkuID:             "test-sku-id",
		Title:             "Test Car",
		CarName:           "Test Car Model",
		Year:              2020,
		Mileage:           10000,
		Price:             "20.00",
		Image:             "https://example.com/image.jpg",
		Link:              "https://example.com/car/12345",
		BrandName:         "Test Brand",
		SeriesName:        "Test Series",
		City:              "Test City",
		ShopID:            "shop123",
		Tags:              `["tag1", "tag2"]`,
		IsAvailable:       true,
		SortNumber:        1,
		BrandID:           1,
		SeriesID:          2,
		CarSourceCityName: "Test City",
		TagsV2:            `["tag3", "tag4"]`,
		Description:       "Test description",
		Color:             "Red",
		Transmission:      "Automatic",
		FuelType:          "Gasoline",
		EngineVolume:      "2.0",
		BodyType:          "Sedan",
		DriveType:         "FWD",
		Condition:         "Good",
		CreatedAt:         now,
		UpdatedAt:         now,
	}
}

// Создает несколько тестовых машин с уникальными UUID
func createTestCars(count int) []domain.Car {
	cars := make([]domain.Car, count)
	for i := 0; i < count; i++ {
		cars[i] = createTestCar()
		cars[i].SortNumber = i + 1
	}
	return cars
}

// Очищает тестовые данные после тестов
func cleanupTestData() {
	repo := repository.NewCarRepository()
	ctx := context.Background()
	if err := repo.DeleteBySource(ctx, "benchmark"); err != nil {
		fmt.Printf("Warning: failed to clean up test data: %v\n", err)
	}
}

// Измеряет использование памяти
func measureMemory(t *testing.T, name string, f func()) {
	var m1, m2 runtime.MemStats
	runtime.GC()
	runtime.ReadMemStats(&m1)

	f()

	runtime.GC()
	runtime.ReadMemStats(&m2)

	t.Logf("%s: Alloc = %v KB, TotalAlloc = %v KB, Sys = %v KB",
		name,
		(m2.Alloc-m1.Alloc)/1024,
		(m2.TotalAlloc-m1.TotalAlloc)/1024,
		(m2.Sys-m1.Sys)/1024,
	)
}

// BenchmarkCreateSingleCar измеряет производительность создания одной записи Car
func BenchmarkCreateSingleCar(b *testing.B) {
	repo := repository.NewCarRepository()
	ctx := context.Background()
	defer cleanupTestData()

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		car := createTestCar()
		if err := repo.Create(ctx, &car); err != nil {
			b.Fatalf("Failed to create car: %v", err)
		}
	}
}

// BenchmarkCreateManyCars измеряет производительность создания множества записей Car
func BenchmarkCreateManyCars(b *testing.B) {
	repo := repository.NewCarRepository()
	ctx := context.Background()
	defer cleanupTestData()

	batchSizes := []int{10, 50, 100}
	for _, size := range batchSizes {
		b.Run(fmt.Sprintf("BatchSize_%d", size), func(b *testing.B) {
			b.ResetTimer()
			for i := 0; i < b.N; i++ {
				cars := createTestCars(size)
				if err := repo.CreateMany(ctx, cars); err != nil {
					b.Fatalf("Failed to create cars: %v", err)
				}
			}
		})
	}
}

// BenchmarkGetByUUID измеряет производительность получения Car по UUID
func BenchmarkGetByUUID(b *testing.B) {
	repo := repository.NewCarRepository()
	ctx := context.Background()
	defer cleanupTestData()

	// Создаем тестовую машину
	car := createTestCar()
	if err := repo.Create(ctx, &car); err != nil {
		b.Fatalf("Failed to create car: %v", err)
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := repo.GetByUUID(ctx, car.UUID)
		if err != nil {
			b.Fatalf("Failed to get car: %v", err)
		}
	}
}

// BenchmarkListWithFilters измеряет производительность получения списка Car с фильтрами
func BenchmarkListWithFilters(b *testing.B) {
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

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _, err := repo.List(ctx, filter, 1, 10)
		if err != nil {
			b.Fatalf("Failed to list cars: %v", err)
		}
	}
}

// BenchmarkListWithComplexFilters измеряет производительность получения списка Car со сложными фильтрами
func BenchmarkListWithComplexFilters(b *testing.B) {
	repo := repository.NewCarRepository()
	ctx := context.Background()
	defer cleanupTestData()

	// Создаем тестовые машины
	cars := createTestCars(100)
	if err := repo.CreateMany(ctx, cars); err != nil {
		b.Fatalf("Failed to create cars: %v", err)
	}

	source := "benchmark"
	brandName := "Test Brand"
	city := "Test City"
	isAvailable := true
	search := "Test"
	filter := &domain.CarFilter{
		Source:      &source,
		BrandName:   &brandName,
		City:        &city,
		IsAvailable: &isAvailable,
		Search:      &search,
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, _, err := repo.List(ctx, filter, 1, 10)
		if err != nil {
			b.Fatalf("Failed to list cars: %v", err)
		}
	}
}

// BenchmarkGetBySourceAndSort измеряет производительность получения Car по источнику и сортировке
func BenchmarkGetBySourceAndSort(b *testing.B) {
	repo := repository.NewCarRepository()
	ctx := context.Background()
	defer cleanupTestData()

	// Создаем тестовые машины
	cars := createTestCars(100)
	if err := repo.CreateMany(ctx, cars); err != nil {
		b.Fatalf("Failed to create cars: %v", err)
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		_, err := repo.GetBySourceAndSort(ctx, "benchmark", 10)
		if err != nil {
			b.Fatalf("Failed to get cars: %v", err)
		}
	}
}

// TestMemoryUsageCreateMany измеряет использование памяти при создании множества записей Car
func TestMemoryUsageCreateMany(t *testing.T) {
	repo := repository.NewCarRepository()
	ctx := context.Background()
	defer cleanupTestData()

	batchSizes := []int{10, 50, 100}
	for _, size := range batchSizes {
		t.Run(fmt.Sprintf("BatchSize_%d", size), func(t *testing.T) {
			measureMemory(t, fmt.Sprintf("CreateMany_%d", size), func() {
				cars := createTestCars(size)
				if err := repo.CreateMany(ctx, cars); err != nil {
					t.Fatalf("Failed to create cars: %v", err)
				}
			})
		})
	}
}

// TestMemoryUsageList измеряет использование памяти при получении списка Car
func TestMemoryUsageList(t *testing.T) {
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

	measureMemory(t, "List", func() {
		_, _, err := repo.List(ctx, filter, 1, 100)
		if err != nil {
			t.Fatalf("Failed to list cars: %v", err)
		}
	})
}

// TestCPUUsageList измеряет использование CPU при получении списка Car
func TestCPUUsageList(t *testing.T) {
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

	// Прогреваем кэш
	_, _, err := repo.List(ctx, filter, 1, 100)
	if err != nil {
		t.Fatalf("Failed to list cars: %v", err)
	}

	// Измеряем время выполнения
	start := time.Now()
	iterations := 100
	for i := 0; i < iterations; i++ {
		_, _, err := repo.List(ctx, filter, 1, 100)
		if err != nil {
			t.Fatalf("Failed to list cars: %v", err)
		}
	}
	elapsed := time.Since(start)

	t.Logf("List: %d iterations took %v (avg: %v per iteration)",
		iterations, elapsed, elapsed/time.Duration(iterations))
}
