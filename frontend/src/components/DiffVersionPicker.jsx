import { useEffect, useState } from 'react'
import { getVersions } from '../api/versionsApi'
import './DiffVersionPicker.css'

export default function DiffVersionPicker({ onCompare, refreshSignal = 0 }) {
  const [versions, setVersions] = useState([])
  const [selectedIds, setSelectedIds] = useState([])
  // Bumped by the Refresh button; the effect below is the only loader.
  const [reloadToken, setReloadToken] = useState(0)

  useEffect(() => {
    // The async work lives inside the effect rather than in a function called
    // from it, so no setState runs synchronously during the effect body. The
    // cancelled flag also stops a late response from setting state after the
    // component has unmounted.
    let cancelled = false

    ;(async () => {
      try {
        const data = await getVersions()
        if (cancelled) return
        setVersions(data)
        setSelectedIds((prev) => prev.filter((id) => data.some((v) => v.id === id)))
      } catch {
        // error intentionally swallowed: the list simply stays as-is on a failed load
      }
    })()

    return () => {
      cancelled = true
    }
  }, [refreshSignal, reloadToken])

  function handleSelect(id) {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(s => s !== id))
    } else if (selectedIds.length < 2) {
      setSelectedIds([...selectedIds, id])
    }
  }

  function handleCompare() {
    const selected = versions.filter(v => selectedIds.includes(v.id))
    selected.sort((a, b) => new Date(a.created_at) - new Date(b.created_at))
    onCompare(selected[0], selected[1], versions.length)
  }

  return (
    <div className="diff-picker">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>Compare Versions</h2>
        <button className="refresh-btn" onClick={() => setReloadToken((n) => n + 1)}>
          Refresh
        </button>
      </div>
      {versions.length === 0 ? (
        <p>No saved versions yet.</p>
      ) : (
        <ul className="diff-picker-list">
          {versions.map((ver) => (
            <li key={ver.id}>
              <button
                className={`diff-picker-btn ${selectedIds.includes(ver.id) ? 'selected' : ''}`}
                onClick={() => handleSelect(ver.id)}
              >
                {ver.name}
                <span className="version-date">
                  {new Date(ver.created_at).toLocaleString()}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      <button
        className="compare-btn"
        onClick={handleCompare}
        disabled={selectedIds.length !== 2}
      >
        Compare
      </button>
    </div>
  )
}
