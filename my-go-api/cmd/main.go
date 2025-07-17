package main

import (
    "github.com/gin-gonic/gin"
    "github.com/swaggo/files"
    "github.com/swaggo/gin-swagger"
    _ "my-go-api/docs" // This is the path to your swagger.json file
)

func main() {
    r := gin.Default()

    // Swagger documentation
    r.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))

    // Set up your routes here
    // r.GET("/api/endpoint", handlers.YourHandlerFunction)

    r.Run(":8080") // Start the server on port 8080
}