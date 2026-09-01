import { useState } from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";

function copyText(text) {
  if (navigator?.clipboard?.writeText) {
    navigator.clipboard.writeText(text);
  }
}

/** Model output is markdown, so it exports as a .md file the formatting survives in. */
function exportMarkdown(model, text) {
  const blob = new Blob([text], { type: "text/markdown" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${model}-response.md`;
  a.click();
  URL.revokeObjectURL(url);
}

function ResponseCard({ result }) {
  const [raw, setRaw] = useState(false);
  const text = result.response_text || "";

  return (
    <div className="response-card">
      <header className="response-card__header">
        <span className="response-card__label">{result.model}</span>
        <div className="response-card__actions">
          <div className="response-card__toggle" role="group" aria-label="View mode">
            <button
              type="button"
              aria-pressed={!raw}
              className={raw ? "" : "is-active"}
              onClick={() => setRaw(false)}
            >
              Formatted
            </button>
            <button
              type="button"
              aria-pressed={raw}
              className={raw ? "is-active" : ""}
              onClick={() => setRaw(true)}
            >
              Markdown
            </button>
          </div>
          <button onClick={() => copyText(text)}>Copy</button>
          <button onClick={() => exportMarkdown(result.model, text)}>Export .md</button>
        </div>
      </header>
      <div className="response-card__body" aria-label={`Response from ${result.model}`}>
        {raw ? (
          <pre className="response-card__text">{text}</pre>
        ) : (
          <div className="response-card__markdown">
            <Markdown remarkPlugins={[remarkGfm]}>{text}</Markdown>
          </div>
        )}
      </div>
      <footer className="response-card__footer">
        {result.latency?.toFixed ? result.latency.toFixed(2) : result.latency}s
      </footer>
    </div>
  );
}

function ResponseDisplay({ results, result }) {
  const list = results || (result ? [result] : []);
  if (!list || list.length === 0) return null;

  return (
    <section aria-label="Model responses" className="response-grid">
      {list.map((r) => (
        <ResponseCard key={r.model} result={r} />
      ))}
    </section>
  );
}

export default ResponseDisplay;
