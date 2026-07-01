import { useState, useEffect, useRef, useCallback } from 'react'

function KnowledgePanel({ token, onClose }) {
    const [documents, setDocuments] = useState([])
    const [stats, setStats] = useState({ document_count: 0, chunk_count: 0 })
    const [uploading, setUploading] = useState(false)
    const [uploadProgress, setUploadProgress] = useState('')
    const [dragOver, setDragOver] = useState(false)
    const [trainingText, setTrainingText] = useState('')
    const [isTraining, setIsTraining] = useState(false)
    const fileInputRef = useRef(null)

    const authHeaders = {
        Authorization: `Bearer ${token}`,
    }

    // Load documents and stats on mount
    useEffect(() => {
        loadDocuments()
        loadStats()
    }, [])

    const loadDocuments = async () => {
        try {
            const res = await fetch('/api/knowledge/documents', { headers: authHeaders })
            const data = await res.json()
            if (data.success) setDocuments(data.documents)
        } catch (e) {
            console.error('Failed to load documents', e)
        }
    }

    const loadStats = async () => {
        try {
            const res = await fetch('/api/knowledge/stats', { headers: authHeaders })
            const data = await res.json()
            if (data.success) setStats(data.stats)
        } catch (e) {
            console.error('Failed to load stats', e)
        }
    }

    const handleUpload = async (file) => {
        if (!file) return

        const allowedTypes = ['.txt', '.md', '.pdf', '.csv', '.json', '.py', '.js', '.html', '.css', '.log']
        const ext = '.' + file.name.split('.').pop().toLowerCase()
        if (!allowedTypes.includes(ext)) {
            alert(`Unsupported file type: ${ext}\nSupported: ${allowedTypes.join(', ')}`)
            return
        }

        if (file.size > 10 * 1024 * 1024) {
            alert('File too large. Maximum size is 10MB.')
            return
        }

        setUploading(true)
        setUploadProgress(`Uploading ${file.name}...`)

        const formData = new FormData()
        formData.append('file', file)

        try {
            const res = await fetch('/api/knowledge/upload', {
                method: 'POST',
                headers: { Authorization: `Bearer ${token}` },
                body: formData,
            })

            const data = await res.json()

            if (data.success) {
                setUploadProgress(`✅ ${file.name} — ${data.document.chunk_count} chunks embedded`)
                await loadDocuments()
                await loadStats()
                setTimeout(() => {
                    setUploading(false)
                    setUploadProgress('')
                }, 2500)
            } else {
                setUploadProgress(`❌ ${data.message || 'Upload failed'}`)
                setTimeout(() => {
                    setUploading(false)
                    setUploadProgress('')
                }, 3000)
            }
        } catch (err) {
            setUploadProgress('❌ Network error. Please try again.')
            setTimeout(() => {
                setUploading(false)
                setUploadProgress('')
            }, 3000)
        }
    }

    const handleDelete = async (docId, filename) => {
        if (!confirm(`Delete "${filename}" and all its embeddings?`)) return

        try {
            const res = await fetch(`/api/knowledge/documents/${docId}`, {
                method: 'DELETE',
                headers: authHeaders,
            })
            const data = await res.json()
            if (data.success) {
                setDocuments((prev) => prev.filter((d) => d.id !== docId))
                await loadStats()
            }
        } catch (err) {
            console.error('Failed to delete document', err)
        }
    }

    const handleTrainText = async () => {
        if (!trainingText.trim()) return
        setIsTraining(true)
        try {
            const res = await fetch('/api/knowledge/train', {
                method: 'POST',
                headers: { ...authHeaders, 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: trainingText }),
            })
            const data = await res.json()
            if (data.success) {
                setTrainingText('')
                alert('✅ Training successful! The AI now knows about this.')
                await loadDocuments()
                await loadStats()
            } else {
                alert('❌ Training failed: ' + data.message)
            }
        } catch (e) {
            alert('❌ Network error during training')
        } finally {
            setIsTraining(false)
        }
    }

    const handleDrop = useCallback((e) => {
        e.preventDefault()
        setDragOver(false)
        const file = e.dataTransfer?.files?.[0]
        if (file) handleUpload(file)
    }, [])

    const handleDragOver = useCallback((e) => {
        e.preventDefault()
        setDragOver(true)
    }, [])

    const handleDragLeave = useCallback(() => {
        setDragOver(false)
    }, [])

    const getFileIcon = (filename) => {
        const ext = filename.split('.').pop().toLowerCase()
        const icons = {
            pdf: '📕', txt: '📄', md: '📝', csv: '📊',
            json: '🔧', py: '🐍', js: '⚡', html: '🌐',
            css: '🎨', log: '📋',
        }
        return icons[ext] || '📁'
    }

    const getFileClass = (filename) => {
        const ext = filename.split('.').pop().toLowerCase()
        if (ext === 'pdf') return 'pdf'
        if (ext === 'txt' || ext === 'log') return 'txt'
        if (ext === 'md') return 'md'
        if (ext === 'csv') return 'csv'
        return 'other'
    }

    const formatSize = (bytes) => {
        if (bytes < 1024) return `${bytes} B`
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    }

    const formatDate = (dateStr) => {
        const d = new Date(dateStr)
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
    }

    return (
        <>
            <div className="knowledge-panel-overlay" onClick={onClose} />
            <div className="knowledge-panel">
                <div className="knowledge-panel-header">
                    <h2>📚 Knowledge Base</h2>
                    <button className="knowledge-close-btn" onClick={onClose}>✕</button>
                </div>

                <div className="knowledge-panel-body">
                    {/* Training Input */}
                    <div className="manual-training">
                        <h3>Manual Training</h3>
                        <p className="training-hint">Type information or a URL to train the AI permanently.</p>
                        <textarea
                            className="training-textarea"
                            placeholder="Example: Saygin Kumar AG is the CEO of QAWebPrints..."
                            value={trainingText}
                            onChange={(e) => setTrainingText(e.target.value)}
                        />
                        <button
                            className="train-btn"
                            onClick={handleTrainText}
                            disabled={isTraining || !trainingText.trim()}
                        >
                            {isTraining ? '🧠 Training...' : '⚡ Train AI'}
                        </button>
                    </div>

                    {/* Stats */}
                    <div className="knowledge-stats">
                        <div className="stat-card">
                            <div className="stat-value">{stats.document_count}</div>
                            <div className="stat-label">Documents</div>
                        </div>
                        <div className="stat-card">
                            <div className="stat-value">{stats.chunk_count}</div>
                            <div className="stat-label">Embeddings</div>
                        </div>
                    </div>

                    {/* Upload Area */}
                    {uploading ? (
                        <div className="upload-progress">
                            <div className="upload-progress-header">
                                <span>{uploadProgress}</span>
                            </div>
                            <div className="upload-progress-bar">
                                <div className="upload-progress-fill" style={{ width: '100%' }} />
                            </div>
                        </div>
                    ) : (
                        <div
                            className={`upload-area ${dragOver ? 'drag-over' : ''}`}
                            onClick={() => fileInputRef.current?.click()}
                            onDrop={handleDrop}
                            onDragOver={handleDragOver}
                            onDragLeave={handleDragLeave}
                        >
                            <div className="upload-icon">📤</div>
                            <p>
                                Drop files here or{' '}
                                <span className="upload-browse">browse</span>
                            </p>
                            <p className="upload-hint">
                                TXT, MD, PDF, CSV, JSON, PY, JS — max 10MB
                            </p>
                            <input
                                ref={fileInputRef}
                                type="file"
                                hidden
                                accept=".txt,.md,.pdf,.csv,.json,.py,.js,.html,.css,.log"
                                onChange={(e) => handleUpload(e.target.files?.[0])}
                            />
                        </div>
                    )}

                    {/* Document List */}
                    <div className="documents-section">
                        <h3>Uploaded Documents</h3>
                        {documents.length > 0 ? (
                            <div className="doc-list">
                                {documents.map((doc) => (
                                    <div key={doc.id} className="doc-item">
                                        <div className={`doc-icon ${getFileClass(doc.filename)}`}>
                                            {getFileIcon(doc.filename)}
                                        </div>
                                        <div className="doc-info">
                                            <div className="doc-name">{doc.filename}</div>
                                            <div className="doc-meta">
                                                <span>{formatSize(doc.file_size)}</span>
                                                <span>•</span>
                                                <span>{doc.chunk_count} chunks</span>
                                                <span>•</span>
                                                <span>{formatDate(doc.created_at)}</span>
                                            </div>
                                        </div>
                                        <span className={`doc-status ${doc.status}`}>
                                            {doc.status === 'ready' ? '● Ready' :
                                                doc.status === 'processing' ? '◌ Processing' : '✕ Error'}
                                        </span>
                                        <button
                                            className="doc-delete-btn"
                                            onClick={() => handleDelete(doc.id, doc.filename)}
                                            title="Delete document"
                                        >
                                            🗑
                                        </button>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="no-docs">
                                <div className="no-docs-icon">📭</div>
                                <p>No documents uploaded yet</p>
                                <p style={{ marginTop: '4px', fontSize: '0.7rem', color: '#444' }}>
                                    Upload files to train the AI with your custom data
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </>
    )
}

export default KnowledgePanel
