import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../services/api'
import './Table.css'

function OrdersTab() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [totalPages, setTotalPages] = useState(0)
  const [totalCount, setTotalCount] = useState(0)
  const navigate = useNavigate()

  useEffect(() => {
    let cancelled = false

    const fetchOrders = async () => {
      setLoading(true)
      try {
        const response = await api.get('/orders', {
          params: { page, pageSize }
        })

        if (cancelled) {
          return
        }

        const data = response.data || {}
        setOrders(data.items || [])
        setTotalCount(data.totalCount ?? 0)
        setTotalPages(data.totalPages ?? 0)

        if (typeof data.page === 'number' && data.page !== page) {
          setPage(data.page || 1)
        }

        if (typeof data.pageSize === 'number' && data.pageSize !== pageSize) {
          setPageSize(data.pageSize)
        }

        setError('')
      } catch (err) {
        if (!cancelled) {
          setError('Не удалось загрузить заявки: ' + (err.response?.data?.message || err.message))
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    fetchOrders()

    return () => {
      cancelled = true
    }
  }, [page, pageSize])

  const handlePageSizeChange = (event) => {
    const newSize = Number(event.target.value)
    setPageSize(newSize)
    setPage(1)
  }

  const goToPreviousPage = () => {
    setPage((prev) => Math.max(1, prev - 1))
  }

  const goToNextPage = () => {
    if (totalPages > 0) {
      setPage((prev) => Math.min(totalPages, prev + 1))
    } else if (orders.length === pageSize) {
      setPage((prev) => prev + 1)
    }
  }

  const openCarDetails = (carUuid) => {
    if (!carUuid) return
    navigate(`/cars/${carUuid}`)
  }

  const openTelegramChat = (tgId, chatId, username) => {
    const openForValue = (value) => {
      const normalized = value.toString().trim()
      if (!normalized) {
        return false
      }

      if (/^tg:|^https?:\/\//i.test(normalized)) {
        window.open(normalized, '_blank', 'noopener,noreferrer')
        return true
      }

      if (/^-?\d+$/.test(normalized)) {
        window.open(`tg://user?id=${normalized}`, '_blank', 'noopener,noreferrer')
        return true
      }

      if (/^@?[A-Za-z0-9_]+$/.test(normalized)) {
        const formatted = normalized.replace(/^@/, '')
        window.open(`https://t.me/${formatted}`, '_blank', 'noopener,noreferrer')
        return true
      }

      return false
    }

    if (tgId && openForValue(tgId)) {
      return
    }

    if (chatId) {
      window.open(`tg://user?id=${chatId}`, '_blank', 'noopener,noreferrer')
      return
    }

    if (username) {
      openForValue(username)
    }
  }

  const displayTotalPages = totalPages > 0 ? totalPages : 1
  const isPrevDisabled = loading || page <= 1
  const isNextDisabled =
    loading || (totalPages > 0 ? page >= totalPages : orders.length < pageSize)

  if (loading) {
    return <div className="loading">Загрузка заявок...</div>
  }

  return (
    <div className="table-container">
      <div className="table-header">
        <h2>Заявки</h2>
        <div className="header-actions">
          <span className="table-meta">Всего: {totalCount}</span>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Car UUID</th>
              <th>Telegram</th>
              <th>Создана</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            {orders.length === 0 ? (
              <tr>
                <td colSpan="4" className="no-data">Заявки не найдены</td>
              </tr>
            ) : (
              orders.map((order) => (
                <tr key={order.id}>
                  <td>{order.carUuid}</td>
                  <td>
                    <div className="telegram-info">
                      {order.tgId && (
                        <span className="telegram-primary">{order.tgId}</span>
                      )}
                      {order.clientTelegramId && order.clientTelegramId !== order.tgId && (
                        <span className="telegram-username">{order.clientTelegramId}</span>
                      )}
                      {order.clientChatId && (
                        <span className="telegram-chat-id">Chat ID: {order.clientChatId}</span>
                      )}
                      {!order.tgId && !order.clientTelegramId && !order.clientChatId && '—'}
                    </div>
                  </td>
                  <td>{new Date(order.createdAt).toLocaleString()}</td>
                  <td className="actions-cell">
                    <button
                      type="button"
                      className="btn-outline"
                      onClick={() => openCarDetails(order.carUuid)}
                    >
                      Открыть машину
                    </button>
                    <button
                      type="button"
                      className="btn-primary"
                      onClick={() => openTelegramChat(order.tgId, order.clientChatId, order.clientTelegramId)}
                      disabled={!order.tgId && !order.clientChatId && !order.clientTelegramId}
                    >
                      Написать
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="card-list">
        {orders.length === 0 ? (
          <div className="card-item">
            <div className="card-value">Заявки не найдены</div>
          </div>
        ) : (
          orders.map((order) => (
            <div key={order.id} className="card-item">
              <div className="card-top">
                <div>
                  <div className="card-label">Car UUID</div>
                  <div className="card-value">{order.carUuid}</div>
                </div>
              </div>
              <div className="card-meta">
                <div>
                  <div className="card-label">Telegram</div>
                  <div className="card-value">
                    {order.tgId && <div className="telegram-primary">{order.tgId}</div>}
                    {order.clientTelegramId && order.clientTelegramId !== order.tgId && (
                      <div className="telegram-username">{order.clientTelegramId}</div>
                    )}
                    {order.clientChatId && <div className="telegram-chat-id">ID: {order.clientChatId}</div>}
                    {!order.tgId && !order.clientTelegramId && !order.clientChatId && '—'}
                  </div>
                </div>
                <div>
                  <div className="card-label">Создана</div>
                  <div className="card-value">{new Date(order.createdAt).toLocaleString()}</div>
                </div>
              </div>
              <div className="card-actions">
                <button
                  type="button"
                  className="btn-outline"
                  onClick={() => openCarDetails(order.carUuid)}
                >
                  Открыть машину
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => openTelegramChat(order.tgId, order.clientChatId, order.clientTelegramId)}
                  disabled={!order.tgId && !order.clientChatId && !order.clientTelegramId}
                >
                  Написать
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="table-footer">
        <div className="pagination">
          <button
            className="btn-outline"
            onClick={goToPreviousPage}
            disabled={isPrevDisabled}
          >
            Предыдущая
          </button>
          <span className="pagination-info">
            Страница {Math.min(page, displayTotalPages)} из {displayTotalPages}
          </span>
          <button
            className="btn-outline"
            onClick={goToNextPage}
            disabled={isNextDisabled}
          >
            Следующая
          </button>
        </div>
        <div className="page-size">
          <label htmlFor="orders-page-size">На странице</label>
          <select
            id="orders-page-size"
            value={pageSize}
            onChange={handlePageSizeChange}
            disabled={loading}
          >
            {[10, 20, 50].map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  )
}

export default OrdersTab




