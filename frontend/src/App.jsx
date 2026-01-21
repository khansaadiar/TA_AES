// src/App.jsx
import { useState, useEffect } from 'react'
import './index.css'

const API_URL = 'http://localhost:8000'

function App() {
  const [activeTab, setActiveTab] = useState('scoring')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [showResultModal, setShowResultModal] = useState(false)
  const [selectedHistory, setSelectedHistory] = useState(null)
  const [history, setHistory] = useState([])
  const [formData, setFormData] = useState({ pertanyaan: '', kunci_jawaban: '', jawaban: '', max_score: 5 })

  useEffect(() => { if (activeTab === 'history') fetchHistory() }, [activeTab])

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_URL}/history`)
      if (res.ok) setHistory((await res.json()).reverse())
    } catch (err) { console.error(err) }
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: name === 'max_score' ? parseInt(value) || 0 : value
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!formData.pertanyaan || !formData.kunci_jawaban || !formData.jawaban) return alert('Please fill all fields')

    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })
      if (!res.ok) throw new Error('Failed')
      const data = await res.json()
      setResult(data)
      setShowResultModal(true)
    } catch (err) { alert(err.message) }
    finally { setLoading(false) }
  }

  return (
    <div className="app-container">
      <header className="header">
        <div className="logo">AES SYSTEM</div>
        <div className="nav-pills">
          <button className={`nav-link ${activeTab === 'scoring' ? 'active' : ''}`} onClick={() => setActiveTab('scoring')}>Scoring</button>
          <button className={`nav-link ${activeTab === 'history' ? 'active' : ''}`} onClick={() => setActiveTab('history')}>History</button>
        </div>
      </header>

      <div className="main-card">
        {activeTab === 'scoring' ? (
          <div className="stack-container">
            <div className="input-group">
              <div className="label">SOAL</div>
              <textarea name="pertanyaan" className="textarea-balanced" placeholder="ketik soal sekarang..." value={formData.pertanyaan} onChange={handleInputChange} />
            </div>
            <div className="input-group">
              <div className="label">Kunci Jawaban</div>
              <textarea name="kunci_jawaban" className="textarea-balanced" placeholder="tuliskan kunci jawaban..." value={formData.kunci_jawaban} onChange={handleInputChange} />
            </div>
            <div className="input-group">
              <div className="label" style={{ color: 'var(--brand-green)' }}>Jawaban Siswa</div>
              <textarea name="jawaban" className="textarea-balanced student-area" placeholder="masukkan jawaban siswa..." value={formData.jawaban} onChange={handleInputChange} />
            </div>
            <div className="footer-actions">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', background: '#F3F4F6', padding: '0.5rem 1rem', borderRadius: '50px' }}>
                <span style={{ fontWeight: '700', fontSize: '0.85rem', color: '#555' }}>MAX SCORE</span>
                <input type="number" name="max_score" style={{ width: '50px', border: 'none', background: 'transparent', fontWeight: '900', textAlign: 'center', fontSize: '1rem' }} value={formData.max_score} onChange={handleInputChange} />
              </div>
              <button className="btn-primary" onClick={handleSubmit} disabled={loading}>{loading ? 'ANALYZING...' : 'PREDICT'}</button>
            </div>
          </div>
        ) : (
          <div style={{ height: '100%', overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead style={{ position: 'sticky', top: 0, background: 'white', zIndex: 10 }}>
                <tr style={{ textAlign: 'left', borderBottom: '2px solid #eee' }}>
                  <th style={{ padding: '1rem', color: 'var(--brand-mute)' }}>Time</th>
                  <th style={{ padding: '1rem', color: 'var(--brand-mute)' }}>Score</th>
                  <th style={{ padding: '1rem', color: 'var(--brand-mute)' }}>Preview</th>
                  <th style={{ padding: '1rem', color: 'var(--brand-mute)' }}>Detail</th>
                </tr>
              </thead>
              <tbody>
                {history.map(h => (
                  <tr key={h.id} style={{ borderBottom: '1px solid #f9f9f9', cursor: 'pointer' }} onClick={() => setSelectedHistory(h)}>
                    <td style={{ padding: '1rem', fontSize: '0.9rem' }}>{new Date(h.timestamp).toLocaleTimeString()}</td>
                    <td style={{ padding: '1rem', fontWeight: '900', color: 'var(--brand-green)' }}>{h.predicted_score}</td>
                    <td style={{ padding: '1rem', color: '#666' }}>{h.jawaban.substring(0, 50)}...</td>
                    <td style={{ padding: '1rem' }}>
                      <button style={{ border: '1px solid #ddd', background: 'white', padding: '4px 12px', borderRadius: '4px', cursor: 'pointer' }}>View Detail</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {showResultModal && result && (
        <div className="modal-overlay" onClick={() => setShowResultModal(false)}>
          <div className="modal-box" onClick={e => e.stopPropagation()}>
            <div style={{ fontSize: '1rem', fontWeight: '700', letterSpacing: '1px', color: 'var(--brand-mute)' }}>PREDICTION RESULT</div>
            <div className="score-big">{result.predicted_score}</div>
            <div style={{ fontSize: '1.2rem', fontWeight: '700', color: 'var(--brand-dark)', marginBottom: '2rem' }}>out of {result.max_score}</div>
            <button className="btn-primary" style={{ width: '100%' }} onClick={() => setShowResultModal(false)}>CLOSE</button>
          </div>
        </div>
      )}

      {selectedHistory && (
        <div className="modal-overlay" onClick={() => setSelectedHistory(null)}>
          <div className="detail-modal" onClick={e => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h2 style={{ fontSize: '1.5rem', fontWeight: '900', color: 'var(--brand-dark)' }}>Prediction Detail</h2>
              <button onClick={() => setSelectedHistory(null)} style={{ border: 'none', background: 'none', fontSize: '1.5rem', cursor: 'pointer' }}>&times;</button>
            </div>
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', background: '#E8F5E9', padding: '1rem', borderRadius: '12px' }}>
              <span style={{ fontWeight: '700', color: 'var(--brand-dark)' }}>SCORE:</span>
              <span style={{ fontSize: '2rem', fontWeight: '900', color: 'var(--brand-green)' }}>{selectedHistory.predicted_score}</span>
              <span style={{ color: '#666' }}>/ {selectedHistory.max_score}</span>
            </div>
            <div className="detail-block"><div className="detail-title">Soal</div><div className="detail-text">{selectedHistory.pertanyaan}</div></div>
            <div className="detail-block"><div className="detail-title">Kunci Jawaban</div><div className="detail-text">{selectedHistory.kunci_jawaban}</div></div>
            <div className="detail-block" style={{ background: '#F0FDF4', border: '1px solid #DCFCE7' }}><div className="detail-title" style={{ color: 'var(--brand-green)' }}>Jawaban Siswa</div><div className="detail-text">{selectedHistory.jawaban}</div></div>
            <div style={{ textAlign: 'right', fontSize: '0.8rem', color: '#999' }}>Predicted at: {new Date(selectedHistory.timestamp).toLocaleString()}</div>
          </div>
        </div>
      )}
    </div>
  )
}

export default App