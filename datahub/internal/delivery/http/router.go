package http

import (
	"log"
	"net"
	"os"
	"strings"

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

// IPWhitelistMiddleware проверяет IP клиента по whitelist
func IPWhitelistMiddleware() gin.HandlerFunc {
	// Читаем разрешённые IP из переменной окружения
	allowedIPsRaw := strings.TrimSpace(os.Getenv("ALLOWED_IPS"))
	
	// Если не задано - пропускаем всех (для обратной совместимости)
	if allowedIPsRaw == "" {
		log.Println("WARNING: ALLOWED_IPS not set - access open to everyone!")
		return func(c *gin.Context) {
			c.Next()
		}
	}
	
	// Парсим список IP/CIDR
	var allowedNets []*net.IPNet
	var allowedIPs []net.IP
	
	for _, item := range strings.Split(allowedIPsRaw, ",") {
		item = strings.TrimSpace(item)
		if item == "" {
			continue
		}
		
		// Пробуем как CIDR
		if strings.Contains(item, "/") {
			_, ipNet, err := net.ParseCIDR(item)
			if err != nil {
				log.Printf("WARNING: Invalid CIDR in ALLOWED_IPS: %s - %v", item, err)
				continue
			}
			allowedNets = append(allowedNets, ipNet)
		} else {
			// Одиночный IP
			ip := net.ParseIP(item)
			if ip == nil {
				log.Printf("WARNING: Invalid IP in ALLOWED_IPS: %s", item)
				continue
			}
			allowedIPs = append(allowedIPs, ip)
		}
	}
	
	log.Printf("IP Whitelist enabled. Allowed: %s", allowedIPsRaw)
	
	// Публичные пути (без проверки IP)
	publicPaths := map[string]bool{
		"/health": true,
	}
	
	return func(c *gin.Context) {
		// Публичные эндпоинты пропускаем
		if publicPaths[c.Request.URL.Path] {
			c.Next()
			return
		}
		
		// Получаем IP клиента
		clientIP := getClientIP(c)
		
		// Проверяем IP
		if !isIPAllowed(clientIP, allowedIPs, allowedNets) {
			log.Printf("Access denied for IP: %s -> %s", clientIP, c.Request.URL.Path)
			c.AbortWithStatusJSON(403, gin.H{
				"data":    nil,
				"message": "Access denied: IP not in whitelist",
				"status":  403,
			})
			return
		}
		
		c.Next()
	}
}

func getClientIP(c *gin.Context) string {
	// Проверяем заголовки прокси
	if xff := c.GetHeader("X-Forwarded-For"); xff != "" {
		// X-Forwarded-For: client, proxy1, proxy2
		parts := strings.Split(xff, ",")
		return strings.TrimSpace(parts[0])
	}
	
	if xri := c.GetHeader("X-Real-IP"); xri != "" {
		return strings.TrimSpace(xri)
	}
	
	// Fallback: прямое подключение
	ip, _, _ := net.SplitHostPort(c.Request.RemoteAddr)
	return ip
}

func isIPAllowed(clientIPStr string, allowedIPs []net.IP, allowedNets []*net.IPNet) bool {
	clientIP := net.ParseIP(clientIPStr)
	if clientIP == nil {
		return false
	}
	
	// Проверяем одиночные IP
	for _, ip := range allowedIPs {
		if ip.Equal(clientIP) {
			return true
		}
	}
	
	// Проверяем сети
	for _, ipNet := range allowedNets {
		if ipNet.Contains(clientIP) {
			return true
		}
	}
	
	return false
}

func (r *Router) Setup() *gin.Engine {
   e := gin.Default()
   
   // Добавляем IP whitelist middleware
   e.Use(IPWhitelistMiddleware())
   
   // Health check (публичный, без проверки IP)
   e.GET("/health", func(c *gin.Context) {
      c.JSON(200, gin.H{"status": "ok"})
   })
   
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

   // Validation endpoints
   e.GET("/validation/status", r.handler.GetValidationStatus)
   e.POST("/validation/start", r.handler.StartValidation)
   e.POST("/validation/stop", r.handler.StopValidation)
   e.POST("/validation/config", r.handler.ConfigureValidation)
   
   // Debug endpoints
   e.POST("/debug/price", r.handler.DebugPrice)
   
   // Swagger UI
   e.GET("/swagger/*any", ginSwagger.WrapHandler(swaggerFiles.Handler))
   return e
}
