// @title           Cars API
// @version         1.0
// @description     API для работы с машинами, фильтрами и обновлениями из внешних источников.
// @termsOfService  http://example.com/terms/

// @contact.name   API Support
// @contact.url    http://www.example.com/support
// @contact.email  support@example.com

// @license.name  MIT
// @license.url   https://opensource.org/licenses/MIT

// @host      localhost:8080
// @BasePath  /

package main

import (
	"context"
	"log"
	"os"
	"strings"

	_ "datahub/docs"

	"github.com/joho/godotenv"

	httpdelivery "datahub/internal/delivery/http"
	"datahub/internal/infrastructure/database"
	"datahub/internal/infrastructure/external"
	"datahub/internal/infrastructure/migration"
	"datahub/internal/infrastructure/repository"
	"datahub/internal/usecase"
)

func main() {
	_ = godotenv.Load("../.env")
	pgUser := os.Getenv("POSTGRES_USER")
	pgPass := os.Getenv("POSTGRES_PASSWORD")
	pgDB := os.Getenv("POSTGRES_DB")
	pgPort := os.Getenv("POSTGRES_PORT")
	pgHost := os.Getenv("POSTGRES_HOST")
	apiBaseURL := os.Getenv("API_BASE_URL")
	translatorURL := os.Getenv("TRANSLATOR_URL")
	translationEnabled := os.Getenv("TRANSLATION_ENABLED") == "true"

	log.Printf("API_BASE_URL: '%s'", apiBaseURL)
	log.Printf("TRANSLATOR_URL: '%s'", translatorURL)
	log.Printf("TRANSLATION_ENABLED: %t", translationEnabled)
	if pgHost == "" {
		pgHost = "localhost"
	}
	dsn := "postgres://" + pgUser + ":" + pgPass + "@" + pgHost + ":" + pgPort + "/" + pgDB + "?sslmode=disable"

	// Применяем миграции перед инициализацией GORM
	migrationsPath := "./migrations"
	if err := migration.RunMigrations(dsn, migrationsPath); err != nil {
		log.Printf("Warning: failed to run migrations: %v", err)
		log.Println("Continuing without migrations - make sure database schema is up to date")
	}

	// Инициализация GORM
	_, err := database.InitDB(dsn)
	if err != nil {
		log.Fatalf("failed to connect to db: %v", err)
	}
	// database.DB теперь глобально доступен

	repo := repository.NewCarRepository()
	brandRepo := repository.NewBrandRepository()
	taskService := usecase.NewTaskService()
	carService := usecase.NewCarService(repo)
	brandService := usecase.NewBrandService(brandRepo)

	dongchediClient := external.NewDongchediClient(apiBaseURL)
	che168Client := external.NewChe168Client(apiBaseURL)
	pyparsersClient := external.NewPyparsersClient(apiBaseURL)

	// Инициализация сервиса перевода
	var translationService *usecase.TranslationService
	brandsCSVPath := os.Getenv("TRANSLATION_BRANDS_CSV_PATH")
	if brandsCSVPath == "" {
		brandsCSVPath = "./resources/brands.csv"
	}

	if translationEnabled && translatorURL != "" {
		translatorClient := external.NewTranslatorClient(translatorURL)
		translationService = usecase.NewTranslationService(translatorClient, true, brandsCSVPath)
		log.Printf("Translation service initialized with URL: %s", translatorURL)
	} else {
		translationService = usecase.NewTranslationService(nil, false, brandsCSVPath)
		log.Printf("Translation service disabled")
	}

	// Инициализация сервиса калькуляции цен
	cbrClient := external.NewCBRClient("")
	priceCalculator := usecase.NewPriceCalculator(cbrClient)
	
	// Запускаем фоновое обновление курса валют
	ctx := context.Background()
	priceCalculator.Start(ctx)

	updateService := map[string]*usecase.UpdateService{
		"dongchedi": usecase.NewUpdateServiceWithPriceCalculator(repo, dongchediClient, "dongchedi", translationService, priceCalculator),
		"che168":    usecase.NewUpdateServiceWithPriceCalculator(repo, che168Client, "che168", translationService, priceCalculator),
	}

	// Инициализация воркера для улучшения машин
	enhancementWorker := usecase.NewEnhancementWorker(repo, dongchediClient, che168Client, translationService, priceCalculator)

	autoStartWorker := true
	if raw := strings.TrimSpace(os.Getenv("ENHANCEMENT_WORKER_AUTO_START")); raw != "" {
		autoStartWorker = true
		switch strings.ToLower(raw) {
		case "false", "0", "off", "no":
			autoStartWorker = false
		}
	}

	if autoStartWorker {
		enhancementWorker.Start()
		log.Println("Enhancement worker auto-started")
		defer func() {
			if enhancementWorker.IsRunning() {
				enhancementWorker.Stop()
			}
		}()
	} else {
		log.Println("Enhancement worker auto-start disabled; use /enhancement/start to run manually")
	}

	handler := httpdelivery.NewHandler(carService, updateService, brandService, taskService, pyparsersClient, enhancementWorker, priceCalculator)
	router := httpdelivery.NewRouter(handler)

	if err := router.Setup().Run(":8080"); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
