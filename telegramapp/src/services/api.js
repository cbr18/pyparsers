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

    // Add filters if they exist
    if (filters.source) params.append('source', filters.source);
    if (filters.brand) params.append('brand', filters.brand);
    if (filters.city) params.append('city', filters.city);
    if (filters.year) params.append('year', filters.year);
    if (filters.search) params.append('search', filters.search);

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

/**
 * Send a lead request to the CBR18 admin bot
 * @param {object} car - Car object
 * @param {string} user - Optional user info
 * @returns {Promise}
 */
export const sendLeadRequest = async (car, user = '') => {
  try {
    const response = await fetch('/admin-lead', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ car, user })
    });
    if (!response.ok) {
      throw new Error(`HTTP error! Status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error('Error sending lead:', error);
    throw error;
  }
};
