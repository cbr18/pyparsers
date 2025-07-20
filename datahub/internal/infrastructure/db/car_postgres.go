package db

import (
	"context"
	"database/sql"
	"datahub/internal/domain"
	"fmt"
	"strings"

	"github.com/google/uuid"
)

type CarPostgres struct {
	db *sql.DB
}

func NewCarPostgres(db *sql.DB) *CarPostgres {
	return &CarPostgres{db: db}
}

// List — получение списка машин с фильтрами, пагинацией и сортировкой
func (r *CarPostgres) List(ctx context.Context, filter domain.CarFilter, page, limit int, sort string) ([]domain.Car, int, error) {
	var cars []domain.Car
	var args []interface{}
	var where []string
	q := "SELECT uuid, source, car_id, sku_id, title, car_name, year, mileage, price, image, link, brand_name, series_name, city, shop_id, tags, is_available, sort_number, brand_id, series_id, car_source_city_name, tags_v2, description, color, transmission, fuel_type, engine_volume, body_type, drive_type, condition, created_at, updated_at FROM cars"

	paramCount := 1
	// Добавляем ограничение по году (не меньше 2017)
	where = append(where, fmt.Sprintf("year >= $%d", paramCount))
	paramCount++
	args = append(args, 2017)
	
	if filter.Source != nil {
		where = append(where, fmt.Sprintf("source = $%d", paramCount))
		paramCount++
		args = append(args, *filter.Source)
	}
	if filter.BrandName != nil {
		where = append(where, fmt.Sprintf("brand_name = $%d", paramCount))
		paramCount++
		args = append(args, *filter.BrandName)
	}
	if filter.City != nil {
		where = append(where, fmt.Sprintf("city = $%d", paramCount))
		paramCount++
		args = append(args, *filter.City)
	}
	if filter.Year != nil {
		where = append(where, fmt.Sprintf("year = $%d", paramCount))
		paramCount++
		args = append(args, *filter.Year)
	}
	if filter.IsAvailable != nil {
		where = append(where, fmt.Sprintf("is_available = $%d", paramCount))
		paramCount++
		args = append(args, *filter.IsAvailable)
	}
	if filter.Search != nil {
		search := "%" + *filter.Search + "%"
		where = append(where, fmt.Sprintf("(title ILIKE $%d OR car_name ILIKE $%d OR brand_name ILIKE $%d)",
			paramCount, paramCount+1, paramCount+2))
		paramCount += 3
		args = append(args, search, search, search)
	}
	if len(where) > 0 {
		q += " WHERE " + strings.Join(where, " AND ")
	}
	if sort == "" {
		sort = "sort_number DESC"
	}
	q += " ORDER BY " + sort
	q += fmt.Sprintf(" OFFSET $%d LIMIT $%d", paramCount, paramCount+1)
	args = append(args, (page-1)*limit, limit)

	rows, err := r.db.QueryContext(ctx, q, args...)
	if err != nil {
		return nil, 0, err
	}
	defer rows.Close()
	for rows.Next() {
		var car domain.Car
		err := rows.Scan(
			&car.UUID, &car.Source, &car.CarID, &car.SkuID, &car.Title, &car.CarName, &car.Year, &car.Mileage, &car.Price, &car.Image, &car.Link, &car.BrandName, &car.SeriesName, &car.City, &car.ShopID, &car.Tags, &car.IsAvailable, &car.SortNumber, &car.BrandID, &car.SeriesID, &car.CarSourceCityName, &car.TagsV2, &car.Description, &car.Color, &car.Transmission, &car.FuelType, &car.EngineVolume, &car.BodyType, &car.DriveType, &car.Condition, &car.CreatedAt, &car.UpdatedAt,
		)
		if err != nil {
			return nil, 0, err
		}
		cars = append(cars, car)
	}
	if err := rows.Err(); err != nil {
		return nil, 0, err
	}
	// Получаем общее количество
	countQ := "SELECT COUNT(*) FROM cars"
	if len(where) > 0 {
		countQ += " WHERE " + strings.Join(where, " AND ")
	}
	// Используем только аргументы для условий WHERE, без OFFSET и LIMIT
	var countArgs []interface{}
	if len(args) > 2 {
		countArgs = args[:len(args)-2]
	}
	countRow := r.db.QueryRowContext(ctx, countQ, countArgs...)
	var total int
	if err := countRow.Scan(&total); err != nil {
		return nil, 0, err
	}
	return cars, total, nil
}

func (r *CarPostgres) GetByUUID(ctx context.Context, uuid string) (*domain.Car, error) {
	q := "SELECT uuid, source, car_id, sku_id, title, car_name, year, mileage, price, image, link, brand_name, series_name, city, shop_id, tags, is_available, sort_number, brand_id, series_id, car_source_city_name, tags_v2, description, color, transmission, fuel_type, engine_volume, body_type, drive_type, condition, created_at, updated_at FROM cars WHERE uuid = $1"
	row := r.db.QueryRowContext(ctx, q, uuid)
	var car domain.Car
	if err := row.Scan(
		&car.UUID, &car.Source, &car.CarID, &car.SkuID, &car.Title, &car.CarName, &car.Year, &car.Mileage, &car.Price, &car.Image, &car.Link, &car.BrandName, &car.SeriesName, &car.City, &car.ShopID, &car.Tags, &car.IsAvailable, &car.SortNumber, &car.BrandID, &car.SeriesID, &car.CarSourceCityName, &car.TagsV2, &car.Description, &car.Color, &car.Transmission, &car.FuelType, &car.EngineVolume, &car.BodyType, &car.DriveType, &car.Condition, &car.CreatedAt, &car.UpdatedAt,
	); err != nil {
		return nil, err
	}
	return &car, nil
}

