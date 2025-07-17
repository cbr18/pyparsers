package server

import (
    "github.com/gin-gonic/gin"
    "github.com/swaggo/files"
    "github.com/swaggo/gin-swagger"
    _ "my-go-api/docs" // Import the generated Swagger docs
)

// StartServer initializes the HTTP server and sets up the routes
func StartServer() {
    r := gin.Default()

    // Swagger documentation route
    r.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))

    // Define other routes here

    // Start the server
    r.Run(":8080") // listen and serve on localhost:8080
}