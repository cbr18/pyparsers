import React, { useState, useEffect, useMemo } from 'react'
import api from '../services/api'
import './Table.css'

const initialFormState = {
  login: '',
  password: '',
  tgIdId: ''
}

function UsersTab() {
  const [users, setUsers] = useState([])
  const [tgIds, setTgIds] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [formData, setFormData] = useState(initialFormState)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    const init = async () => {
      setLoading(true)
      try {
        await Promise.all([loadUsers(), loadTgIds()])
      } finally {
        setLoading(false)
      }
    }

    init()
  }, [])

  const loadUsers = async () => {
    try {
      const response = await api.get('/users')
      setUsers(response.data)
      setError('')
    } catch (err) {
      setError('Не удалось загрузить пользователей: ' + (err.response?.data?.message || err.message))
    }
  }

  const loadTgIds = async () => {
    try {
      const response = await api.get('/tgid')
      setTgIds(response.data)
    } catch (err) {
      setError('Не удалось загрузить Telegram ID: ' + (err.response?.data?.message || err.message))
    }
  }

  const tgIdMap = useMemo(() => {
    const map = {}
    tgIds.forEach((item) => {
      map[item.id] = item.telegramId
    })
    return map
  }, [tgIds])

  const handleOpenCreate = () => {
    setEditingUser(null)
    setFormData(initialFormState)
    setShowForm(true)
    setError('')
  }

  const handleOpenEdit = (user) => {
    setEditingUser(user)
    setFormData({
      login: user.login,
      password: '',
      tgIdId: user.tgIdId || ''
    })
    setShowForm(true)
    setError('')
  }

  const handleDelete = async (user) => {
    if (!window.confirm(`Удалить пользователя \"${user.login}\"?`)) {
      return
    }

    try {
      await api.delete(`/users/${user.id}`)
      await loadUsers()
    } catch (err) {
      setError('Не удалось удалить пользователя: ' + (err.response?.data?.message || err.message))
    }
  }

  const handleCancel = () => {
    setShowForm(false)
    setEditingUser(null)
    setFormData(initialFormState)
    setSubmitting(false)
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')

    const trimmedLogin = formData.login.trim()
    if (!trimmedLogin) {
      setError('Логин обязателен')
      return
    }

    if (!editingUser && formData.password.length < 6) {
      setError('Пароль должен содержать не менее 6 символов')
      return
    }

    if (editingUser && formData.password && formData.password.length < 6) {
      setError('Пароль должен содержать не менее 6 символов')
      return
    }

    const selectedTgId = formData.tgIdId
    setSubmitting(true)

    try {
      if (editingUser) {
        const payload = {}

        if (trimmedLogin && trimmedLogin !== editingUser.login) {
          payload.login = trimmedLogin
        }

        if (formData.password) {
          payload.password = formData.password
        }

        const currentTgId = editingUser.tgIdId || ''
        if (selectedTgId === '') {
          if (currentTgId) {
            payload.clearTgId = true
          }
        } else if (selectedTgId !== currentTgId) {
          payload.tgIdId = selectedTgId
        }

        if (Object.keys(payload).length === 0) {
          setError('Нет изменений для сохранения')
          setSubmitting(false)
          return
        }

        await api.put(`/users/${editingUser.id}`, payload)
      } else {
        const payload = {
          login: trimmedLogin,
          password: formData.password
        }

        if (selectedTgId) {
          payload.tgIdId = selectedTgId
        }

        await api.post('/users', payload)
      }

      await loadUsers()
      setShowForm(false)
      setEditingUser(null)
      setFormData(initialFormState)
    } catch (err) {
      setError('Не удалось сохранить пользователя: ' + (err.response?.data?.message || err.message))
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return <div className="loading">Загрузка пользователей...</div>
  }

  return (
    <div className="table-container">
      <div className="table-header">
        <h2>Пользователи</h2>
        <button
          className="btn-primary"
          onClick={handleOpenCreate}
          disabled={showForm}
        >
          Добавить пользователя
        </button>
      </div>

      {error && <div className="error-message">{error}</div>}

      {showForm && (
        <div className="form-modal" onClick={handleCancel}>
          <div className="form-box" onClick={(event) => event.stopPropagation()}>
            <h3>{editingUser ? 'Редактирование пользователя' : 'Создание пользователя'}</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="login">Логин</label>
                <input
                  id="login"
                  type="text"
                  value={formData.login}
                  onChange={(e) => setFormData({ ...formData, login: e.target.value })}
                  required
                  placeholder="admin"
                />
              </div>

              <div className="form-group">
                <label htmlFor="password">Пароль {editingUser && ' (оставьте пустым, чтобы не менять)'}</label>
                <input
                  id="password"
                  type="password"
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  placeholder={editingUser ? '********' : 'Не менее 6 символов'}
                  minLength={editingUser ? undefined : 6}
                />
              </div>

              <div className="form-group">
                <label htmlFor="tgId">Telegram ID (опционально)</label>
                <select
                  id="tgId"
                  value={formData.tgIdId}
                  onChange={(e) => setFormData({ ...formData, tgIdId: e.target.value })}
                >
                  <option value="">Без привязки</option>
                  {tgIds.map((tg) => (
                    <option key={tg.id} value={tg.id}>
                      {tg.telegramId}{tg.isActive ? '' : ' (неактивен)'}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-actions">
                <button type="submit" className="btn-primary" disabled={submitting}>
                  {submitting ? 'Сохранение...' : editingUser ? 'Сохранить' : 'Создать'}
                </button>
                <button type="button" className="btn-secondary" onClick={handleCancel} disabled={submitting}>
                  Отмена
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="table-scroll">
        <table className="data-table">
          <thead>
            <tr>
              <th>Логин</th>
              <th>Telegram ID</th>
              <th>Создан</th>
              <th>Обновлён</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 ? (
              <tr>
                <td colSpan="5" className="no-data">Пользователи не найдены</td>
              </tr>
            ) : (
              users.map((user) => (
                <tr key={user.id}>
                  <td>{user.login}</td>
                  <td>{user.tgIdId ? (tgIdMap[user.tgIdId] || user.tgIdId) : '-'}</td>
                  <td>{new Date(user.createdAt).toLocaleString()}</td>
                  <td>{new Date(user.updatedAt).toLocaleString()}</td>
                  <td>
                    <button
                      onClick={() => handleOpenEdit(user)}
                      className="btn-edit"
                      title="Редактировать"
                    >
                      Редактировать
                    </button>
                    <button
                      onClick={() => handleDelete(user)}
                      className="btn-delete"
                      title="Удалить"
                    >
                      Удалить
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="card-list">
        {users.length === 0 ? (
          <div className="card-item">
            <div className="card-value">Пользователи не найдены</div>
          </div>
        ) : (
          users.map((user) => (
            <div key={user.id} className="card-item">
              <div className="card-top">
                <div>
                  <div className="card-label">Логин</div>
                  <div className="card-value">{user.login}</div>
                </div>
                <div>
                  <div className="card-label">Telegram ID</div>
                  <div className="card-value">
                    {user.tgIdId ? (tgIdMap[user.tgIdId] || user.tgIdId) : '-'}
                  </div>
                </div>
              </div>
              <div className="card-meta">
                <div>
                  <div className="card-label">Создан</div>
                  <div className="card-value">{new Date(user.createdAt).toLocaleString()}</div>
                </div>
                <div>
                  <div className="card-label">Обновлён</div>
                  <div className="card-value">{new Date(user.updatedAt).toLocaleString()}</div>
                </div>
              </div>
              <div className="card-actions">
                <button
                  onClick={() => handleOpenEdit(user)}
                  className="btn-edit"
                  title="Редактировать"
                >
                  Редактировать
                </button>
                <button
                  onClick={() => handleDelete(user)}
                  className="btn-delete"
                  title="Удалить"
                >
                  Удалить
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default UsersTab


