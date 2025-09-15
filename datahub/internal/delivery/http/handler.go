package http

import (
	"datahub/internal/domain"
	"datahub/internal/infrastructure/external"
	"datahub/internal/usecase"
	"net/http"
	"strconv"
	"strings"

	"github.com/gin-gonic/gin"
)

type Handler struct {
	carService      *usecase.CarService
	updateService   map[string]*usecase.UpdateService // ключ: source ("dongchedi", "che168")
	brandService    *usecase.BrandService
	taskService     *usecase.TaskService
	pyparsersClient *external.PyparsersClient
}

func NewHandler(carService *usecase.CarService, updateService map[string]*usecase.UpdateService, brandService *usecase.BrandService, taskService *usecase.TaskService, pyparsersClient *external.PyparsersClient) *Handler {
	return &Handler{carService: carService, updateService: updateService, brandService: brandService, taskService: taskService, pyparsersClient: pyparsersClient}
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
// @Description  Создает задачу полного обновления данных для источника (dongchedi/che168) в pyparsers
// @Tags         update
// @Produce      json
// @Param        source path string true "Источник"
// @Success      200 {object} map[string]string
// @Failure      400 {object} map[string]string
// @Failure      500 {object} map[string]string
// @Router       /update/{source}/full [get]
func (h *Handler) FullUpdate(c *gin.Context) {
	source := c.Param("source")
	if source != "dongchedi" && source != "che168" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "unknown source"})
		return
	}
	
	// Создаем задачу в pyparsers
	response, err := h.pyparsersClient.CreateTask(c.Request.Context(), source)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{
		"status": "ok", 
		"message": "Task created successfully",
		"task_id": response.TaskID,
	})
}

// isDuplicateKeyError проверяет, является ли ошибка нарушением ограничения уникальности
func isDuplicateKeyError(err error) bool {
	errMsg := err.Error()
	return strings.Contains(errMsg, "duplicate key value violates unique constraint") ||
		strings.Contains(errMsg, "UNIQUE constraint failed") ||
		strings.Contains(errMsg, "Duplicate entry")
}

// POST /update/{source}
// @Summary      Инкрементальное обновление источника
// @Description  Создает задачу инкрементального обновления для источника (dongchedi/che168) в pyparsers
// @Tags         update
// @Accept       json
// @Produce      json
// @Param        source path string true "Источник"
// @Param        request body object{last_n=int} true "Сколько последних обновить (игнорируется в push-модели)"
// @Success      200 {object} map[string]string
// @Failure      400 {object} map[string]string
// @Failure      500 {object} map[string]string
// @Router       /update/{source} [post]
func (h *Handler) IncrementalUpdate(c *gin.Context) {
	source := c.Param("source")
	if source != "dongchedi" && source != "che168" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "unknown source"})
		return
	}
	
	// Игнорируем last_n в push-модели, так как pyparsers сам определяет что парсить
	var req struct {
		LastN int `json:"last_n"`
	}
	if err := c.ShouldBindJSON(&req); err != nil {
		// Если не удалось распарсить JSON, продолжаем без ошибки
	}
	
	// Создаем задачу в pyparsers
	response, err := h.pyparsersClient.CreateTask(c.Request.Context(), source)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{
		"status": "ok", 
		"message": "Task created successfully",
		"task_id": response.TaskID,
	})
}

// GetBrands godoc
// @Summary      Получить список брендов
// @Description  Список всех брендов
// @Tags         brands
// @Accept       json
// @Produce      json
// @Success      200    {object}  map[string]interface{}
// @Router       /brands [get]
func (h *Handler) GetBrands(c *gin.Context) {
	brands, err := h.brandService.ListAllBrands(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, gin.H{"data": brands})
}

// CompleteTask godoc
// @Summary      Завершить задачу парсинга
// @Description  Принимает результаты парсинга от pyparsers и сохраняет их в БД
// @Tags         tasks
// @Accept       json
// @Produce      json
// @Param        id   path      string                    true  "ID задачи"
// @Param        request body   object{task_id=string,source=string,status=string,data=array} true "Данные для завершения задачи"
// @Success      200   {object} map[string]string
// @Failure      400   {object} map[string]string
// @Failure      500   {object} map[string]string
// @Router       /api/tasks/{id}/complete [post]
func (h *Handler) CompleteTask(c *gin.Context) {
	taskID := c.Param("id")
	
	var req struct {
		TaskID string      `json:"task_id" binding:"required"`
		Source string      `json:"source" binding:"required"`
		Status string      `json:"status" binding:"required"`
		Data   []domain.Car `json:"data" binding:"required"`
	}
	
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request"})
		return
	}
	
	// Проверяем, что ID в пути совпадает с ID в теле запроса
	if req.TaskID != taskID {
		c.JSON(http.StatusBadRequest, gin.H{"error": "task ID mismatch"})
		return
	}
	
	// Создаем задачу в сервисе задач
	task, err := h.taskService.CreateTask(req.Source, "full")
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	
	// Обновляем статус задачи на "done"
	h.taskService.UpdateTaskStatus(task.ID, "done", &domain.TaskResult{
		Count:   len(req.Data),
		Message: "Data received from pyparsers",
	}, nil)
	
	// Сохраняем данные машин в базу через существующий сервис
	service, ok := h.updateService[req.Source]
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "unknown source"})
		return
	}
	
	// Используем существующий метод для сохранения данных
	err = service.SaveCars(c.Request.Context(), req.Data)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}
