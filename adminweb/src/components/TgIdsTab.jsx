import React, { useState, useEffect } from 'react'
import api, { applyTelegramIdsToBot } from '../services/api'
import './Table.css'

function TgIdsTab() {
  const [tgIds, setTgIds] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [infoMessage, setInfoMessage] = useState('')
  const [syncing, setSyncing] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [formData, setFormData] = useState({ telegramId: '', chatId: '', isActive: true })

  useEffect(() => {
    loadTgIds()
  }, [])

  const loadTgIds = async () => {
    try {
      setLoading(true)
      const response = await api.get('/tgid')
      setTgIds(response.data)
      setError('')
    } catch (err) {
      setError('Не удалось загрузить Telegram ID: ' + (err.response?.data?.message || err.message))
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setInfoMessage('')
    const isEdit = Boolean(editingId)

    try {
      const payload = {
        telegramId: formData.telegramId,
        isActive: formData.isActive,
        chatId: null
      }

      const trimmedChatId = formData.chatId.trim()
      if (trimmedChatId) {
        const normalizedChatId = trimmedChatId.replace(/\s+/g, '')
        if (!/^[-]?\d+$/.test(normalizedChatId)) {
          setError('Chat ID должен содержать только цифры (может начинаться с - для чатов)')
          return
        }
        payload.chatId = Number(normalizedChatId)
      }

      if (isEdit) {
        await api.put(`/tgid/${editingId}`, payload)
      } else {
        await api.post('/tgid', payload)
      }

      await loadTgIds()
      setShowForm(false)
      setEditingId(null)
      setFormData({ telegramId: '', chatId: '', isActive: true })
      setInfoMessage(isEdit ? 'Telegram ID обновлён' : 'Telegram ID добавлен')
    } catch (err) {
      setError('Не удалось сохранить Telegram ID: ' + (err.response?.data?.message || err.message))
    }
  }

  const handleEdit = (tgId) => {
    setEditingId(tgId.id)
    setFormData({
      telegramId: tgId.telegramId,
      chatId: tgId.chatId !== null && tgId.chatId !== undefined ? String(tgId.chatId) : '',
      isActive: tgId.isActive
    })
    setShowForm(true)
    setError('')
    setInfoMessage('')
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Удалить этот Telegram ID?')) {
      return
    }

    try {
      await api.delete(`/tgid/${id}`)
      setInfoMessage('Telegram ID удалён')
      await loadTgIds()
    } catch (err) {
      setError('Не удалось удалить Telegram ID: ' + (err.response?.data?.message || err.message))
    }
  }

  const handleCancel = () => {
    setShowForm(false)
    setEditingId(null)
    setFormData({ telegramId: '', chatId: '', isActive: true })
    setError('')
  }

  const handleApplyToBot = async () => {
    setError('')
    setInfoMessage('')
    setSyncing(true)

    try {
      const response = await applyTelegramIdsToBot()
      const synced = response.data?.synced ?? response.data?.total ?? null
      if (synced !== null && synced !== undefined) {
        setInfoMessage(`Telegram ID синхронизированы с ботом (всего ${synced})`)
      } else {
        setInfoMessage('Telegram ID отправлены в бот')
      }
    } catch (err) {
      setError('Не удалось применить Telegram ID в боте: ' + (err.response?.data?.message || err.message))
    } finally {
      setSyncing(false)
    }
  }

  if (loading) {
    return <div className="loading">Загрузка Telegram ID...</div>
  }

  return (
    <div className="table-container">
      <div className="table-header">
        <h2>Telegram IDs</h2>
        <div className="header-actions">
          <button 
            className="btn-primary" 
            onClick={() => {
              setShowForm(true)
              setError('')
              setInfoMessage('')
            }}
            disabled={showForm}
          >
            Добавить Telegram ID
          </button>
          <button
            className="btn-outline"
            onClick={handleApplyToBot}
            disabled={syncing}
          >
            {syncing ? 'Применение...' : 'Применить в боте'}
          </button>
        </div>
      </div>

      {error && <div className="error-message">{error}</div>}
      {infoMessage && <div className="info-message">{infoMessage}</div>}

      {showForm && (
        <div className="form-modal" onClick={handleCancel}>
          <div className="form-box" onClick={(event) => event.stopPropagation()}>
            <h3>{editingId ? 'Редактирование Telegram ID' : 'Добавление Telegram ID'}</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label htmlFor="telegramId">Telegram ID</label>
                <input
                  type="text"
                  id="telegramId"
                  value={formData.telegramId}
                  onChange={(e) => setFormData({ ...formData, telegramId: e.target.value })}
                  required
                  placeholder="e.g., 123456789"
                />
              </div>
              <div className="form-group">
                <label htmlFor="chatId">Chat ID (опционально, числовой)</label>
                <input
                  type="text"
                  id="chatId"
                  value={formData.chatId}
                  onChange={(e) => setFormData({ ...formData, chatId: e.target.value })}
                  placeholder="Например, 123456789 или -1001234567890"
                />
              </div>
              <div className="form-group">
                <label>
                  <input
                    type="checkbox"
                    checked={formData.isActive}
                    onChange={(e) => setFormData({ ...formData, isActive: e.target.checked })}
                  />
                  Активен
                </label>
              </div>
              <div className="form-actions">
                <button type="submit" className="btn-primary">
                  {editingId ? 'Обновить' : 'Создать'}
                </button>
                <button type="button" onClick={handleCancel} className="btn-secondary">
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
              <th>Telegram ID</th>
              <th>Chat ID</th>
              <th>Статус</th>
              <th>Создан</th>
              <th>Обновлён</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            {tgIds.length === 0 ? (
              <tr>
                <td colSpan="5" className="no-data">Telegram ID не найдены</td>
              </tr>
            ) : (
              tgIds.map((tgId) => (
                <tr key={tgId.id}>
                  <td>{tgId.telegramId}</td>
                  <td>{tgId.chatId ?? '-'}</td>
                  <td>
                    <span className={`status ${tgId.isActive ? 'active' : 'inactive'}`}>
                      {tgId.isActive ? 'Активен' : 'Отключён'}
                    </span>
                  </td>
                  <td>{new Date(tgId.createdAt).toLocaleString()}</td>
                  <td>{new Date(tgId.updatedAt).toLocaleString()}</td>
                  <td>
                    <button 
                      onClick={() => handleEdit(tgId)} 
                      className="btn-edit"
                      title="Редактировать"
                    >
                      Редактировать
                    </button>
                    <button 
                      onClick={() => handleDelete(tgId.id)} 
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
        {tgIds.length === 0 ? (
          <div className="card-item">
            <div className="card-value">Telegram ID не найдены</div>
          </div>
        ) : (
          tgIds.map((tgId) => (
            <div key={tgId.id} className="card-item">
              <div className="card-top">
                <div>
                  <div className="card-label">Telegram ID</div>
                  <div className="card-value">{tgId.telegramId}</div>
                </div>
                <div>
                  <div className="card-label">Статус</div>
                  <span className={`status ${tgId.isActive ? 'active' : 'inactive'}`}>
                    {tgId.isActive ? 'Активен' : 'Отключён'}
                  </span>
                </div>
              </div>
              <div className="card-meta">
                <div>
                  <div className="card-label">Chat ID</div>
                  <div className="card-value">{tgId.chatId ?? '-'}</div>
                </div>
                <div>
                  <div className="card-label">Создан</div>
                  <div className="card-value">{new Date(tgId.createdAt).toLocaleString()}</div>
                </div>
                <div>
                  <div className="card-label">Обновлён</div>
                  <div className="card-value">{new Date(tgId.updatedAt).toLocaleString()}</div>
                </div>
              </div>
              <div className="card-actions">
                <button
                  onClick={() => handleEdit(tgId)}
                  className="btn-edit"
                  title="Редактировать"
                >
                  Редактировать
                </button>
                <button
                  onClick={() => handleDelete(tgId.id)}
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

export default TgIdsTab







