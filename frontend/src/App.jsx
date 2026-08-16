import { useState, useEffect } from 'react'

export default function App() {
  const [pollId, setPollId] = useState(() => {
    const params = new URLSearchParams(window.location.search)
    return params.get('poll') || ''
  })
  
  const [poll, setPoll] = useState(null)
  const [question, setQuestion] = useState('')
  const [options, setOptions] = useState(['', ''])
  const [allowMultiple, setAllowMultiple] = useState(false)
  const [selectedOptions, setSelectedOptions] = useState([])
  const [hasVoted, setHasVoted] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    if (!pollId) return

    fetch(`/api/polls/${pollId}`)
      .then(res => {
        if (!res.ok) throw new Error('Not found')
        return res.json()
      })
      .then(data => setPoll(data))
      .catch(() => setPoll(null))

    // Connect WebSocket for real-time live vote counts
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/polls/${pollId}`)

    ws.onmessage = (event) => {
      try {
        const updated = JSON.parse(event.data)
        setPoll(updated)
      } catch (err) {
        console.error(err)
      }
    }

    return () => ws.close()
  }, [pollId])

  const handleAddOption = () => {
    if (options.length < 8) {
      setOptions([...options, ''])
    }
  }

  const handleOptionChange = (idx, val) => {
    const next = [...options]
    next[idx] = val
    setOptions(next)
  }

  const handleRemoveOption = (idx) => {
    if (options.length > 2) {
      setOptions(options.filter((_, i) => i !== idx))
    }
  }

  const handleCreatePoll = async (e) => {
    e.preventDefault()
    const validOptions = options.map(o => o.trim()).filter(Boolean)
    if (validOptions.length < 2 || !question.trim()) return

    const res = await fetch('/api/polls', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question: question.trim(),
        options: validOptions,
        allow_multiple: allowMultiple
      })
    })

    if (res.ok) {
      const data = await res.json()
      setPoll(data)
      setPollId(data.id)
      window.history.pushState({}, '', `?poll=${data.id}`)
    }
  }

  const handleToggleSelect = (optId) => {
    if (hasVoted) return

    if (poll.allow_multiple) {
      setSelectedOptions(prev => 
        prev.includes(optId) ? prev.filter(id => id !== optId) : [...prev, optId]
      )
    } else {
      setSelectedOptions([optId])
    }
  }

  const handleVote = async () => {
    if (!selectedOptions.length || hasVoted) return

    const res = await fetch(`/api/polls/${poll.id}/vote`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ option_ids: selectedOptions })
    })

    if (res.ok) {
      const data = await res.json()
      setPoll(data)
      setHasVoted(true)
    }
  }

  const copyShareLink = () => {
    navigator.clipboard.writeText(window.location.href)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="container">
      <div className="header">
        <div className="logo">⚡ QuickPoll</div>
        {poll && <span className="badge">LIVE</span>}
      </div>

      {!poll ? (
        <form onSubmit={handleCreatePoll}>
          <div className="form-group">
            <label>Poll Question</label>
            <input
              type="text"
              placeholder="e.g. What is your favorite backend language?"
              value={question}
              onChange={e => setQuestion(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label>Poll Options</label>
            <div className="options-list">
              {options.map((opt, idx) => (
                <div key={idx} className="option-input-row">
                  <input
                    type="text"
                    placeholder={`Option ${idx + 1}`}
                    value={opt}
                    onChange={e => handleOptionChange(idx, e.target.value)}
                    required
                  />
                  {options.length > 2 && (
                    <button
                      type="button"
                      className="btn-remove"
                      onClick={() => handleRemoveOption(idx)}
                    >
                      &times;
                    </button>
                  )}
                </div>
              ))}
            </div>

            {options.length < 8 && (
              <button
                type="button"
                className="btn-add-opt"
                onClick={handleAddOption}
              >
                + Add Another Option
              </button>
            )}
          </div>

          <button type="submit" className="btn-primary">
            Create Live Poll
          </button>
        </form>
      ) : (
        <div className="poll-view">
          <h2>{poll.question}</h2>

          <div className="options-view">
            {poll.options.map(opt => {
              const isSelected = selectedOptions.includes(opt.id)
              return (
                <div
                  key={opt.id}
                  className={`poll-option-card ${isSelected ? 'selected' : ''}`}
                  onClick={() => handleToggleSelect(opt.id)}
                >
                  <div
                    className="progress-bar"
                    style={{ width: `${opt.percentage}%` }}
                  />
                  <span className="option-text">{opt.text}</span>
                  <span className="option-stats">
                    {opt.percentage}% ({opt.votes})
                  </span>
                </div>
              )
            })}
          </div>

          {!hasVoted ? (
            <button
              className="btn-primary"
              style={{ marginTop: 12 }}
              disabled={!selectedOptions.length}
              onClick={handleVote}
            >
              Submit Vote
            </button>
          ) : (
            <div className="share-link-box" onClick={copyShareLink} style={{ cursor: 'pointer' }}>
              🔗 {copied ? 'Link copied to clipboard!' : 'Click to copy shareable live link'}
            </div>
          )}

          <div className="poll-footer">
            <span>Total votes: {poll.total_votes}</span>
            <a
              href="/"
              style={{ color: '#58a6ff', textDecoration: 'none' }}
              onClick={(e) => {
                e.preventDefault()
                setPoll(null)
                setPollId('')
                setHasVoted(false)
                setSelectedOptions([])
                window.history.pushState({}, '', '/')
              }}
            >
              + Create new poll
            </a>
          </div>
        </div>
      )}
    </div>
  )
}
