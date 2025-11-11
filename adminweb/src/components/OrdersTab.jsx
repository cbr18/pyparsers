import React, { useEffect, useState } from 'react'
import api from '../services/api'
import './Table.css'

function OrdersTab() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const loadOrders = async () => {
      try {
        setLoading(true)
        const response = await api.get('/orders')
        setOrders(response.data || [])
        setError('')
      } catch (err) {
        setError('Не удалось загрузить заявки: ' + (err.response?.data?.message || err.message))
      } finally {
        setLoading(false)
      }
    }

    loadOrders()
  }, [])

  if (loading) {
    return <div className="loading">Загрузка заявок...</div>
  }

  return (
    <div className="table-container">
      <div className="table-header">
        <h2>Заявки</h2>
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Car UUID</th>
              <th>Telegram клиента</th>
              <th>Telegram ID привязан</th>
              <th>Создана</th>
              <th>Обновлена</th>
            </tr>
          </thead>
          <tbody>
            {orders.length === 0 ? (
              <tr>
                <td colSpan="5" className="no-data">Заявки не найдены</td>
              </tr>
            ) : (
              orders.map((order) => (
                <tr key={order.id}>
                  <td>{order.carUuid}</td>
                  <td>{order.clientTelegramId || '-'}</td>
                  <td>{order.linkedTelegramId || '-'}</td>
                  <td>{new Date(order.createdAt).toLocaleString()}</td>
                  <td>{new Date(order.updatedAt).toLocaleString()}</td>
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
                <div>
                  <div className="card-label">Привязан</div>
                  <div className="card-value">{order.linkedTelegramId || '-'}</div>
                </div>
              </div>
              <div className="card-meta">
                <div>
                  <div className="card-label">Telegram клиента</div>
                  <div className="card-value">{order.clientTelegramId || '-'}</div>
                </div>
                <div>
                  <div className="card-label">Создана</div>
                  <div className="card-value">{new Date(order.createdAt).toLocaleString()}</div>
                </div>
                <div>
                  <div className="card-label">Обновлена</div>
                  <div className="card-value">{new Date(order.updatedAt).toLocaleString()}</div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default OrdersTab




