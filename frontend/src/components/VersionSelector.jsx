import { useEffect, useState } from 'react'
import { deleteVersion, getVersions, updateVersion } from '../api/versionsApi'
import './VersionSelector.css'

export default function VersionSelector({ token, onSelectVersion, onVersionDeleted }) {
  const [versions, setVersions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchText, setSearchText] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [editName, setEditName] = useState('')
  const [editTag, setEditTag] = useState('')
  const [editError, setEditError] = useState(null)
  const [savingEdit, setSavingEdit] = useState(false)
  const [deletingId, setDeletingId] = useState(null)

  async function loadVersions(search = '') {
    if (!token) return
    try {
      setLoading(true)
      const data = await getVersions(token, search)
      setVersions(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchText), 300)
    return () => clearTimeout(timer)
  }, [searchText])

  useEffect(() => {
    loadVersions(debouncedSearch)
  }, [debouncedSearch, token])

  function startEdit(version) {
    setEditingId(version.id)
    setEditName(version.name)
    setEditTag(version.tag || '')
    setEditError(null)
  }

  function cancelEdit() {
    setEditingId(null)
    setEditName('')
    setEditTag('')
    setEditError(null)
  }

  async function saveEdit(versionId) {
    const trimmedName = editName.trim()
    const trimmedTag = editTag.trim()

    if (!trimmedName) {
      setEditError('Version name is required')
      return
    }
    if (trimmedTag.length > 32) {
      setEditError('Tag must be 32 characters or fewer')
      return
    }

    try {
      setSavingEdit(true)
      setEditError(null)
      const updated = await updateVersion(token, versionId, {
        name: trimmedName,
        tag: trimmedTag || null,
      })
      setVersions((prev) => prev.map((v) => (v.id === versionId ? updated : v)))
      onSelectVersion(updated)
      cancelEdit()
    } catch (err) {
      setEditError(err.message || 'Failed to update version')
    } finally {
      setSavingEdit(false)
    }
  }

  async function handleDelete(versionId) {
    try {
      setDeletingId(versionId)
      setError(null)
      await deleteVersion(token, versionId)
      setVersions((prev) => prev.filter((v) => v.id !== versionId))
      if (onVersionDeleted) {
        onVersionDeleted(versionId)
      }
      if (editingId === versionId) {
        cancelEdit()
      }
    } catch (err) {
      setError(err.message || 'Failed to delete version')
    } finally {
      setDeletingId(null)
    }
  }


  if (error) {
    return <div className="version-selector error">{error}</div>
  }

  return (
    <div className="version-selector">
      <div className="version-header">
        <h2>Saved Versions</h2>
        <button 
          className="refresh-btn" 
          onClick={() => loadVersions(debouncedSearch)} 
          disabled={loading}
        >
          Refresh
        </button>
      </div>
      <input
        type="text"
        className="version-search"
        placeholder="Search by name or tag"
        value={searchText}
        onChange={(e) => setSearchText(e.target.value)}
      />
      {loading ? (
        <p>Loading versions...</p>
      ) : versions.length === 0 ? (
        <p>{debouncedSearch ? 'No results found.' : 'No saved versions yet.'}</p>
      ) : (
        <ul className="version-list">
          {versions.map((ver) => (
            <li key={ver.id}>
              {editingId === ver.id ? (
                <div>
                  <input
                    type="text"
                    placeholder="Version name"
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                  />
                  <input
                    type="text"
                    placeholder="Tag (optional)"
                    value={editTag}
                    onChange={(e) => setEditTag(e.target.value)}
                    maxLength={32}
                  />
                  <button onClick={() => saveEdit(ver.id)} disabled={savingEdit}>
                    {savingEdit ? 'Saving...' : 'Save'}
                  </button>
                  <button onClick={cancelEdit} disabled={savingEdit}>Cancel</button>
                  {editError && <p>{editError}</p>}
                </div>
              ) : (
                <div className="version-row">
                  <button
                    className="version-btn"
                    onClick={() => onSelectVersion(ver)}
                  >
                    {ver.name}
                    {ver.tag && <span className="version-tag">{ver.tag}</span>}
                    <br />
                    <span className="version-date">
                      {new Date(ver.created_at).toLocaleString()}
                    </span>
                  </button>
                  <button className="edit-btn" onClick={() => startEdit(ver)}>Edit</button>
                  <button
                    className="delete-btn"
                    onClick={() => handleDelete(ver.id)}
                    disabled={deletingId === ver.id}
                  >
                    {deletingId === ver.id ? 'Deleting...' : 'Delete'}
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
