# CarCatch API Examples

This document provides practical examples of using the CarCatch API.

## Base URLs

- **Production:** `https://car-catch.ru`
- **Development:** `http://localhost:8000`
- **Direct Services:**
  - DataHub: `http://localhost:8080`
  - Dongchedi parser: `http://localhost:5001`
  - Che168 parser: `http://localhost:5002`
  - Telegram Bot: `http://localhost:3001`

## Authentication

Currently, the API does not require authentication for most endpoints.

## Common Headers

```bash
Content-Type: application/json
Accept: application/json
```

## Cars API Examples

### 1. Get All Cars (Paginated)

```bash
# Basic request
curl "http://localhost/cars"

# With pagination
curl "http://localhost/cars?page=1&limit=20"

# With filters
curl "http://localhost/cars?source=dongchedi&brand=BMW&city=北京&year=2020"

# Search query
curl "http://localhost/cars?search=BMW X5"
```

**JavaScript Example:**
```javascript
const response = await fetch('/cars?page=1&limit=10&source=dongchedi');
const data = await response.json();
console.log(data.data); // Array of cars
console.log(data.total); // Total count
```

**Response:**
```json
{
  "data": [
    {
      "uuid": "550e8400-e29b-41d4-a716-446655440000",
      "car_id": "123456",
      "brand_name": "BMW",
      "car_name": "X5",
      "series_name": "X系列",
      "year": "2020",
      "city": "北京",
      "price": "450000",
      "source": "dongchedi",
      "sort_number": 100,
      "link": "https://dongchedi.com/car/123456"
    }
  ],
  "total": 1500
}
```

### 2. Check Specific Car

```bash
# Check dongchedi car by ID
curl -X POST "http://localhost/checkcar" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "dongchedi",
    "car_id": "123456"
  }'

# Check che168 car by URL
curl -X POST "http://localhost/checkcar" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "che168",
    "car_url": "https://che168.com/car/123456"
  }'
```

**JavaScript Example:**
```javascript
const checkCar = async (source, identifier) => {
  const body = source === 'dongchedi' 
    ? { source, car_id: identifier }
    : { source, car_url: identifier };
    
  const response = await fetch('/checkcar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  
  return await response.json();
};
```

### 3. Get Brands

```bash
curl "http://localhost/brands"
```

**Response:**
```json
{
  "data": [
    {
      "id": 1,
      "name": "BMW",
      "count": 1200
    },
    {
      "id": 2,
      "name": "Mercedes-Benz",
      "count": 1100
    }
  ]
}
```

## PyParsers API Examples

### 1. Get Cars from Dongchedi

```bash
# First page
curl "http://localhost:5001/cars/dongchedi"

# Specific page
curl "http://localhost:5001/cars/dongchedi/page/2"

# All cars (warning: may take time)
curl "http://localhost:5001/cars/dongchedi/all"
```

### 2. Incremental Update

```bash
curl -X POST "http://localhost:5001/cars/dongchedi/incremental" \
  -H "Content-Type: application/json" \
  -d '{
    "existing_cars": [
      {
        "car_id": "123456",
        "source": "dongchedi"
      }
    ]
  }'
```

### 3. Get Car Details

```bash
# Single car details
curl "http://localhost:5001/cars/dongchedi/car/123456"

# Multiple cars (max 20)
curl -X POST "http://localhost:5001/cars/dongchedi/cars" \
  -H "Content-Type: application/json" \
  -d '{
    "car_ids": ["123456", "789012", "345678"]
  }'
```

### 4. Get Statistics

```bash
curl "http://localhost:5001/cars/dongchedi/stats"
```

**Response:**
```json
{
  "data": {
    "total_cars": 15000,
    "has_more_pages": true,
    "cars_on_first_page": 20,
    "top_brands": {
      "BMW": 1200,
      "Mercedes-Benz": 1100,
      "Audi": 950
    },
    "timestamp": "2025-01-09T10:30:00.000Z"
  },
  "message": "Статистика по машинам с dongchedi",
  "status": 200
}
```

### 5. Probe IP Block Status

```bash
curl "http://localhost:5001/blocked/dongchedi"
curl "http://localhost:5002/blocked/che168"
```

