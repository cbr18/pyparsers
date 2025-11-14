import React, { useState } from 'react'
import { triggerFullParsing, triggerIncrementalParsing } from '../services/api'
import './ParsingTab.css'

const parsingSources = [
  {
    id: 'dongchedi',
    title: 'Dongchedi',
    description: 'Полный каталог и инкрементальные обновления с площадки Dongchedi (懂车帝).'
  },
  {
    id: 'che168',
    title: 'Che168',
    description: 'Обновления объявлений с площадки Che168, включая новые и изменённые позиции.'
  }
]

const initialState = parsingSources.reduce((acc, source) => {
  acc[source.id] = {
    loading: null,
    error: '',
    success: '',
    lastTaskId: '',
    lastType: '',
    lastTriggeredAt: '',
    lastN: ''
  }
  return acc
}, {})

function ParsingTab() {
  const [state, setState] = useState(initialState)

  const handleInputChange = (sourceId, value) => {
    setState((prev) => ({
      ...prev,
      [sourceId]: {
        ...prev[sourceId],
        lastN: value
      }
    }))
  }

  const updateState = (sourceId, updates) => {
    setState((prev) => ({
      ...prev,
      [sourceId]: {
        ...prev[sourceId],
        ...updates
      }
    }))
  }

  const handleFullUpdate = async (sourceId) => {
    updateState(sourceId, {
      loading: 'full',
      error: '',
      success: ''
    })

    try {
      const response = await triggerFullParsing(sourceId)
      updateState(sourceId, {
        loading: null,
        success: response.data?.message || 'Полное обновление запущено',
        error: '',
        lastTaskId: response.data?.taskId || '',
        lastType: 'Полное обновление',
        lastTriggeredAt: new Date().toISOString()
      })
    } catch (err) {
      const message =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.message ||
        'Не удалось запустить полное обновление'

      updateState(sourceId, {
        loading: null,
        error: message,
        success: ''
      })
    }
  }

  const handleIncrementalUpdate = async (sourceId) => {
    const { lastN } = state[sourceId]
    const normalized = lastN.trim()
    const parsed = normalized ? Number(normalized) : undefined

    if (normalized && (!Number.isInteger(parsed) || parsed <= 0)) {
      updateState(sourceId, {
        error: 'Поле "Количество последних записей" должно быть положительным числом',
        success: ''
      })
      return
    }

    updateState(sourceId, {
      loading: 'incremental',
      error: '',
      success: ''
    })

    try {
      const payloadLastN = parsed && parsed > 0 ? parsed : undefined
      const response = await triggerIncrementalParsing(sourceId, payloadLastN)
      updateState(sourceId, {
        loading: null,
        success: response.data?.message || 'Инкрементальное обновление запущено',
        error: '',
        lastTaskId: response.data?.taskId || '',
        lastType: 'Инкрементальное обновление',
        lastTriggeredAt: new Date().toISOString()
      })
    } catch (err) {
      const message =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.message ||
        'Не удалось запустить инкрементальное обновление'

      updateState(sourceId, {
        loading: null,
        error: message,
        success: ''
      })
    }
  }

  return (
    <div className="parsing-tab table-container">
      <div className="parsing-header">
        <div>
          <h2>Парсинг источников</h2>
          <p className="parsing-subtitle">
            Запускайте полное или инкрементальное обновление данных с площадок. После старта
            обновления задача отправляется в DataHub и отрабатывается асинхронно.
          </p>
        </div>
      </div>

      <div className="parsing-grid">
        {parsingSources.map((source) => {
          const sourceState = state[source.id]
          const isFullLoading = sourceState.loading === 'full'
          const isIncrementalLoading = sourceState.loading === 'incremental'

          return (
            <div className="parsing-card" key={source.id}>
              <div className="parsing-card-header">
                <div>
                  <h3>{source.title}</h3>
                  <p>{source.description}</p>
                </div>
                <span className="parsing-tag">{source.id}</span>
              </div>

              <div className="parsing-actions">
                <button
                  className="btn-primary"
                  onClick={() => handleFullUpdate(source.id)}
                  disabled={isFullLoading || isIncrementalLoading}
                >
                  {isFullLoading ? 'Запуск...' : 'Полное обновление'}
                </button>

                <div className="parsing-inline-form">
                  <label htmlFor={`lastN-${source.id}`}>Количество последних записей</label>
                  <input
                    id={`lastN-${source.id}`}
                    type="number"
                    min="1"
                    placeholder="по умолчанию авто"
                    value={sourceState.lastN}
                    onChange={(event) => handleInputChange(source.id, event.target.value)}
                  />
                </div>

                <button
                  className="btn-outline"
                  onClick={() => handleIncrementalUpdate(source.id)}
                  disabled={isFullLoading || isIncrementalLoading}
                >
                  {isIncrementalLoading ? 'Запуск...' : 'Инкрементальное обновление'}
                </button>
              </div>

              {sourceState.error && <div className="error-message">{sourceState.error}</div>}
              {sourceState.success && <div className="info-message">{sourceState.success}</div>}

              {(sourceState.lastTaskId || sourceState.lastTriggeredAt) && (
                <div className="parsing-meta">
                  <div>
                    <span className="parsing-meta-label">Последний запуск:</span>
                    <span className="parsing-meta-value">
                      {sourceState.lastTriggeredAt
                        ? new Date(sourceState.lastTriggeredAt).toLocaleString()
                        : '—'}
                    </span>
                  </div>
                  <div>
                    <span className="parsing-meta-label">Тип запуска:</span>
                    <span className="parsing-meta-value">
                      {sourceState.lastType || '—'}
                    </span>
                  </div>
                  <div>
                    <span className="parsing-meta-label">ID задачи:</span>
                    <span className="parsing-meta-value parsing-task-id">
                      {sourceState.lastTaskId || '—'}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default ParsingTab

