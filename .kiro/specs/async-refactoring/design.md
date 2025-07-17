# Design Document: Asynchronous Refactoring for pyparsers and datahub

## Overview

This design document outlines the approach for refactoring and optimizing the pyparsers and datahub projects to support asynchronous operations while maintaining backward compatibility with existing interfaces. The goal is to improve performance, resource utilization, and concurrency handling without requiring changes to dependent systems.

## Architecture

### Current Architecture

#### pyparsers
- Python-based parser system for extracting car data from various sources
- Uses synchronous HTTP requests via the `requests` library
- Processes data sequentially
- Uses Selenium for browser automation in some cases
- Exposes REST API endpoints via a simple server

#### datahub
- Go-based data management system
- Uses GORM and direct SQL for database operations
- Implements repository pattern for data access
- Processes requests synchronously
- Uses standard Go HTTP server for API endpoints

### Proposed Architecture

#### pyparsers
- Maintain the same external API endpoints and interfaces
- Replace `requests` with `aiohttp` or `httpx` for asynchronous HTTP requests
- Implement asynchronous processing using Python's `asyncio`
- Replace synchronous Selenium operations with asynchronous alternatives where possible
- Use connection pooling for HTTP requests
- Implement task queues for long-running operations

#### datahub
- Maintain the same external API endpoints and interfaces
- Implement Go's concurrency patterns (goroutines and channels)
- Use connection pooling for database operations
- Implement context-based cancellation for long-running operations
- Optimize database queries and transactions

## Components and Interfaces

### pyparsers Components

#### HTTP Client Layer
- **Current:** Uses synchronous `requests` library
- **Proposed:** Replace with asynchronous HTTP client (`aiohttp` or `httpx`)
- **Interface Changes:** None externally, internal methods will use async/await pattern

```python
# Current implementation
def fetch_data(url):
    response = requests.get(url)
    return response.json()

# Proposed implementation
async def fetch_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

#### Parser Layer
- **Current:** Synchronous parsing methods
- **Proposed:** Asynchronous parsing methods with concurrent processing
- **Interface Changes:** None externally, internal methods will use async/await pattern

```python
# Current implementation
def parse_cars(data):
    results = []
    for item in data:
        results.append(process_item(item))
    return results

# Proposed implementation
async def parse_cars(data):
    tasks = [process_item(item) for item in data]
    return await asyncio.gather(*tasks)
```

#### API Layer
- **Current:** Synchronous Flask/FastAPI endpoints
- **Proposed:** Asynchronous FastAPI endpoints
- **Interface Changes:** None externally, same REST API endpoints

```python
# Current implementation
@app.route('/parse', methods=['POST'])
def parse():
    data = request.json
    result = parser.parse(data)
    return jsonify(result)

# Proposed implementation
@app.post('/parse')
async def parse(data: dict):
    result = await parser.parse(data)
    return result
```

### datahub Components

#### Repository Layer
- **Current:** Synchronous database operations
- **Proposed:** Concurrent database operations using goroutines
- **Interface Changes:** None externally, same method signatures

```go
// Current implementation
func (r *CarRepository) List(ctx context.Context, filter *domain.CarFilter, offset, limit int) ([]*domain.Car, int64, error) {
    var cars []*domain.Car
    var count int64
    
    // Sequential operations
    if err := query.Count(&count).Error; err != nil {
        return nil, 0, err
    }
    
    if err := query.Order("sort_number DESC, created_at DESC").
        Offset(offset).
        Limit(limit).
        Find(&cars).Error; err != nil {
        return nil, 0, err
    }
    
    return cars, count, nil
}

