import React, { useState } from 'react';

const Filters = ({ tempFilters, setTempFilters, applyFilters, resetFilters, sources, brands }) => {
  const [showAdvanced, setShowAdvanced] = useState(false);

  return (
    <div className="filters-panel">
      {/* Базовые фильтры */}
      <div className="filter-group">
        <label>Бренд:</label>
        <input
          type="text"
          list="brand-options"
          value={tempFilters.brand || ''}
          onChange={(e) => setTempFilters({ ...tempFilters, brand: e.target.value })}
          placeholder="Начните вводить бренд"
        />
        <datalist id="brand-options">
          <option value="">Все бренды</option>
          {brands && brands.length > 0 && brands.map((brand, index) => {
            const label = brand.name || brand.orig_name || '';
            const key = brand.id || label || index;
            return label ? <option key={key} value={label} /> : null;
          })}
        </datalist>
      </div>

      <div className="filter-group">
        <label>Год от:</label>
        <input
          type="text"
          value={tempFilters.yearFrom}
          onChange={(e) => setTempFilters({...tempFilters, yearFrom: e.target.value})}
          placeholder="От"
        />
      </div>

      <div className="filter-group">
        <label>Год до:</label>
        <input
          type="text"
          value={tempFilters.yearTo}
          onChange={(e) => setTempFilters({...tempFilters, yearTo: e.target.value})}
          placeholder="До"
        />
      </div>

      <div className="filter-group">
        <label>Цена от (₽):</label>
        <input
          type="text"
          value={tempFilters.priceFrom}
          onChange={(e) => setTempFilters({...tempFilters, priceFrom: e.target.value})}
          placeholder="Минимальная цена"
        />
      </div>

      <div className="filter-group">
        <label>Цена до (₽):</label>
        <input
          type="text"
          value={tempFilters.priceTo}
          onChange={(e) => setTempFilters({...tempFilters, priceTo: e.target.value})}
          placeholder="Максимальная цена"
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

      {/* Сортировка */}
      <div className="filter-group">
        <label>Сортировка:</label>
        <select
          value={tempFilters.sortBy || ''}
          onChange={(e) => {
            const value = e.target.value;
            let sortBy = '';
            let sortOrder = '';
            if (value === 'price_asc') {
              sortBy = 'price';
              sortOrder = 'asc';
            } else if (value === 'price_desc') {
              sortBy = 'price';
              sortOrder = 'desc';
            } else if (value === 'year_desc') {
              sortBy = 'year';
              sortOrder = 'desc';
            }
            setTempFilters({
              ...tempFilters,
              sortBy,
              sortOrder
            });
          }}
        >
          <option value="">По умолчанию</option>
          <option value="price_asc">Сначала дешевле</option>
          <option value="price_desc">Сначала дороже</option>
          <option value="year_desc">Сначала новее</option>
        </select>
      </div>

      {/* Расширенные фильтры */}
      <div className="filter-group">
        <button
          type="button"
          className="advanced-toggle"
          onClick={() => setShowAdvanced(!showAdvanced)}
        >
          {showAdvanced ? 'Скрыть расширенные' : 'Показать расширенные'}
        </button>
      </div>

      {showAdvanced && (
        <div className="advanced-filters">
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
        </div>
      )}

      <div className="filter-actions">
        <button onClick={applyFilters}>Применить</button>
        <button onClick={resetFilters}>Сбросить</button>
      </div>
    </div>
  );
};

export default Filters;
