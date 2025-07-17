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
	"database/sql"
	"log"
	"os"
	"time"

	_ "datahub/docs"

	"github.com/joho/godotenv"
	_ "github.com/lib/pq"

	httpdelivery "datahub/internal/delivery/http"
	"datahub/internal/infrastructure/db"
	"datahub/internal/infrastructure/external"
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
	dbConn, err := sql.Open("postgres", dsn)
	if err != nil {
		log.Fatalf("failed to connect to db: %v", err)
	}
	defer dbConn.Close()
	dbConn.SetMaxOpenConns(10)
	dbConn.SetConnMaxLifetime(time.Hour)

	repo := db.NewCarPostgres(dbConn)
	carService := usecase.NewCarService(repo)

	dongchediClient := external.NewDongchediClient(apiBaseURL)
	che168Client := external.NewChe168Client(apiBaseURL)
	updateService := map[string]*usecase.UpdateService{
		"dongchedi": usecase.NewUpdateService(repo, dongchediClient, "dongchedi"),
		"che168":    usecase.NewUpdateService(repo, che168Client, "che168"),
	}

	handler := httpdelivery.NewHandler(carService, updateService)
	router := httpdelivery.NewRouter(handler)

	if err := router.Setup().Run(":8080"); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
