package http

import (
	"datahub/internal/domain"
	"datahub/internal/usecase"
	"net/http"
	"strconv"

	"github.com/gin-gonic/gin"
)

type Handler struct {
	carService    *usecase.CarService
	updateService map[string]*usecase.UpdateService // ключ: source ("dongchedi", "che168")
}

func NewHandler(carService *usecase.CarService, updateService map[string]*usecase.UpdateService) *Handler {
	return &Handler{carService: carService, updateService: updateService}
}

// GetCars godoc
// @Summary      Получить список машин
// @Description  Список машин с фильтрами и пагинацией
// @Tags         cars
// @Accept       json
// @Produce      json
// @Param        page   query     int     false  "Номер страницы"
// @Param        limit  query     int     false  "Размер страницы"
// @Param        source query     string  false  "Источник"
// @Param        brand  query     string  false  "Бренд"
// @Param        city   query     string  false  "Город"
// @Param        year   query     string  false  "Год"
// @Param        search query     string  false  "Поиск"
// @Success      200    {object}  map[string]interface{}
// @Router       /cars [get]
func (h *Handler) GetCars(c *gin.Context) {
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))
	var filter domain.CarFilter
	if source := c.Query("source"); source != "" {
		filter.Source = &source
	}
	if brand := c.Query("brand"); brand != "" {
		filter.BrandName = &brand
	}
	if city := c.Query("city"); city != "" {
		filter.City = &city
	}
	if year := c.Query("year"); year != "" {
		filter.Year = &year
	}
	if search := c.Query("search"); search != "" {
		filter.Search = &search
	}
cars, total, err := h.carService.ListCars(c.Request.Context(), filter, page, limit, "sort_number DESC")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"data": cars, "total": total})
}

// POST /checkcar
// @Summary      Проверить машину по источнику и id/url
// @Description  Проверяет наличие и детали машины по источнику (dongchedi/che168) и id/url
// @Tags         cars
// @Accept       json
// @Produce      json
// @Param        request body object{source=string,car_id=string,car_url=string} true "Данные для проверки"
// @Success      200 {object} map[string]interface{}
// @Failure      400 {object} map[string]string
// @Failure      500 {object} map[string]string
// @Router       /checkcar [post]
func (h *Handler) CheckCar(c *gin.Context) {
	var req struct {
		Source string `json:"source"`
		CarID  string `json:"car_id"`
		CarURL string `json:"car_url"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request"})
		return
	}
	service, ok := h.updateService[req.Source]
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "unknown source"})
		return
	}
	var car *domain.Car
	var err error
	if req.Source == "dongchedi" {
		car, err = service.CheckCar(c.Request.Context(), req.CarID)
	} else if req.Source == "che168" {
		car, err = service.CheckCar(c.Request.Context(), req.CarURL)
	} else {
		c.JSON(http.StatusBadRequest, gin.H{"error": "unsupported source"})
		return
	}
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, car)
}

// GET /update/{source}/full
// @Summary      Полное обновление источника
// @Description  Запускает полное обновление данных для источника (dongchedi/che168)
// @Tags         update
// @Produce      json
// @Param        source path string true "Источник"
// @Success      200 {object} map[string]string
// @Failure      400 {object} map[string]string
// @Failure      500 {object} map[string]string
// @Router       /update/{source}/full [get]
func (h *Handler) FullUpdate(c *gin.Context) {
	source := c.Param("source")
	service, ok := h.updateService[source]
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "unknown source"})
		return
	}
	if err := service.FullUpdate(c.Request.Context()); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

// POST /update/{source}
// @Summary      Инкрементальное обновление источника
// @Description  Запускает обновление последних N записей для источника (dongchedi/che168)
// @Tags         update
// @Accept       json
// @Produce      json
// @Param        source path string true "Источник"
// @Param        request body object{last_n=int} true "Сколько последних обновить"
// @Success      200 {object} map[string]string
// @Failure      400 {object} map[string]string
// @Failure      500 {object} map[string]string
// @Router       /update/{source} [post]
func (h *Handler) IncrementalUpdate(c *gin.Context) {
	source := c.Param("source")
	service, ok := h.updateService[source]
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "unknown source"})
		return
	}
	var req struct {
		LastN int `json:"last_n"`
	}
	if err := c.ShouldBindJSON(&req); err != nil || req.LastN <= 0 {
		req.LastN = 5 // по умолчанию
	}
	if err := service.IncrementalUpdate(c.Request.Context(), req.LastN); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}
