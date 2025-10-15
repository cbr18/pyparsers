package database

import (
	"fmt"
	"log"
	"os"
	"time"

	"datahub/internal/domain"

	"gorm.io/driver/postgres"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

// DB - глобальный экземпляр подключения к базе данных
var DB *gorm.DB

// InitDB - инициализирует подключение к базе данных
func InitDB(dsn string) (*gorm.DB, error) {
    newLogger := logger.New(
        log.New(os.Stdout, "\r\n", log.LstdFlags),
        logger.Config{
            SlowThreshold:             time.Second,
            LogLevel:                  logger.Silent, // no SQL logs at all
            IgnoreRecordNotFoundError: true,
            Colorful:                  true,
        },
    )

	db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{
		Logger: newLogger,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to connect to database: %w", err)
	}

	// Устанавливаем соединение с базой данных
	sqlDB, err := db.DB()
	if err != nil {
		return nil, fmt.Errorf("failed to get database connection: %w", err)
	}

	// Настройка пула соединений
	sqlDB.SetMaxIdleConns(10)
	sqlDB.SetMaxOpenConns(100)
	sqlDB.SetConnMaxLifetime(time.Hour)

	// Проверка соединения
	if err := sqlDB.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	DB = db
	return db, nil
}

// AutoMigrate - автоматическая миграция схемы базы данных
// Примечание: в продакшене лучше использовать миграции через golang-migrate
func AutoMigrate() error {
	if DB == nil {
		return fmt.Errorf("database connection not initialized")
	}

	// Регистрируем модели для миграции
	return DB.AutoMigrate(
		&domain.Car{},
		&domain.Brand{},
		// Добавьте здесь другие модели по мере необходимости
	)
}
