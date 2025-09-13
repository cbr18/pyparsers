package migration

import (
	"database/sql"
	"fmt"
	"log"
	"path/filepath"

	"github.com/golang-migrate/migrate/v4"
	"github.com/golang-migrate/migrate/v4/database/postgres"
	_ "github.com/golang-migrate/migrate/v4/source/file"
	_ "github.com/lib/pq"
)

// RunMigrations применяет все доступные миграции
func RunMigrations(databaseURL, migrationsPath string) error {
	log.Println("Starting database migrations...")

	// Открываем соединение с базой данных
	db, err := sql.Open("postgres", databaseURL)
	if err != nil {
		return fmt.Errorf("failed to open database connection: %w", err)
	}
	defer db.Close()

	// Проверяем соединение
	if err := db.Ping(); err != nil {
		return fmt.Errorf("failed to ping database: %w", err)
	}

	// Создаем драйвер для postgres
	driver, err := postgres.WithInstance(db, &postgres.Config{})
	if err != nil {
		return fmt.Errorf("failed to create postgres driver: %w", err)
	}

	// Получаем абсолютный путь к миграциям
	absPath, err := filepath.Abs(migrationsPath)
	if err != nil {
		return fmt.Errorf("failed to get absolute path for migrations: %w", err)
	}

	// Создаем экземпляр migrate
	m, err := migrate.NewWithDatabaseInstance(
		fmt.Sprintf("file://%s", absPath),
		"postgres",
		driver,
	)
	if err != nil {
		return fmt.Errorf("failed to create migrate instance: %w", err)
	}
	defer m.Close()

	// Получаем текущую версию
	currentVersion, dirty, err := m.Version()
	if err != nil && err != migrate.ErrNilVersion {
		return fmt.Errorf("failed to get current migration version: %w", err)
	}

	if dirty {
		log.Printf("Database is in dirty state at version %d, attempting to fix...", currentVersion)
		// В случае dirty state, можно попробовать force к текущей версии
		if err := m.Force(int(currentVersion)); err != nil {
			return fmt.Errorf("failed to force migration version %d: %w", currentVersion, err)
		}
	}

	log.Printf("Current migration version: %d", currentVersion)

	// Применяем все доступные миграции
	err = m.Up()
	if err != nil && err != migrate.ErrNoChange {
		return fmt.Errorf("failed to run migrations: %w", err)
	}

	if err == migrate.ErrNoChange {
		log.Println("No new migrations to apply")
	} else {
		// Получаем новую версию после миграции
		newVersion, _, err := m.Version()
		if err != nil {
			log.Println("Migrations applied successfully, but failed to get new version")
		} else {
			log.Printf("Migrations applied successfully. New version: %d", newVersion)
		}
	}

	return nil
}

// CheckMigrationStatus проверяет статус миграций без их применения
func CheckMigrationStatus(databaseURL, migrationsPath string) error {
	log.Println("Checking migration status...")

	db, err := sql.Open("postgres", databaseURL)
	if err != nil {
		return fmt.Errorf("failed to open database connection: %w", err)
	}
	defer db.Close()

	if err := db.Ping(); err != nil {
		return fmt.Errorf("failed to ping database: %w", err)
	}

	driver, err := postgres.WithInstance(db, &postgres.Config{})
	if err != nil {
		return fmt.Errorf("failed to create postgres driver: %w", err)
	}

	absPath, err := filepath.Abs(migrationsPath)
	if err != nil {
		return fmt.Errorf("failed to get absolute path for migrations: %w", err)
	}

	m, err := migrate.NewWithDatabaseInstance(
		fmt.Sprintf("file://%s", absPath),
		"postgres",
		driver,
	)
	if err != nil {
		return fmt.Errorf("failed to create migrate instance: %w", err)
	}
	defer m.Close()

	currentVersion, dirty, err := m.Version()
	if err != nil && err != migrate.ErrNilVersion {
		return fmt.Errorf("failed to get current migration version: %w", err)
	}

	if dirty {
		log.Printf("WARNING: Database is in dirty state at version %d", currentVersion)
		return fmt.Errorf("database is in dirty state at version %d", currentVersion)
	}

	if err == migrate.ErrNilVersion {
		log.Println("No migrations have been applied yet")
	} else {
		log.Printf("Current migration version: %d", currentVersion)
	}

	return nil
}
