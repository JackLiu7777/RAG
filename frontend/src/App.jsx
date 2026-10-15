import React, { useState, useRef, useEffect } from 'react'

export default function App() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [files, setFiles] = useState([])
  const [sessions, setSessions] = useState([])
  const [currentSession, setCurrentSession] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showDebug, setShowDebug] = useState(false)
  const [lastDebug, setLastDebug] = useState(null)
  const [ctxMenu, setCtxMenu] = useState(null) // {x, y, sid}
  const fileRef = useRef()

  // 初始化：加载会话列表
  useEffect(() => {
    refreshSessions()
  }, [])

  const refreshSessions = () => {
    fetch('/api/sessions').then(r => r.json()).then(setSessions).catch(() => {})
    fetch('/api/files').then(r => r.json()).then(setFiles).catch(() => {})
  }

  const newSession = async () => {
    const res = await fetch('/api/sessions', { method: 'POST' })
    const data = await res.json()
    refreshSessions()
    selectSession(data.session_id)
  }

  const selectSession = async (sid) => {
    setCurrentSession(sid)
    const res = await fetch(`/api/sessions/${sid}/messages`)
    const msgs = await res.json()
    setMessages(msgs.map(m => ({ ...m, contexts: [], text: m.text })))
    setLastDebug(null)
  }

  const deleteSession = async (sid) => {
    if (!confirm('删除这个对话？')) return
    await fetch(`/api/sessions/${sid}`, { method: 'DELETE' })
    refreshSessions()
    if (currentSession === sid) {
      setCurrentSession(null)
      setMessages([])
    }
  }

  const renameSession = async (sid, oldTitle) => {
    const newTitle = prompt('重命名对话：', oldTitle)
    if (newTitle && newTitle.trim() && newTitle !== oldTitle) {
      await fetch(`/api/sessions/${sid}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle.trim() }),
      })
      refreshSessions()
    }
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setError('')
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await fetch('/api/upload', { method: 'POST', body: fd })
      if (!res.ok) throw new Error('上传失败')
      const data = await res.json()
      alert(`上传成功：${data.chunks} 个文本块`)
      fetch('/api/files').then(r => r.json()).then(setFiles)
    } catch (e) {
      setError(e.message)
    } finally {
      setUploading(false)
      setFile(null)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const handleDeleteFile = async (docId) => {
    if (!confirm('确定删除？')) return
    await fetch(`/api/files/${docId}`, { method: 'DELETE' })
    fetch('/api/files').then(r => r.json()).then(setFiles)
  }

  const send = async () => {
    if (!input.trim() || loading) return
    if (!currentSession) {
      setError('请先新建一个对话')
      return
    }
    const q = input.trim()
    setInput('')
    setError('')
    setLastDebug(null)
    setMessages(m => [...m, { role: 'user', text: q }, { role: 'ai', text: '', contexts: [] }])
    setLoading(true)

    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, session_id: currentSession }),
      })
      if (!res.ok) throw new Error('请求失败')

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop()
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const evt = JSON.parse(line.slice(6))
            setMessages(prev => {
              const next = [...prev]
              const last = { ...next[next.length - 1] }
              if (evt.type === 'contexts') {
                last.contexts = evt.data || []
              } else if (evt.type === 'debug') {
                setLastDebug(evt.data)
              } else if (evt.type === 'text') {
                last.text += evt.data
              } else if (evt.type === 'done') {
                setLoading(false)
              }
              next[next.length - 1] = last
              return next
            })
          } catch (e) {}
        }
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ display: 'flex', height: '100vh' }} onClick={() => setCtxMenu(null)}>
      {/* 右键菜单 */}
      {ctxMenu && (
        <div style={{
          position: 'fixed', left: ctxMenu.x, top: ctxMenu.y, zIndex: 100,
          background: '#fff', borderRadius: 8, boxShadow: '0 2px 12px rgba(0,0,0,0.15)',
          padding: 4, minWidth: 120,
        }}>
          <div onClick={() => { renameSession(ctxMenu.sid, ctxMenu.title); setCtxMenu(null) }}
            style={{ padding: '8px 12px', fontSize: 13, cursor: 'pointer', borderRadius: 4 }}>
            重命名
          </div>
          <div onClick={() => { deleteSession(ctxMenu.sid); setCtxMenu(null) }}
            style={{ padding: '8px 12px', fontSize: 13, cursor: 'pointer', borderRadius: 4, color: '#cf1322' }}>
            删除对话
          </div>
        </div>
      )}
      {/* 左侧会话栏 */}
      <div style={{
        width: 220, background: '#f4f3ee', borderRight: '1px solid #E4E3DD',
        display: 'flex', flexDirection: 'column', padding: 12, flexShrink: 0,
      }}>
        <button onClick={newSession} style={{
          padding: '10px', borderRadius: 8, border: 'none',
          background: '#1A1B1C', color: '#fff', cursor: 'pointer', fontSize: 14, marginBottom: 12,
        }}>
          + 新对话
        </button>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {sessions.map(s => (
            <div key={s.session_id} style={{
              padding: '8px 10px', borderRadius: 6, marginBottom: 4, fontSize: 13,
              background: currentSession === s.session_id ? '#e0e7f5' : 'transparent',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <span
                onClick={() => selectSession(s.session_id)}
                onContextMenu={(e) => {
                  e.preventDefault()
                  setCtxMenu({ x: e.clientX, y: e.clientY, sid: s.session_id, title: s.title })
                }}
                style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', cursor: 'pointer' }}
              >
                {s.title}
              </span>
              <span onClick={() => deleteSession(s.session_id)} style={{ color: '#ccc', cursor: 'pointer', marginLeft: 4 }}>×</span>
            </div>
          ))}
        </div>
      </div>

      {/* 右侧主区 */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', maxWidth: 760, margin: '0 auto', padding: '16px 24px', width: '100%' }}>
        <h1 style={{ fontSize: 18, marginBottom: 8 }}>本地 RAG 问答系统</h1>

        {error && (
          <div style={{ padding: '8px 12px', marginBottom: 8, borderRadius: 6, background: '#fff2f0', border: '1px solid #ffccc7', color: '#cf1322', fontSize: 13 }}>
            {error}
          </div>
        )}

        {/* 上传区 */}
        <div style={{ background: '#fff', borderRadius: 8, padding: 10, marginBottom: 8, border: '1px solid #E4E3DD' }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input type="file" accept=".txt,.md,.docx,.pdf,.csv" ref={fileRef}
              onChange={e => setFile(e.target.files[0])} style={{ flex: 1, fontSize: 13 }} />
            <button onClick={handleUpload} disabled={!file || uploading}
              style={{ padding: '6px 12px', borderRadius: 6, border: 'none', background: '#9BBBF4', color: '#fff', cursor: 'pointer', fontSize: 12, opacity: !file || uploading ? 0.5 : 1 }}>
              {uploading ? '...' : '上传'}
            </button>
          </div>
          {files.length > 0 && (
            <div style={{ marginTop: 6, fontSize: 12, color: '#6B7280' }}>
              {files.map(f => (
                <span key={f.doc_id} style={{ display: 'inline-block', marginRight: 8 }}>
                  {f.filename}({f.chunk_count}块)
                  <span onClick={() => handleDeleteFile(f.doc_id)} style={{ color: '#ccc', cursor: 'pointer', marginLeft: 4 }}>×</span>
                </span>
              ))}
            </div>
          )}
        </div>

        {/* 调试开关 */}
        <div style={{ marginBottom: 8, fontSize: 12 }}>
          <label style={{ cursor: 'pointer', color: '#6B7280' }}>
            <input type="checkbox" checked={showDebug} onChange={e => setShowDebug(e.target.checked)} />
            显示调试信息
          </label>
        </div>

        {/* 调试面板 */}
        {showDebug && lastDebug && (
          <div style={{ background: '#f8f8f6', borderRadius: 8, padding: 10, marginBottom: 8, fontSize: 11, maxHeight: 200, overflowY: 'auto', border: '1px solid #e4e3dd' }}>
            {lastDebug.vector_hits && (
              <div style={{ marginBottom: 6 }}>
                <b>向量召回：</b>
                {lastDebug.vector_hits.map((h, i) => (
                  <div key={i} style={{ color: '#666' }}>[{i+1}] {h.score} {h.text.slice(0, 50)}...</div>
                ))}
              </div>
            )}
            {lastDebug.keyword_hits && (
              <div style={{ marginBottom: 6 }}>
                <b>BM25召回：</b>
                {lastDebug.keyword_hits.map((h, i) => (
                  <div key={i} style={{ color: '#666' }}>[{i+1}] {h.score} {h.text.slice(0, 50)}...</div>
                ))}
              </div>
            )}
            {lastDebug.reranked && (
              <div>
                <b>Rerank后：</b>
                {lastDebug.reranked.map((h, i) => (
                  <div key={i} style={{ color: '#666' }}>[{i+1}] {h.rerank_score} {h.text.slice(0, 50)}...</div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 聊天区 */}
        <div style={{ flex: 1, background: '#fff', borderRadius: 8, border: '1px solid #E4E3DD', display: 'flex', flexDirection: 'column', minHeight: 300 }}>
          <div style={{ flex: 1, padding: 12, overflowY: 'auto', maxHeight: 500 }}>
            {messages.length === 0 && (
              <p style={{ color: '#999', fontSize: 13, textAlign: 'center', marginTop: 30 }}>
                {currentSession ? '输入问题开始对话' : '新建或选择左侧对话'}
              </p>
            )}
            {messages.map((m, i) => (
              <div key={i} style={{ marginBottom: 10, display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
                <div style={{
                  maxWidth: '85%', padding: '8px 12px', borderRadius: 10, fontSize: 13,
                  background: m.role === 'user' ? '#9BBBF4' : '#f0efe9',
                  color: m.role === 'user' ? '#fff' : '#1A1B1C',
                }}>
                  {m.text}
                  {m.contexts && m.contexts.length > 0 && (
                    <div style={{ marginTop: 6, paddingTop: 6, borderTop: '1px solid #ddd', fontSize: 11, color: '#6B7280' }}>
                      {m.contexts.map((c, j) => (
                        <div key={j} style={{ marginTop: 3 }}>[{j+1}] {c.text.slice(0, 60)}...</div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && <div style={{ color: '#999', fontSize: 12, padding: 6 }}>思考中...</div>}
          </div>
          <div style={{ display: 'flex', gap: 8, padding: 10, borderTop: '1px solid #E4E3DD' }}>
            <input value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && send()}
              placeholder="输入问题..."
              style={{ flex: 1, padding: '8px 10px', borderRadius: 6, border: '1px solid #ddd', fontSize: 13, outline: 'none' }} />
            <button onClick={send} disabled={loading}
              style={{ padding: '8px 16px', borderRadius: 6, border: 'none', background: '#1A1B1C', color: '#fff', cursor: 'pointer', fontSize: 13 }}>
              发送
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
