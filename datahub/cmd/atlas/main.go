package main

import (
	"encoding/json"
	"fmt"
	"os"

	"datahub/internal/domain"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/schema"
)

// Функция для генерации схемы из моделей GORM для Atlas
func main() {
	// Создаем конфигурацию GORM
	config := &gorm.Config{
		NamingStrategy: schema.NamingStrategy{
			TablePrefix:   "",
			SingularTable: false,
		},
	}

	// Создаем подключение к базе данных (не используется, нужно только для инициализации)
	db, err := gorm.Open(postgres.New(postgres.Config{
		DSN: "postgres://postgres:3iop4r459u8988@localhost:5432/carsdb?sslmode=disable",
	}), config)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to open gorm connection: %v\n", err)
		os.Exit(1)
	}

	// Регистрируем модели
	models := []interface{}{
		&domain.Car{},
		// Добавьте здесь другие модели по мере необходимости
	}

	// Получаем схему для каждой модели
	schemas := make(map[string]map[string]interface{})
	for _, model := range models {
		stmt := &gorm.Statement{DB: db}
		if err := stmt.Parse(model); err != nil {
			fmt.Fprintf(os.Stderr, "failed to parse model: %v\n", err)
			os.Exit(1)
		}

		// Получаем информацию о таблице
		tableName := stmt.Schema.Table
		fields := make(map[string]interface{})
		for _, field := range stmt.Schema.Fields {
			if !field.IgnoreMigration {
				fields[field.DBName] = map[string]interface{}{
					"type":     field.DataType,
					"nullable": field.NotNull,
				}
			}
		}
		schemas[tableName] = fields
	}

	// Выводим схему в формате JSON
	if err := json.NewEncoder(os.Stdout).Encode(schemas); err != nil {
		fmt.Fprintf(os.Stderr, "failed to encode schema: %v\n", err)
		os.Exit(1)
	}
}
