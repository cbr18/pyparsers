import React from 'react';

const Filters = ({ tempFilters, setTempFilters, applyFilters, resetFilters, sources }) => {
  return (
    <div className="filters-panel">
      <div className="filter-group">
        <label>Источник:</label>
        <select
          value={tempFilters.source}
          onChange={(e) => setTempFilters({...tempFilters, source: e.target.value})}
        >
          <option value="">Все источники</option>
          {sources.map(source => (
            <option key={source} value={source}>{source}</option>
          ))}
        </select>
      </div>

      <div className="filter-group">
        <label>Бренд:</label>
        <input
          type="text"
          value={tempFilters.brand}
          onChange={(e) => setTempFilters({...tempFilters, brand: e.target.value})}
          placeholder="Введите бренд"
        />
      </div>

      <div className="filter-group">
        <label>Город:</label>
        <input
          type="text"
          value={tempFilters.city}
          onChange={(e) => setTempFilters({...tempFilters, city: e.target.value})}
          placeholder="Введите город"
        />
      </div>

      <div className="filter-group">
        <label>Год:</label>
        <input
          type="text"
          value={tempFilters.year}
          onChange={(e) => setTempFilters({...tempFilters, year: e.target.value})}
          placeholder="Введите год"
        />
      </div>

      <div className="filter-group">
        <label>Поиск:</label>
        <input
          type="text"
          value={tempFilters.search}
          onChange={(e) => setTempFilters({...tempFilters, search: e.target.value})}
          placeholder="Поиск по названию"
        />
      </div>

      <div className="filter-actions">
        <button onClick={applyFilters}>Применить</button>
        <button onClick={resetFilters}>Сбросить</button>
      </div>
    </div>
  );
};

export default Filters;
