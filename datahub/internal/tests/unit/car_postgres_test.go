package unit

import (
	"context"
	"datahub/internal/domain"
	"datahub/internal/infrastructure/database"
	"datahub/internal/infrastructure/db"
	"testing"

	"github.com/google/uuid"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// TestCarPostgresList тестирует метод List
func TestCarPostgresList(t *testing.T) {
	// Получаем соединение с базой данных
	sqlDB, err := database.DB.DB()
	require.NoError(t, err)

	carPostgres := db.NewCarPostgres(sqlDB)
	ctx := context.Background()

	// Очищаем тестовые данные
	cleanupTestData()

	// Создаем несколько тестовых машин
	car1 := createTestCar()
	car1.SortNumber = 3
	car1.Title = "Car 1"

	car2 := createTestCar()
	car2.SortNumber = 2
	car2.Title = "Car 2"

	car3 := createTestCar()
	car3.SortNumber = 1
	car3.Title = "Car 3"

	cars := []domain.Car{car1, car2, car3}
	err = carPostgres.CreateMany(ctx, cars)
	require.NoError(t, err)

	// Тест без фильтров
	foundCars, count, err := carPostgres.List(ctx, domain.CarFilter{}, 1, 10, "sort_number DESC")
	require.NoError(t, err)
	assert.GreaterOrEqual(t, count, 3)
	assert.GreaterOrEqual(t, len(foundCars), 3)

	// Тест с фильтром по источнику
	source := "test"
	filter := domain.CarFilter{
		Source: &source,
	}
	foundCars, count, err = carPostgres.List(ctx, filter, 1, 10, "sort_number DESC")
	require.NoError(t, err)
	assert.Equal(t, 3, count)
	assert.Equal(t, 3, len(foundCars))

	// Проверяем сортировку по sort_number DESC
	assert.Equal(t, 3, foundCars[0].SortNumber)
	assert.Equal(t, 2, foundCars[1].SortNumber)
	assert.Equal(t, 1, foundCars[2].SortNumber)

	// Тест с пагинацией
	foundCars, count, err = carPostgres.List(ctx, filter, 1, 2, "sort_number DESC")
	require.NoError(t, err)
	assert.Equal(t, 3, count)
	assert.Equal(t, 2, len(foundCars))

	// Тест с фильтром по поиску
	search := "Car 1"
	filterSearch := domain.CarFilter{
		Source: &source,
		Search: &search,
	}
	foundCars, count, err = carPostgres.List(ctx, filterSearch, 1, 10, "sort_number DESC")
	require.NoError(t, err)
	assert.Equal(t, 1, count)
	assert.Equal(t, 1, len(foundCars))
	assert.Equal(t, "Car 1", foundCars[0].Title)
}

// TestCarPostgresGetByUUID тестирует метод GetByUUID
func TestCarPostgresGetByUUID(t *testing.T) {
	// Получаем соединение с базой данных
	sqlDB, err := database.DB.DB()
	require.NoError(t, err)

	carPostgres := db.NewCarPostgres(sqlDB)
	ctx := context.Background()

	// Очищаем тестовые данные
	cleanupTestData()

	// Создаем тестовую машину
	car := createTestCar()
	err = carPostgres.CreateMany(ctx, []domain.Car{car})
	require.NoError(t, err)

	// Вызываем метод GetByUUID
	foundCar, err := carPostgres.GetByUUID(ctx, car.UUID)
	require.NoError(t, err)
	require.NotNil(t, foundCar)
	assert.Equal(t, car.UUID, foundCar.UUID)
	assert.Equal(t, car.Title, foundCar.Title)
	assert.Equal(t, car.Year, foundCar.Year)

	// Проверяем, что метод возвращает ошибку для несуществующего UUID
	_, err = carPostgres.GetByUUID(ctx, uuid.New().String())
	require.Error(t, err)
}

// TestCarPostgresGetByID тестирует метод GetByID
func TestCarPostgresGetByID(t *testing.T) {
	// Получаем соединение с базой данных
	sqlDB, err := database.DB.DB()
	require.NoError(t, err)

	carPostgres := db.NewCarPostgres(sqlDB)
	ctx := context.Background()

	// Вызываем метод GetByID, который должен вернуть ошибку
	_, err = carPostgres.GetByID(ctx, 1)
	require.Error(t, err)
	assert.Contains(t, err.Error(), "deprecated")
}

// TestCarPostgresGetBySourceAndSort тестирует метод GetBySourceAndSort
func TestCarPostgresGetBySourceAndSort(t *testing.T) {
	// Получаем соединение с базой данных
	sqlDB, err := database.DB.DB()
	require.NoError(t, err)

	carPostgres := db.NewCarPostgres(sqlDB)
	ctx := context.Background()

	// Очищаем тестовые данные
	cleanupTestData()

	// Создаем несколько тестовых машин
	car1 := createTestCar()
	car1.SortNumber = 3
	car1.Title = "Car 1"

	car2 := createTestCar()
	car2.SortNumber = 2
	car2.Title = "Car 2"

	car3 := createTestCar()
	car3.SortNumber = 1
	car3.Title = "Car 3"

	cars := []domain.Car{car1, car2, car3}
	err = carPostgres.CreateMany(ctx, cars)
	require.NoError(t, err)

	// Вызываем метод GetBySourceAndSort
	foundCars, err := carPostgres.GetBySourceAndSort(ctx, "test", 2)
	require.NoError(t, err)
	assert.Equal(t, 2, len(foundCars))

	// Проверяем сортировку по sort_number DESC
	assert.Equal(t, 3, foundCars[0].SortNumber)
	assert.Equal(t, 2, foundCars[1].SortNumber)
}

// TestCarPostgresCreateMany тестирует метод CreateMany
func TestCarPostgresCreateMany(t *testing.T) {
	// Получаем соединение с базой данных
	sqlDB, err := database.DB.DB()
	require.NoError(t, err)

	carPostgres := db.NewCarPostgres(sqlDB)
	ctx := context.Background()

	// Очищаем тестовые данные
	cleanupTestData()

	// Создаем несколько тестовых машин
	car1 := createTestCar()
	car1.Title = "Car 1"

	car2 := createTestCar()
	car2.Title = "Car 2"

	car3 := createTestCar()
	car3.Title = "Car 3"

	cars := []domain.Car{car1, car2, car3}

	// Вызываем метод CreateMany
	err = carPostgres.CreateMany(ctx, cars)
	require.NoError(t, err)

	// Проверяем, что все машины созданы
	source := "test"
	filter := domain.CarFilter{
		Source: &source,
	}
	foundCars, count, err := carPostgres.List(ctx, filter, 1, 10, "")
	require.NoError(t, err)
	assert.Equal(t, 3, count)
	assert.Equal(t, 3, len(foundCars))

	// Проверяем пустой слайс
	err = carPostgres.CreateMany(ctx, []domain.Car{})
	require.NoError(t, err)

	// Проверяем генерацию UUID
	car4 := createTestCar()
	car4.UUID = ""
	err = carPostgres.CreateMany(ctx, []domain.Car{car4})
	require.NoError(t, err)
}

// TestCarPostgresDeleteBySource тестирует метод DeleteBySource
func TestCarPostgresDeleteBySource(t *testing.T) {
	// Получаем соединение с базой данных
	sqlDB, err := database.DB.DB()
	require.NoError(t, err)

	carPostgres := db.NewCarPostgres(sqlDB)
	ctx := context.Background()

	// Очищаем тестовые данные
	cleanupTestData()

	// Создаем тестовую машину
	car := createTestCar()
	err = carPostgres.CreateMany(ctx, []domain.Car{car})
	require.NoError(t, err)

	// Создаем машину с другим источником
	otherCar := createTestCar()
	otherCar.Source = "other"
	err = carPostgres.CreateMany(ctx, []domain.Car{otherCar})
	require.NoError(t, err)

	// Вызываем метод DeleteBySource
	err = carPostgres.DeleteBySource(ctx, "test")
	require.NoError(t, err)

	// Проверяем, что машина с источником "test" удалена
	source := "test"
	filter := domain.CarFilter{
		Source: &source,
	}
	foundCars, count, err := carPostgres.List(ctx, filter, 1, 10, "")
	require.NoError(t, err)
	assert.Equal(t, 0, count)
	assert.Equal(t, 0, len(foundCars))

	// Проверяем, что машина с источником "other" не удалена
	otherSource := "other"
	otherFilter := domain.CarFilter{
		Source: &otherSource,
	}
	otherFoundCars, otherCount, err := carPostgres.List(ctx, otherFilter, 1, 10, "")
	require.NoError(t, err)
	assert.Equal(t, 1, otherCount)
	assert.Equal(t, 1, len(otherFoundCars))

	// Очищаем тестовые данные
	carPostgres.DeleteBySource(ctx, "other")
}
