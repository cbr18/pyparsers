package unit

import (
	"context"
	"datahub/internal/domain"
	"datahub/internal/infrastructure/database"
	"datahub/internal/infrastructure/repository"
	"os"
	"testing"
	"time"

	"github.com/google/uuid"
	"github.com/joho/godotenv"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// Инициализация тестов
func init() {
	// Загружаем переменные окружения из .env файла
	if err := godotenv.Load("../../../.env"); err != nil {
		// Игнорируем ошибку, если файл не найден
	}

	// Инициализируем подключение к базе данных
	if _, err := database.InitDB(os.Getenv("DATABASE_URL")); err != nil {
		panic(err)
	}
}

// Создает тестовую машину с уникальным UUID
func createTestCar() domain.Car {
	now := time.Now()
	return domain.Car{
		UUID:              uuid.New().String(),
		Source:            "test",
		CarID:             99999999,
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

// Очищает тестовые данные после тестов
func cleanupTestData() {
	repo := repository.NewCarRepository()
	ctx := context.Background()
	repo.DeleteBySource(ctx, "test")
}

// TestMain выполняется перед всеми тестами
func TestMain(m *testing.M) {
	// Запускаем тесты
	code := m.Run()

	// Очищаем тестовые данные
	cleanupTestData()

	// Завершаем программу с кодом выполнения тестов
	os.Exit(code)
}

// TestCarRepositoryCreate тестирует метод Create
func TestCarRepositoryCreate(t *testing.T) {
	repo := repository.NewCarRepository()
	ctx := context.Background()

	// Создаем тестовую машину
	car := createTestCar()

	// Вызываем метод Create
	err := repo.Create(ctx, &car)
	require.NoError(t, err)

	// Проверяем, что машина создана
	createdCar, err := repo.GetByUUID(ctx, car.UUID)
	require.NoError(t, err)
	require.NotNil(t, createdCar)
	assert.Equal(t, car.UUID, createdCar.UUID)
	assert.Equal(t, car.Title, createdCar.Title)
	assert.Equal(t, car.Year, createdCar.Year)
}

// TestCarRepositoryGetByUUID тестирует метод GetByUUID
func TestCarRepositoryGetByUUID(t *testing.T) {
	repo := repository.NewCarRepository()
	ctx := context.Background()

	// Создаем тестовую машину
	car := createTestCar()
	err := repo.Create(ctx, &car)
	require.NoError(t, err)

	// Вызываем метод GetByUUID
	foundCar, err := repo.GetByUUID(ctx, car.UUID)
	require.NoError(t, err)
	require.NotNil(t, foundCar)
	assert.Equal(t, car.UUID, foundCar.UUID)
	assert.Equal(t, car.Title, foundCar.Title)
	assert.Equal(t, car.Year, foundCar.Year)

	// Проверяем, что метод возвращает nil для несуществующего UUID
	notFoundCar, err := repo.GetByUUID(ctx, uuid.New().String())
	require.NoError(t, err)
	assert.Nil(t, notFoundCar)
}

// TestCarRepositoryUpdate тестирует метод Update
func TestCarRepositoryUpdate(t *testing.T) {
	repo := repository.NewCarRepository()
	ctx := context.Background()

	// Создаем тестовую машину
	car := createTestCar()
	err := repo.Create(ctx, &car)
	require.NoError(t, err)

	// Изменяем данные
	car.Title = "Updated Title"
	car.Year = 2021
	car.IsAvailable = false

	// Вызываем метод Update
	err = repo.Update(ctx, &car)
	require.NoError(t, err)

	// Проверяем, что данные обновлены
	updatedCar, err := repo.GetByUUID(ctx, car.UUID)
	require.NoError(t, err)
	require.NotNil(t, updatedCar)
	assert.Equal(t, "Updated Title", updatedCar.Title)
	assert.Equal(t, 2021, updatedCar.Year)
	assert.False(t, updatedCar.IsAvailable)
}

// TestCarRepositoryDelete тестирует метод Delete
func TestCarRepositoryDelete(t *testing.T) {
	repo := repository.NewCarRepository()
	ctx := context.Background()

	// Создаем тестовую машину
	car := createTestCar()
	err := repo.Create(ctx, &car)
	require.NoError(t, err)

	// Вызываем метод Delete
	err = repo.Delete(ctx, car.UUID)
	require.NoError(t, err)

	// Проверяем, что машина удалена
	deletedCar, err := repo.GetByUUID(ctx, car.UUID)
	require.NoError(t, err)
	assert.Nil(t, deletedCar)
}

// TestCarRepositoryList тестирует метод List
func TestCarRepositoryList(t *testing.T) {
	repo := repository.NewCarRepository()
	ctx := context.Background()

	// Создаем несколько тестовых машин
	car1 := createTestCar()
	car1.SortNumber = 3
	car1.Title = "Car 1"
	err := repo.Create(ctx, &car1)
	require.NoError(t, err)

	car2 := createTestCar()
	car2.SortNumber = 2
	car2.Title = "Car 2"
	err = repo.Create(ctx, &car2)
	require.NoError(t, err)

	car3 := createTestCar()
	car3.SortNumber = 1
	car3.Title = "Car 3"
	err = repo.Create(ctx, &car3)
	require.NoError(t, err)

	// Тест без фильтров
	cars, count, err := repo.List(ctx, nil, 0, 10)
	require.NoError(t, err)
	assert.GreaterOrEqual(t, count, int64(3))
	assert.GreaterOrEqual(t, len(cars), 3)

	// Тест с фильтром по источнику
	source := "test"
	filter := &domain.CarFilter{
		Source: &source,
	}
	cars, count, err = repo.List(ctx, filter, 0, 10)
	require.NoError(t, err)
	assert.Equal(t, int64(3), count)
	assert.Equal(t, 3, len(cars))

	// Проверяем сортировку по sort_number DESC
	assert.Equal(t, 3, cars[0].SortNumber)
	assert.Equal(t, 2, cars[1].SortNumber)
	assert.Equal(t, 1, cars[2].SortNumber)

	// Тест с пагинацией
	cars, count, err = repo.List(ctx, filter, 1, 2)
	require.NoError(t, err)
	assert.Equal(t, int64(3), count)
	assert.Equal(t, 2, len(cars))

	// Тест с фильтром по поиску
	search := "Car 1"
	filterSearch := &domain.CarFilter{
		Source: &source,
		Search: &search,
	}
	cars, count, err = repo.List(ctx, filterSearch, 0, 10)
	require.NoError(t, err)
	assert.Equal(t, int64(1), count)
	assert.Equal(t, 1, len(cars))
	assert.Equal(t, "Car 1", cars[0].Title)
}

// TestCarRepositoryDeleteBySource тестирует метод DeleteBySource
func TestCarRepositoryDeleteBySource(t *testing.T) {
	repo := repository.NewCarRepository()
	ctx := context.Background()

	// Создаем тестовую машину
	car := createTestCar()
	err := repo.Create(ctx, &car)
	require.NoError(t, err)

	// Создаем машину с другим источником
	otherCar := createTestCar()
	otherCar.Source = "other"
	err = repo.Create(ctx, &otherCar)
	require.NoError(t, err)

	// Вызываем метод DeleteBySource
	err = repo.DeleteBySource(ctx, "test")
	require.NoError(t, err)

	// Проверяем, что машина с источником "test" удалена
	deletedCar, err := repo.GetByUUID(ctx, car.UUID)
	require.NoError(t, err)
	assert.Nil(t, deletedCar)

	// Проверяем, что машина с источником "other" не удалена
	otherCarFound, err := repo.GetByUUID(ctx, otherCar.UUID)
	require.NoError(t, err)
	require.NotNil(t, otherCarFound)

	// Очищаем тестовые данные
	repo.DeleteBySource(ctx, "other")
}

// TestCarRepositoryCreateMany тестирует метод CreateMany
func TestCarRepositoryCreateMany(t *testing.T) {
	repo := repository.NewCarRepository()
	ctx := context.Background()

	// Создаем несколько тестовых машин
	car1 := createTestCar()
	car1.Title = "Car 1"

	car2 := createTestCar()
	car2.Title = "Car 2"

	car3 := createTestCar()
	car3.Title = "Car 3"

	cars := []domain.Car{car1, car2, car3}

	// Вызываем метод CreateMany
	err := repo.CreateMany(ctx, cars)
	require.NoError(t, err)

	// Проверяем, что все машины созданы
	source := "test"
	filter := &domain.CarFilter{
		Source: &source,
	}
	foundCars, count, err := repo.List(ctx, filter, 0, 10)
	require.NoError(t, err)
	assert.GreaterOrEqual(t, count, int64(3))
	assert.GreaterOrEqual(t, len(foundCars), 3)

	// Проверяем пустой слайс
	err = repo.CreateMany(ctx, []domain.Car{})
	require.NoError(t, err)
}

// TestCarRepositoryGetBySourceAndSort тестирует метод GetBySourceAndSort
func TestCarRepositoryGetBySourceAndSort(t *testing.T) {
	repo := repository.NewCarRepository()
	ctx := context.Background()

	// Создаем несколько тестовых машин
	car1 := createTestCar()
	car1.SortNumber = 3
	car1.Title = "Car 1"
	err := repo.Create(ctx, &car1)
	require.NoError(t, err)

	car2 := createTestCar()
	car2.SortNumber = 2
	car2.Title = "Car 2"
	err = repo.Create(ctx, &car2)
	require.NoError(t, err)

	car3 := createTestCar()
	car3.SortNumber = 1
	car3.Title = "Car 3"
	err = repo.Create(ctx, &car3)
	require.NoError(t, err)

	// Вызываем метод GetBySourceAndSort
	cars, err := repo.GetBySourceAndSort(ctx, "test", 2)
	require.NoError(t, err)
	assert.Equal(t, 2, len(cars))

	// Проверяем сортировку по sort_number DESC
	assert.Equal(t, 3, cars[0].SortNumber)
	assert.Equal(t, 2, cars[1].SortNumber)
}