**Response:**
```json
{
  "data": {
    "source": "dongchedi",
    "blocked": 0,
    "checks": {
      "list": 1,
      "detailed": 1
    },
    "details": {
      "list_count": 20,
      "probe_car_id": "7398947128411625779",
      "detail_status": 200,
      "detail_is_banned": 0,
      "detail_has_images": 1,
      "detail_has_registration": 1
    }
  },
  "message": "Source availability probe completed",
  "status": 200
}
```

`blocked=1` means the service could not complete the same list+detailed parsing flow that the public endpoints use.

## Update Operations

### 1. Full Update

```bash
# Update all dongchedi cars
curl "http://localhost/update/dongchedi/full"

# Update all che168 cars
curl "http://localhost/update/che168/full"
```

### 2. Incremental Update

```bash
# Update last 10 records
curl -X POST "http://localhost/update/dongchedi" \
  -H "Content-Type: application/json" \
  -d '{"last_n": 10}'
```

## Telegram Bot Examples

### 1. Submit Lead Request

```bash
curl -X POST "http://localhost/lead" \
  -H "Content-Type: application/json" \
  -d '{
    "car": {
      "brand_name": "BMW",
      "car_name": "X5",
      "year": "2020",
      "city": "北京",
      "price": "450000",
      "link": "https://dongchedi.com/car/123456"
    },
    "user": "John Doe"
  }'
```

**JavaScript Example:**
```javascript
const submitLead = async (car, user = '') => {
  const response = await fetch('/lead', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ car, user })
  });
  
  if (!response.ok) {
    throw new Error('Failed to submit lead');
  }
  
  return await response.json();
};

// Usage
const car = {
  brand_name: "BMW",
  car_name: "X5",
  year: "2020",
  city: "北京",
  price: "450000"
};

submitLead(car, "John Doe")
  .then(result => console.log('Lead submitted:', result))
  .catch(error => console.error('Error:', error));
```

## Frontend Integration Examples

### React Component Example

```jsx
import React, { useState, useEffect } from 'react';

const CarsList = () => {
  const [cars, setCars] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    page: 1,
    limit: 20,
    source: '',
    brand: '',
    city: '',
    year: '',
    search: ''
  });

  useEffect(() => {
    const fetchCars = async () => {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        Object.entries(filters).forEach(([key, value]) => {
          if (value) params.append(key, value);
        });

        const response = await fetch(`/cars?${params}`);
        const data = await response.json();
        setCars(data.data || []);
      } catch (error) {
        console.error('Error fetching cars:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCars();
  }, [filters]);

  const handleSubmitLead = async (car) => {
    try {
      await fetch('/lead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ car, user: 'Web User' })
      });
      alert('Lead submitted successfully!');
    } catch (error) {
      alert('Error submitting lead');
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div>
      {cars.map(car => (
        <div key={car.uuid} className="car-card">
          <h3>{car.brand_name} {car.car_name}</h3>
          <p>Year: {car.year}</p>
          <p>City: {car.city}</p>
          <p>Price: {car.price}</p>
          <button onClick={() => handleSubmitLead(car)}>
            Submit Lead
          </button>
        </div>
      ))}
    </div>
  );
};

export default CarsList;
```

### Angular Service Example

```typescript
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Car {
  uuid: string;
  car_id: string;
  brand_name: string;
  car_name: string;
  year: string;
  city: string;
  price: string;
  source: string;
}

export interface CarsResponse {
  data: Car[];
  total: number;
}

@Injectable({
  providedIn: 'root'
})
export class CarsService {
  private apiUrl = '/cars';

  constructor(private http: HttpClient) {}

  getCars(filters: any = {}): Observable<CarsResponse> {
    let params = new HttpParams();
    
    Object.keys(filters).forEach(key => {
      if (filters[key]) {
        params = params.set(key, filters[key]);
      }
    });

    return this.http.get<CarsResponse>(this.apiUrl, { params });
  }

  submitLead(car: Car, user: string = ''): Observable<any> {
    return this.http.post('/lead', { car, user });
  }

  getBrands(): Observable<any> {
    return this.http.get('/brands');
  }
}
```

## Error Handling Examples

### JavaScript Error Handling

```javascript
const apiCall = async (url, options = {}) => {
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      ...options
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || `HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
};

// Usage with error handling
apiCall('/cars?page=1')
  .then(data => {
    console.log('Cars loaded:', data);
  })
  .catch(error => {
    console.error('Failed to load cars:', error.message);
    // Show user-friendly error message
  });
