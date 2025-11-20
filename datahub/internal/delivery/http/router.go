package http

import (
	"github.com/gin-gonic/gin"
	swaggerFiles "github.com/swaggo/files"
	ginSwagger "github.com/swaggo/gin-swagger"
)

type Router struct {
	handler *Handler
}

func NewRouter(handler *Handler) *Router {
	return &Router{handler: handler}
}

func (r *Router) Setup() *gin.Engine {
   e := gin.Default()
   e.GET("/cars", r.handler.GetCars)
   e.GET("/cars/uuid/:uuid", r.handler.GetCarByUUID)
   e.POST("/checkcar", r.handler.CheckCar)
   e.GET("/update/:source/full", r.handler.FullUpdate)
   e.POST("/update/:source", r.handler.IncrementalUpdate)
   e.GET("/brands", r.handler.GetBrands)
   e.POST("/api/tasks/:id/complete", r.handler.CompleteTask)
   
   // Enhancement endpoints
   e.GET("/enhancement/status", r.handler.GetEnhancementStatus)
   e.POST("/enhancement/start", r.handler.StartEnhancement)
   e.POST("/enhancement/stop", r.handler.StopEnhancement)
   e.POST("/enhancement/config", r.handler.ConfigureEnhancement)
   
   // Debug endpoints
   e.POST("/debug/price", r.handler.DebugPrice)
   
   // Swagger UI
   e.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))
   return e
}
