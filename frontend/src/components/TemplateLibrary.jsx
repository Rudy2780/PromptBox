import { useEffect, useState } from 'react'
import { getTemplates } from '../api/templatesApi'
import './TemplateLibrary.css'

export default function TemplateLibrary({ onSelectTemplate, currentPrompt }) {
  const [templates, setTemplates] = useState([])
  const [category, setCategory] = useState('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  async function loadTemplates() {
    try {
      setLoading(true)
      const cat = category === 'all' ? null : category
      const data = await getTemplates(cat)
      setTemplates(data)
      setError(null)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTemplates()
  }, [category])

  function handleSelect(content) {
    if (currentPrompt && currentPrompt.trim() !== '') {
      const confirmed = window.confirm(
        'You have unsaved content in the editor. Replace it with this template?'
      )
      if (!confirmed) return
    }
    onSelectTemplate(content)
  }

  return (
    <div className="template-library">
      <h2>Prompt Templates</h2>

      <div className="template-filter">
        <button
          className={category === 'all' ? 'active' : ''}
          onClick={() => setCategory('all')}
        >
          All
        </button>
        <button
          className={category === 'reasoning' ? 'active' : ''}
          onClick={() => setCategory('reasoning')}
        >
          Reasoning
        </button>
        <button
          className={category === 'structure' ? 'active' : ''}
          onClick={() => setCategory('structure')}
        >
          Structure
        </button>
        <button
          className={category === 'task' ? 'active' : ''}
          onClick={() => setCategory('task')}
        >
          Task
        </button>
      </div>

      {loading && <p>Loading templates...</p>}
      {error && <p className="template-error">{error}</p>}

      {!loading && !error && templates.length === 0 && (
        <p>No templates found.</p>
      )}

      {!loading && !error && (
        <ul className="template-list">
          {templates.map((t) => (
            <li key={t.id}>
              <button
                className="template-btn"
                onClick={() => handleSelect(t.content)}
              >
                <span className="template-name">{t.name}</span>
                <span className={`template-category ${t.category}`}>
                  {t.category === 'reasoning' ? 'Reasoning' : 
                   t.category === 'structure' ? 'Structure' : 'Task'}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}