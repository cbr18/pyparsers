import React, { useEffect, useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import './App.css';
import brandLogo from './assets/logo192.png';
import CarCard from './components/CarCard';
import CarDetails from './components/CarDetails';
import CarFullDetails from './components/CarFullDetails';
import Filters from './components/Filters';
import Pagination from './components/Pagination';
import Footer from './components/Footer';
import { fetchCars, fetchBrands } from './services/api';

function App() {
  const [cars, setCars] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(10);
  const [total, setTotal] = useState(0);
  const [filters, setFilters] = useState({
    source: '',
    brand: '',
    // Диапазоны по году и цене и общий поиск
    yearFrom: '',
    yearTo: '',
    priceFrom: '',
    priceTo: '',
    search: '',
    // Сортировка
    sortBy: '',
    sortOrder: ''
  });
  const [showFilters, setShowFilters] = useState(false);
  const [tempFilters, setTempFilters] = useState({
    source: '',
    brand: '',
    yearFrom: '',
    yearTo: '',
    priceFrom: '',
    priceTo: '',
    search: '',
    sortBy: '',
    sortOrder: ''
  });
  const [brands, setBrands] = useState([]);

  // Sources for dropdown
  const sources = ['dongchedi', 'che168'];

  // Load cars data
  const loadCars = async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await fetchCars(page, limit, filters);
      setCars(data.data || []);
      setTotal(data.total || 0);
    } catch (err) {
      setError(`Ошибка загрузки данных: ${err.message}`);
      console.error('Error loading cars:', err);
    } finally {
      setLoading(false);
    }
  };

  // Apply filters and reset to page 1
  const applyFilters = () => {
    setFilters(tempFilters);
    setPage(1);
    setShowFilters(false);
  };

  // Reset filters
  const resetFilters = () => {
    const emptyFilters = {
      source: '',
      brand: '',
      yearFrom: '',
      yearTo: '',
      priceFrom: '',
      priceTo: '',
      search: '',
      sortBy: '',
      sortOrder: ''
    };
    setTempFilters(emptyFilters);
    setFilters(emptyFilters);
    setPage(1);
  };

  // Handle pagination
  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= Math.ceil(total / limit)) {
      setPage(newPage);
    }
  };

  // Fetch cars when page, limit, or filters change
  useEffect(() => {
    loadCars();
  }, [page, limit, filters]);

  // Load brands data
  useEffect(() => {
    const loadBrands = async () => {
      try {
        const data = await fetchBrands();
        setBrands(data.data || []);
      } catch (err) {
        console.error('Error loading brands:', err);
      }
    };
    loadBrands();
  }, []);

  // Set up global error handlers
  useEffect(() => {
    window.onerror = function (message, source, lineno, colno, error) {
      console.error('JS Error:', message);
    };
    window.onunhandledrejection = function (e) {
      console.error('Promise Error:', e.reason);
    };
  }, []);

  return (
    <div className="app-root">
      <main className="app-main">
        <Routes>
          <Route path="/car/:uuid" element={<CarDetails />} />
          <Route path="/car/:uuid/full" element={<CarFullDetails />} />
          <Route
            path="/"
            element={
              <div className="app-container">
                <header className="app-header">
                  <div className="header-brand">
                    <div className="brand-logo-wrap">
                      <img src={brandLogo} alt="CarCatch" className="brand-logo" />
                    </div>
                    <div className="brand-text">
                      <h1>Автомобили</h1>
                      <p className="brand-subtitle">подбор от CarCatch</p>
                    </div>
                  </div>
                  <div className="header-actions">
                    <button
                      className="filter-button"
                      onClick={() => {
                        setTempFilters({ ...filters });
                        setShowFilters(!showFilters);
                      }}
                    >
                      {showFilters ? 'Скрыть фильтры' : 'Показать фильтры'}
                    </button>
                    <select
                      className="limit-select"
                      value={limit}
                      onChange={(e) => {
                        setLimit(Number(e.target.value));
                        setPage(1);
                      }}
                    >
                      <option value={5}>5 на странице</option>
                      <option value={10}>10 на странице</option>
                      <option value={20}>20 на странице</option>
                      <option value={50}>50 на странице</option>
                    </select>
                  </div>
                </header>

                {/* Filters panel */}
                {showFilters && (
                  <Filters
                    tempFilters={tempFilters}
                    setTempFilters={setTempFilters}
                    applyFilters={applyFilters}
                    resetFilters={resetFilters}
                    sources={sources}
                    brands={brands}
                  />
                )}

                {/* Error message */}
                {error && <div className="error-message">{error}</div>}

                {/* Loading indicator */}
                {loading ? (
                  <div className="loader-container">
                    <div className="loader">Загрузка автомобилей...</div>
                  </div>
                ) : (
                  <>
                    {/* Car list */}
                    {cars.length > 0 ? (
                      <div className="car-list">
                        {cars.map((car) => (
                          <CarCard key={car.uuid || car.id} car={car} />
                        ))}
                      </div>
                    ) : (
                      <div className="no-results">Нет доступных автомобилей</div>
                    )}

                    {/* Pagination */}
                    {total > 0 && (
                      <Pagination
                        page={page}
                        limit={limit}
                        total={total}
                        handlePageChange={handlePageChange}
                      />
                    )}
                  </>
                )}
              </div>
            }
          />
        </Routes>
      </main>
      <Footer />
    </div>
  );
}

export default App;