```

### Retry Logic Example

```javascript
const apiCallWithRetry = async (url, options = {}, maxRetries = 3) => {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const response = await fetch(url, options);
      
      if (response.ok) {
        return await response.json();
      }
      
      if (response.status >= 500 && attempt < maxRetries) {
        // Retry on server errors
        await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
        continue;
      }
      
      throw new Error(`HTTP ${response.status}`);
    } catch (error) {
      if (attempt === maxRetries) {
        throw error;
      }
      
      // Wait before retry
      await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
    }
  }
};
```

## Performance Optimization

### Caching Example

```javascript
class CarsCache {
  constructor(ttl = 5 * 60 * 1000) { // 5 minutes
    this.cache = new Map();
    this.ttl = ttl;
  }

  get(key) {
    const item = this.cache.get(key);
    if (!item) return null;
    
    if (Date.now() > item.expiry) {
      this.cache.delete(key);
      return null;
    }
    
    return item.data;
  }

  set(key, data) {
    this.cache.set(key, {
      data,
      expiry: Date.now() + this.ttl
    });
  }

  async getCars(filters) {
    const key = JSON.stringify(filters);
    let data = this.get(key);
    
    if (!data) {
      const response = await fetch(`/cars?${new URLSearchParams(filters)}`);
      data = await response.json();
      this.set(key, data);
    }
    
    return data;
  }
}

const carsCache = new CarsCache();
```

### Pagination Helper

```javascript
class PaginationHelper {
  constructor(apiUrl, pageSize = 20) {
    this.apiUrl = apiUrl;
    this.pageSize = pageSize;
    this.currentPage = 1;
    this.totalPages = 1;
    this.totalItems = 0;
  }

  async loadPage(page = 1, filters = {}) {
    const params = new URLSearchParams({
      page: page.toString(),
      limit: this.pageSize.toString(),
      ...filters
    });

    const response = await fetch(`${this.apiUrl}?${params}`);
    const data = await response.json();

    this.currentPage = page;
    this.totalItems = data.total || 0;
    this.totalPages = Math.ceil(this.totalItems / this.pageSize);

    return {
      items: data.data || [],
      pagination: {
        currentPage: this.currentPage,
        totalPages: this.totalPages,
        totalItems: this.totalItems,
        hasNext: this.currentPage < this.totalPages,
        hasPrev: this.currentPage > 1
      }
    };
  }

  async nextPage(filters = {}) {
    if (this.currentPage < this.totalPages) {
      return await this.loadPage(this.currentPage + 1, filters);
    }
    return null;
  }

  async prevPage(filters = {}) {
    if (this.currentPage > 1) {
      return await this.loadPage(this.currentPage - 1, filters);
    }
    return null;
  }
}

// Usage
const pagination = new PaginationHelper('/cars');
const result = await pagination.loadPage(1, { source: 'dongchedi' });
```

## Testing Examples

### Unit Test Example (Jest)

```javascript
// cars.test.js
import { fetchCars, submitLead } from './api';

// Mock fetch
global.fetch = jest.fn();

describe('Cars API', () => {
  beforeEach(() => {
    fetch.mockClear();
  });

  test('fetchCars returns data correctly', async () => {
    const mockData = {
      data: [{ id: 1, brand_name: 'BMW' }],
      total: 1
    };

    fetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockData
    });

    const result = await fetchCars({ page: 1 });
    
    expect(fetch).toHaveBeenCalledWith('/cars?page=1');
    expect(result).toEqual(mockData);
  });

  test('submitLead handles errors', async () => {
    fetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: async () => ({ error: 'Invalid data' })
    });

    await expect(submitLead({})).rejects.toThrow('Invalid data');
  });
});
```

### Integration Test Example

```javascript
// integration.test.js
describe('API Integration Tests', () => {
  test('full workflow: get cars, check car, submit lead', async () => {
    // 1. Get cars
    const carsResponse = await fetch('/cars?limit=1');
    const carsData = await carsResponse.json();
    expect(carsData.data).toHaveLength(1);

    const car = carsData.data[0];

    // 2. Check car details
    const checkResponse = await fetch('/checkcar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source: car.source,
        car_id: car.car_id
      })
    });
    expect(checkResponse.ok).toBe(true);

    // 3. Submit lead
    const leadResponse = await fetch('/lead', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        car: car,
        user: 'Test User'
      })
    });
    expect(leadResponse.ok).toBe(true);
  });
});
```

This documentation provides comprehensive examples for integrating with the CarCatch API across different technologies and use cases.
