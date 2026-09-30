import { useEffect, useState } from 'react'
import { api } from '../api/client'

export default function Documents() {
  const [documents, setDocuments] = useState([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')

  async function loadDocuments() {
    try {
      const docs = await api.listDocuments()
      setDocuments(docs)
    } catch (err) {
      setError(err.message)
    }
  }

  useEffect(() => {
    loadDocuments()
  }, [])

  async function handleUpload(e) {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    setError('')
    try {
      await api.uploadDocument(file)
      await loadDocuments()
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  async function handleDelete(id) {
    try {
      await api.deleteDocument(id)
      await loadDocuments()
    } catch (err) {
      setError(err.message)
    }
  }

  const statusColor = {
    READY: 'bg-green-100 text-green-800',
    PROCESSING: 'bg-yellow-100 text-yellow-800',
    PENDING: 'bg-slate-100 text-slate-800',
    FAILED: 'bg-red-100 text-red-800',
  }

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Documents</h1>
        <label className="bg-slate-900 text-white px-4 py-2 rounded-lg cursor-pointer hover:bg-slate-800">
          {uploading ? 'Uploading...' : 'Upload document'}
          <input type="file" accept=".pdf,.docx,.txt" className="hidden" onChange={handleUpload} disabled={uploading} />
        </label>
      </div>

      {error && <p className="text-red-600 text-sm mb-4">{error}</p>}

      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-slate-500 text-left">
            <tr>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Chunks</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Uploaded</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <tr key={doc.id} className="border-t">
                <td className="px-4 py-3 font-medium text-slate-800">{doc.fileName}</td>
                <td className="px-4 py-3 uppercase text-slate-500">{doc.fileType}</td>
                <td className="px-4 py-3">{doc.chunkCount}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusColor[doc.status] || ''}`}>
                    {doc.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-500">{new Date(doc.uploadedAt).toLocaleString()}</td>
                <td className="px-4 py-3 text-right">
                  <button onClick={() => handleDelete(doc.id)} className="text-red-600 hover:underline">
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {documents.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-slate-400">No documents yet. Upload one to get started.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
