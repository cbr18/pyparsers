package http

import (
	"context"
	"datahub/internal/domain"
	"datahub/internal/infrastructure/external"
	"datahub/internal/usecase"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
)

type Handler struct {
	carService        *usecase.CarService
	updateService     map[string]*usecase.UpdateService // ключ: source ("dongchedi", "che168")
	brandService      *usecase.BrandService
	taskService       *usecase.TaskService
	pyparsersClient   *external.PyparsersClient
	enhancementWorker *usecase.EnhancementWorker
}

func NewHandler(carService *usecase.CarService, updateService map[string]*usecase.UpdateService, brandService *usecase.BrandService, taskService *usecase.TaskService, pyparsersClient *external.PyparsersClient, enhancementWorker *usecase.EnhancementWorker) *Handler {
	return &Handler{carService: carService, updateService: updateService, brandService: brandService, taskService: taskService, pyparsersClient: pyparsersClient, enhancementWorker: enhancementWorker}
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

    // Меняем поведение на push-модель: быстро создаем задачу в pyparsers и сразу отвечаем
    // Дальше pyparsers сам спарсит и отправит результат в datahub через /api/tasks/{id}/complete
    resp, err := h.pyparsersClient.CreateTask(c.Request.Context(), source, "full", "", nil)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    c.JSON(http.StatusOK, gin.H{
        "status":  "ok",
        "message": "Task created successfully",
        "task_id": resp.TaskID,
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
    // Подготовим existing_ids для инкрементала
    // Для dongchedi используем sku_id, для che168 — car_id
    idField := ""
    var existingIDs []string
    if svc, ok := h.updateService[source]; ok {
        const lastN = 1000
        cars, _ := svc.RepoGetBySourceAndSort(c.Request.Context(), source, lastN)
        if source == "dongchedi" {
            idField = "sku_id"
            for _, car := range cars {
                if car.SkuID != "" {
                    existingIDs = append(existingIDs, car.SkuID)
                }
            }
        } else if source == "che168" {
            idField = "car_id"
            for _, car := range cars {
                if car.CarID != 0 {
                    existingIDs = append(existingIDs, strconv.FormatInt(car.CarID, 10))
                }
            }
        }
    }

    // Увеличиваем таймаут для pyparsers до 5 минут
    ctx, cancel := context.WithTimeout(c.Request.Context(), 5*time.Minute)
    defer cancel()
    
    response, err := h.pyparsersClient.CreateTask(ctx, source, "incremental", idField, existingIDs)
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

// GetCarByUUID godoc
// @Summary      Получить машину по UUID
// @Description  Поиск машины по UUID с полной информацией
// @Tags         cars
// @Accept       json
// @Produce      json
// @Param        uuid   path      string  true  "UUID машины"
// @Success      200    {object}  map[string]interface{}
// @Failure      404    {object}  map[string]string
// @Failure      500    {object}  map[string]string
// @Router       /cars/uuid/{uuid} [get]
func (h *Handler) GetCarByUUID(c *gin.Context) {
	uuid := c.Param("uuid")
	if uuid == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "UUID is required"})
		return
	}

	car, err := h.carService.GetCarByUUID(c.Request.Context(), uuid)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if car == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Car not found"})
		return
	}

	c.JSON(http.StatusOK, gin.H{"data": car})
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
        TaskID   string      `json:"task_id" binding:"required"`
        Source   string      `json:"source" binding:"required"`
        TaskType string      `json:"task_type" binding:"required"`
        Status   string      `json:"status" binding:"required"`
        Data     []domain.Car `json:"data" binding:"required"`
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
	
    // Создаем задачу в сервисе задач (тип из запроса)
    task, err := h.taskService.CreateTask(req.Source, req.TaskType)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	
    // Сохраняем данные машин в базу через существующий сервис
	service, ok := h.updateService[req.Source]
	if !ok {
		c.JSON(http.StatusBadRequest, gin.H{"error": "unknown source"})
		return
	}

    // Full: защищаемся от пустого датасета и делаем замену атомарно
    if req.TaskType == "full" {
        if len(req.Data) == 0 {
            c.JSON(http.StatusUnprocessableEntity, gin.H{"error": "empty dataset for full update"})
            return
        }
        // Присвоим sort_number детерминированно: новые сверху => больший номер
        total := len(req.Data)
        for i := range req.Data {
            req.Data[i].Source = req.Source
            req.Data[i].SortNumber = total - i
        }
        if err := service.ReplaceSource(c.Request.Context(), req.Data); err != nil {
            c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
            return
        }
    } else {
        // Incremental: наращиваем сверху — возьмем текущий max и назначим по порядку
        if err := service.AppendIncremental(c.Request.Context(), req.Data); err != nil {
            c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
            return
        }
    }

    // Обновляем статус задачи на "done" (после успешной записи)
    h.taskService.UpdateTaskStatus(task.ID, "done", &domain.TaskResult{
        Count:   len(req.Data),
        Message: "Data received from pyparsers",
    }, nil)
	
	c.JSON(http.StatusOK, gin.H{"status": "ok"})
}

// GetEnhancementStatus godoc
// @Summary      Получить статус воркера улучшения машин
// @Description  Возвращает информацию о работе фонового процесса улучшения машин
// @Tags         enhancement
// @Produce      json
// @Success      200  {object}  map[string]interface{}
// @Router       /enhancement/status [get]
func (h *Handler) GetEnhancementStatus(c *gin.Context) {
	status, err := h.enhancementWorker.GetStatus(c.Request.Context())
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	c.JSON(http.StatusOK, status)
}

// StartEnhancement godoc
// @Summary      Запустить воркер улучшения машин
// @Description  Запускает фоновый процесс улучшения машин детальной информацией
// @Tags         enhancement
// @Produce      json
// @Success      200  {object}  map[string]interface{}
// @Router       /enhancement/start [post]
func (h *Handler) StartEnhancement(c *gin.Context) {
	h.enhancementWorker.Start()
	c.JSON(http.StatusOK, gin.H{"status": "started"})
}

// StopEnhancement godoc
// @Summary      Остановить воркер улучшения машин
// @Description  Останавливает фоновый процесс улучшения машин
// @Tags         enhancement
// @Produce      json
// @Success      200  {object}  map[string]interface{}
// @Router       /enhancement/stop [post]
func (h *Handler) StopEnhancement(c *gin.Context) {
	h.enhancementWorker.Stop()
	c.JSON(http.StatusOK, gin.H{"status": "stopped"})
}

// ConfigureEnhancement godoc
// @Summary      Настроить воркер улучшения машин
// @Description  Обновляет конфигурацию фонового процесса улучшения машин
// @Tags         enhancement
// @Accept       json
// @Produce      json
// @Param        config  body  object  true  "Конфигурация"
// @Success      200  {object}  map[string]interface{}
// @Router       /enhancement/config [post]
func (h *Handler) ConfigureEnhancement(c *gin.Context) {
	var config struct {
		BatchSize          int `json:"batch_size"`
		DelayBetweenBatchesSec int `json:"delay_between_batches_sec"`
		DelayBetweenCarsSec    int `json:"delay_between_cars_sec"`
		MaxConcurrent      int `json:"max_concurrent"`
	}

	if err := c.ShouldBindJSON(&config); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	h.enhancementWorker.SetConfig(
		config.BatchSize,
		time.Duration(config.DelayBetweenBatchesSec)*time.Second,
		time.Duration(config.DelayBetweenCarsSec)*time.Second,
		config.MaxConcurrent,
	)

	c.JSON(http.StatusOK, gin.H{"status": "configured"})
}