// GetByID - для обратной совместимости, преобразует id в uuid и вызывает GetByUUID
func (r *CarPostgres) GetByID(ctx context.Context, id int64) (*domain.Car, error) {
	// Поскольку мы больше не используем id, просто возвращаем ошибку
	return nil, fmt.Errorf("GetByID is deprecated, use GetByUUID instead")
}

func (r *CarPostgres) GetBySourceAndSort(ctx context.Context, source string, limit int) ([]domain.Car, error) {
	q := "SELECT uuid, source, car_id, sku_id, title, car_name, year, mileage, price, image, link, brand_name, series_name, city, shop_id, tags, is_available, sort_number, brand_id, series_id, car_source_city_name, tags_v2, description, color, transmission, fuel_type, engine_volume, body_type, drive_type, condition, created_at, updated_at FROM cars WHERE source = $1 ORDER BY sort_number DESC LIMIT $2"
	rows, err := r.db.QueryContext(ctx, q, source, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var cars []domain.Car
	for rows.Next() {
		var car domain.Car
		err := rows.Scan(
			&car.UUID, &car.Source, &car.CarID, &car.SkuID, &car.Title, &car.CarName, &car.Year, &car.Mileage, &car.Price, &car.Image, &car.Link, &car.BrandName, &car.SeriesName, &car.City, &car.ShopID, &car.Tags, &car.IsAvailable, &car.SortNumber, &car.BrandID, &car.SeriesID, &car.CarSourceCityName, &car.TagsV2, &car.Description, &car.Color, &car.Transmission, &car.FuelType, &car.EngineVolume, &car.BodyType, &car.DriveType, &car.Condition, &car.CreatedAt, &car.UpdatedAt,
		)
		if err != nil {
			return nil, err
		}
		cars = append(cars, car)
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}
	return cars, nil
}

func (r *CarPostgres) CreateMany(ctx context.Context, cars []domain.Car) error {
	if len(cars) == 0 {
		return nil
	}

	// Используем более простой подход с отдельными запросами для каждой машины
	// Это менее эффективно, но более надежно
	tx, err := r.db.BeginTx(ctx, nil)
	if err != nil {
		return err
	}
	defer tx.Rollback()

	stmt, err := tx.PrepareContext(ctx, `
		INSERT INTO cars (uuid, source, car_id, sku_id, title, car_name, year, mileage, price, image, link, brand_name, series_name, city, shop_id, tags, is_available, sort_number, brand_id, series_id, car_source_city_name, tags_v2, description, color, transmission, fuel_type, engine_volume, body_type, drive_type, condition, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32)
	`)
	if err != nil {
		return err
	}
	defer stmt.Close()

	for _, car := range cars {
		uuidVal := car.UUID
		if uuidVal == "" {
			uuidVal = uuid.New().String()
		}

		_, err := stmt.ExecContext(ctx,
			uuidVal, car.Source, car.CarID, car.SkuID, car.Title, car.CarName, car.Year, car.Mileage, car.Price, car.Image, car.Link, car.BrandName, car.SeriesName, car.City, car.ShopID, car.Tags, car.IsAvailable, car.SortNumber, car.BrandID, car.SeriesID, car.CarSourceCityName, car.TagsV2, car.Description, car.Color, car.Transmission, car.FuelType, car.EngineVolume, car.BodyType, car.DriveType, car.Condition, car.CreatedAt, car.UpdatedAt,
		)
		if err != nil {
			return err
		}
	}

	return tx.Commit()
}

func (r *CarPostgres) Create(ctx context.Context, car domain.Car) error {
	uuidVal := car.UUID
	if uuidVal == "" {
		uuidVal = uuid.New().String()
	}

	_, err := r.db.ExecContext(ctx, `
		INSERT INTO cars (uuid, source, car_id, sku_id, title, car_name, year, mileage, price, image, link, brand_name, series_name, city, shop_id, tags, is_available, sort_number, brand_id, series_id, car_source_city_name, tags_v2, description, color, transmission, fuel_type, engine_volume, body_type, drive_type, condition, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32)
	`, uuidVal, car.Source, car.CarID, car.SkuID, car.Title, car.CarName, car.Year, car.Mileage, car.Price, car.Image, car.Link, car.BrandName, car.SeriesName, car.City, car.ShopID, car.Tags, car.IsAvailable, car.SortNumber, car.BrandID, car.SeriesID, car.CarSourceCityName, car.TagsV2, car.Description, car.Color, car.Transmission, car.FuelType, car.EngineVolume, car.BodyType, car.DriveType, car.Condition, car.CreatedAt, car.UpdatedAt)
	
	return err
}

func (r *CarPostgres) DeleteBySource(ctx context.Context, source string) error {
	_, err := r.db.ExecContext(ctx, "DELETE FROM cars WHERE source = $1", source)
	return err
}
