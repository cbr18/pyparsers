import React from 'react';

const Pagination = ({ page, limit, total, handlePageChange }) => {
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="pagination">
      <button
        onClick={() => handlePageChange(1)}
        disabled={page === 1}
      >
        &laquo;
      </button>

      <button
        onClick={() => handlePageChange(page - 1)}
        disabled={page === 1}
      >
        &lsaquo;
      </button>

      <span className="page-info">
        Страница {page} из {totalPages}
      </span>

      <button
        onClick={() => handlePageChange(page + 1)}
        disabled={page >= totalPages}
      >
        &rsaquo;
      </button>

      <button
        onClick={() => handlePageChange(totalPages)}
        disabled={page >= totalPages}
      >
        &raquo;
      </button>

      <span className="total-info">
        Всего: {total} автомобилей
      </span>
    </div>
  );
};

export default Pagination;
