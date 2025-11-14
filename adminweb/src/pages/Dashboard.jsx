import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import UsersTab from '../components/UsersTab'
import TgIdsTab from '../components/TgIdsTab'
import OrdersTab from '../components/OrdersTab'
import ParsingTab from '../components/ParsingTab'
import './Dashboard.css'

function Dashboard() {
  const { user, logout } = useAuth()
  const [activeTab, setActiveTab] = useState('orders')
  const navigate = useNavigate()

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <h1>Admin Panel</h1>
          <div className="header-actions">
            <button
              onClick={() => navigate('/cars')}
              className="btn-outline"
            >
              Найти машину по UUID
            </button>
            <span className="user-info">Welcome, {user?.login || user?.Login || 'User'}</span>
            <button onClick={logout} className="btn-logout">Logout</button>
          </div>
        </div>
      </header>
      
      <div className="dashboard-content">
        <div className="tabs">
          <button
            className={`tab ${activeTab === 'orders' ? 'active' : ''}`}
            onClick={() => setActiveTab('orders')}
          >
            Заявки
          </button>
          <button
            className={`tab ${activeTab === 'tgids' ? 'active' : ''}`}
            onClick={() => setActiveTab('tgids')}
          >
            Telegram IDs
          </button>
          <button
            className={`tab ${activeTab === 'users' ? 'active' : ''}`}
            onClick={() => setActiveTab('users')}
          >
            Users
          </button>
          <button
            className={`tab ${activeTab === 'parsing' ? 'active' : ''}`}
            onClick={() => setActiveTab('parsing')}
          >
            Парсинг
          </button>
        </div>

        <div className="tab-content">
          {activeTab === 'orders' && <OrdersTab />}
          {activeTab === 'tgids' && <TgIdsTab />}
          {activeTab === 'users' && <UsersTab />}
          {activeTab === 'parsing' && <ParsingTab />}
        </div>
      </div>
    </div>
  )
}

export default Dashboard







