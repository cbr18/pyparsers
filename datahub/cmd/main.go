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
	"log"
	"os"

	_ "datahub/docs"

	"github.com/joho/godotenv"

	httpdelivery "datahub/internal/delivery/http"
	"datahub/internal/infrastructure/database"
	"datahub/internal/infrastructure/external"
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
	log.Printf("API_BASE_URL: '%s'", apiBaseURL)
	if pgHost == "" {
		pgHost = "localhost"
	}
	dsn := "postgres://" + pgUser + ":" + pgPass + "@" + pgHost + ":" + pgPort + "/" + pgDB + "?sslmode=disable"

	// Инициализация GORM
	_, err := database.InitDB(dsn)
	if err != nil {
		log.Fatalf("failed to connect to db: %v", err)
	}
	// database.DB теперь глобально доступен

	repo := repository.NewCarRepository()
	brandRepo := repository.NewBrandRepository()
	carService := usecase.NewCarService(repo)
	brandService := usecase.NewBrandService(brandRepo)

	dongchediClient := external.NewDongchediClient(apiBaseURL)
	che168Client := external.NewChe168Client(apiBaseURL)
	updateService := map[string]*usecase.UpdateService{
		"dongchedi": usecase.NewUpdateService(repo, dongchediClient, "dongchedi"),
		"che168":    usecase.NewUpdateService(repo, che168Client, "che168"),
	}

	handler := httpdelivery.NewHandler(carService, updateService, brandService)
	router := httpdelivery.NewRouter(handler)

	if err := router.Setup().Run(":8080"); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