// Proposed implementation
func (r *CarRepository) List(ctx context.Context, filter *domain.CarFilter, offset, limit int) ([]*domain.Car, int64, error) {
    var cars []*domain.Car
    var count int64
    
    // Concurrent operations
    var wg sync.WaitGroup
    var countErr, queryErr error
    
    wg.Add(2)
    go func() {
        defer wg.Done()
        if err := query.Count(&count).Error; err != nil {
            countErr = err
        }
    }()
    
    go func() {
        defer wg.Done()
        if err := query.Order("sort_number DESC, created_at DESC").
            Offset(offset).
            Limit(limit).
            Find(&cars).Error; err != nil {
            queryErr = err
        }
    }()
    
    wg.Wait()
    
    if countErr != nil {
        return nil, 0, countErr
    }
    
    if queryErr != nil {
        return nil, 0, queryErr
    }
    
    return cars, count, nil
}
```

#### Database Layer
- **Current:** Uses GORM and direct SQL with synchronous operations
- **Proposed:** Implement connection pooling and concurrent operations
- **Interface Changes:** None externally, same method signatures

#### API Layer
- **Current:** Standard Go HTTP handlers
- **Proposed:** Concurrent request handling with goroutines
- **Interface Changes:** None externally, same API endpoints

## Data Models

No changes to the data models are required for this refactoring. The existing models will be maintained to ensure backward compatibility:

### pyparsers
- `DongchediCar`
- `DongchediApiResponse`
- `DongchediData`

### datahub
- `Car`
- `CarFilter`

## Error Handling

### pyparsers
- Implement proper async exception handling
- Use structured logging for asynchronous operations
- Implement retry mechanisms for transient failures
- Add timeout handling for asynchronous operations

```python
async def fetch_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    return await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as e:
            if attempt == max_retries - 1:
                logger.error(f"Failed to fetch {url} after {max_retries} attempts: {e}")
                raise
            await asyncio.sleep(1 * (2 ** attempt))  # Exponential backoff
```

### datahub
- Implement context-based cancellation
- Add proper error propagation in concurrent operations
- Implement circuit breakers for database operations
- Add structured logging for concurrent operations

```go
func (r *CarRepository) GetWithTimeout(ctx context.Context, uuid string) (*domain.Car, error) {
    // Create a context with timeout
    ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
    defer cancel()
    
    // Use the context with timeout for the database query
    var car domain.Car
    err := r.db.WithContext(ctx).Where("uuid = ?", uuid).First(&car).Error
    if err != nil {
        if errors.Is(err, gorm.ErrRecordNotFound) {
            return nil, nil
        }
        return nil, err
    }
    return &car, nil
}
```

## Testing Strategy

### Unit Testing
- Test asynchronous functions in isolation
- Mock external dependencies
- Test error handling and edge cases
- Ensure backward compatibility

### Integration Testing
- Test the interaction between components
- Verify that the refactored code works with existing systems
- Test performance under load

### Performance Testing
- Benchmark before and after refactoring
- Test resource usage (CPU, memory)
- Test concurrency handling
- Test with different load patterns

## Implementation Approach

### Phase 1: Preparation
1. Add comprehensive tests to ensure current functionality is preserved
2. Set up benchmarking to measure performance improvements
3. Identify critical paths for optimization

### Phase 2: pyparsers Refactoring
1. Introduce asynchronous HTTP client
2. Refactor parser methods to be asynchronous
3. Implement concurrent processing for batch operations
4. Update API layer to support asynchronous operations
5. Optimize resource usage

### Phase 3: datahub Refactoring
1. Implement connection pooling for database operations
2. Add concurrent processing for independent operations
3. Optimize database queries
4. Implement context-based cancellation
5. Enhance error handling

### Phase 4: Testing and Optimization
1. Run comprehensive tests to ensure functionality is preserved
2. Benchmark performance and resource usage
3. Identify and fix bottlenecks
4. Fine-tune concurrency parameters

## Technical Considerations

### pyparsers
- Python's Global Interpreter Lock (GIL) may limit CPU-bound concurrency
- Focus on I/O-bound concurrency with `asyncio`
- Consider using `multiprocessing` for CPU-bound operations
- Ensure proper resource cleanup in asynchronous code

### datahub
- Go's goroutines are lightweight but still consume resources
- Implement proper context cancellation to avoid resource leaks
- Use buffered channels to prevent goroutine leaks
- Consider using worker pools for database operations

## Migration Plan

1. Develop the refactored code in parallel with the existing code
2. Run comprehensive tests to ensure functionality is preserved
3. Deploy the refactored code in a staging environment
4. Monitor performance and resource usage
5. Roll out to production with a fallback plan

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking changes to interfaces | Maintain the same external interfaces and add comprehensive tests |
| Performance regressions | Benchmark before and after refactoring, optimize critical paths |
| Resource leaks | Implement proper resource cleanup and monitoring |
| Increased complexity | Add comprehensive documentation and follow established patterns |
| Database connection issues | Implement connection pooling and circuit breakers |
