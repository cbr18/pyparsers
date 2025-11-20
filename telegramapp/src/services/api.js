// API service for datahub

const API_URL = '/api/cars';

/**
 * Fetch cars with pagination and filters
 * @param {number} page - Current page number
 * @param {number} limit - Number of items per page
 * @param {object} filters - Filter parameters
 * @returns {Promise} - Promise with cars data and total count
 */
export const fetchCars = async (page = 1, limit = 10, filters = {}) => {
  try {
    // Build query parameters
    const params = new URLSearchParams({
      page,
      limit
    });

    // Add filters if they exist (пустые значения не отправляем)
    if (filters.source) params.append('source', filters.source);
    if (filters.brand) params.append('brand', filters.brand);
    if (filters.search) params.append('search', filters.search);

    // Диапазоны по году
    if (filters.yearFrom) params.append('year_from', filters.yearFrom);
    if (filters.yearTo) params.append('year_to', filters.yearTo);

    // Диапазоны по цене (в рублях)
    if (filters.priceFrom) params.append('price_from', filters.priceFrom);
    if (filters.priceTo) params.append('price_to', filters.priceTo);

    // Сортировка
    if (filters.sortBy) params.append('sort_by', filters.sortBy);
    if (filters.sortOrder) params.append('sort_order', filters.sortOrder);

    const response = await fetch(`${API_URL}?${params.toString()}`);

    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error fetching cars:', error);
    throw error;
  }
};

/**
 * Fetch a single car by UUID
 * @param {string} uuid - Car UUID
 * @returns {Promise} - Promise with car data
 */
export const fetchCarByUUID = async (uuid) => {
  try {
    const response = await fetch(`/api/cars/uuid/${uuid}`);
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching car:', error);
    throw error;
  }
};

/**
 * Fetch brands from backend
 * @returns {Promise} - Promise with brands data
 */
export const fetchBrands = async () => {
  try {
    const response = await fetch('/api/brands');
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error fetching brands:', error);
    throw error;
  }
};

export const createOrder = async ({
  carUuid,
  clientTelegramId = '',
  clientChatId = null,
  car = null,
  tgId = ''
}) => {
  try {
    const response = await fetch('/api/admin-service/orders', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        carUuid,
        clientTelegramId,
        clientChatId,
        tgId,
        car
      })
    })

    return response
  } catch (error) {
    console.error('Error creating order:', error)
    throw error
  }
}
