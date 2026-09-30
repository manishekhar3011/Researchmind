import { useState, useRef, useEffect } from 'react'
import { api } from '../api/client'

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [conversationId, setConversationId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend(e) {
    e.preventDefault()
    if (!input.trim()) return
    const userText = input
    setInput('')
    setError('')
    setMessages((prev) => [...prev, { role: 'USER', content: userText }])
    setLoading(true)

    try {
      const res = await api.sendChat(userText, conversationId, [])
      setConversationId(res.conversationId)
      setMessages((prev) => [
        ...prev,
        {
          role: 'ASSISTANT',
          content: res.answer,
          citations: res.citations,
          grounded: res.grounded,
          faithfulnessScore: res.faithfulnessScore,
          latencyMs: res.latencyMs,
        },
      ])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleNewConversation() {
    setConversationId(null)
    setMessages([])
  }

  return (
    <div className="max-w-3xl mx-auto flex flex-col h-[calc(100vh-56px)]">
      <div className="flex items-center justify-between px-4 py-3 border-b bg-white">
        <h2 className="font-semibold text-slate-800">Research Chat</h2>
        <button onClick={handleNewConversation} className="text-sm text-slate-500 hover:text-slate-900">
          New conversation
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 bg-slate-50">
        {messages.length === 0 && (
          <p className="text-slate-400 text-center mt-10">
            Ask a question about your uploaded documents. If there isn't enough evidence, ResearchMind will tell you instead of guessing.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === 'USER' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] rounded-xl px-4 py-3 ${m.role === 'USER' ? 'bg-slate-900 text-white' : 'bg-white shadow-sm text-slate-800'}`}>
              <p className="whitespace-pre-wrap text-sm">{m.content}</p>

              {m.role === 'ASSISTANT' && m.citations && m.citations.length > 0 && (
                <div className="mt-3 pt-3 border-t border-slate-100 space-y-1">
                  {m.citations.map((c) => (
                    <p key={c.index} className="text-xs text-slate-500">
                      [{c.index}] {c.document} — Page {c.page}, {c.section} (score {c.rerankScore.toFixed(2)})
                    </p>
                  ))}
                </div>
              )}

              {m.role === 'ASSISTANT' && (
                <p className="text-xs text-slate-400 mt-2">
                  {m.grounded ? `Faithfulness: ${m.faithfulnessScore != null ? m.faithfulnessScore.toFixed(2) : 'n/a'}` : 'No supporting evidence found'} · {m.latencyMs}ms
                </p>
              )}
            </div>
          </div>
        ))}
        {loading && <p className="text-slate-400 text-sm">ResearchMind is thinking...</p>}
        <div ref={bottomRef} />
      </div>

      {error && <p className="text-red-600 text-sm px-4 py-2">{error}</p>}

      <form onSubmit={handleSend} className="flex items-center gap-2 p-4 border-t bg-white">
        <input
          value={input} onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about your documents..."
          className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-slate-500"
        />
        <button type="submit" disabled={loading} className="bg-slate-900 text-white px-5 py-2 rounded-lg hover:bg-slate-800 disabled:opacity-50">
          Send
        </button>
      </form>
    </div>
  )
}
