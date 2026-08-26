import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getTemplates } from "../api/templatesApi";
import { useWorkspace } from "../workspaceContext";
import "./Community.css";

/*
 * The prompt template catalogue.
 *
 * Scoped to what the backend actually serves: GET /api/templates/ returns
 * id, name, category and content, and nothing else. There is no author, no
 * publish flow, no likes or forks, and no server-side search -- so none of
 * those appear here.
 */

const FILTERS = [
  { value: "all", label: "All" },
  { value: "reasoning", label: "Reasoning" },
  { value: "structure", label: "Structure" },
  { value: "task", label: "Task" },
];

const CATEGORY_LABELS = {
  reasoning: "Reasoning",
  structure: "Structure",
  task: "Task",
};

const CATEGORY_TONE = {
  reasoning: "pb-tag--purple",
  structure: "pb-tag--green",
  task: "pb-tag--amber",
};

function categoryLabel(category) {
  return CATEGORY_LABELS[category] || category;
}

export default function Community() {
  const [templates, setTemplates] = useState([]);
  const [category, setCategory] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const navigate = useNavigate();
  const { prompt, setPrompt, setCurrentVersionId, setCurrentTag } = useWorkspace();

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        setLoading(true);
        const cat = category === "all" ? null : category;
        const data = await getTemplates(cat);
        if (cancelled) return;
        setTemplates(data);
        setError(null);
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [category]);

  function handleSelect(content) {
    if (prompt && prompt.trim() !== "") {
      const confirmed = window.confirm(
        "You have unsaved content in the editor. Replace it with this template?"
      );
      if (!confirmed) return;
    }
    setPrompt(content);
    // The loaded prompt is no longer the saved version it came from.
    setCurrentVersionId(null);
    setCurrentTag(null);
    navigate("/editor");
  }

  return (
    <div className="community">
      <h1 className="pb-page-title">Community</h1>
      <p className="pb-page-lede">
        Browse the shared prompt template catalogue. Selecting one loads it into
        the editor.
      </p>

      <div className="community__filters" role="group" aria-label="Filter by category">
        {FILTERS.map((filter) => (
          <button
            key={filter.value}
            type="button"
            className="pb-pill"
            aria-pressed={category === filter.value}
            onClick={() => setCategory(filter.value)}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {loading && <p className="pb-empty">Loading templates...</p>}
      {error && <p className="pb-status pb-status--error">{error}</p>}

      {!loading && !error && templates.length === 0 && (
        <p className="pb-empty">No templates found.</p>
      )}

      {!loading && !error && templates.length > 0 && (
        <div className="community__grid">
          {templates.map((template) => (
            <button
              key={template.id}
              type="button"
              className="template-card"
              onClick={() => handleSelect(template.content)}
            >
              <span className="template-card__name">{template.name}</span>
              <p className="template-card__preview">{template.content}</p>
              <span className="template-card__footer">
                <span
                  className={`pb-tag ${CATEGORY_TONE[template.category] || "pb-tag--purple"}`}
                >
                  {categoryLabel(template.category)}
                </span>
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
