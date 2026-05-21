function copyText(text) {
  if (navigator?.clipboard?.writeText) {
    navigator.clipboard.writeText(text);
  }
}

function exportText(model, text) {
  const blob = new Blob([text], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${model}-response.txt`;
  a.click();
  URL.revokeObjectURL(url);
}

function ResponseCard({ result }) {
  return (
    <div className="response-card">
      <header className="response-card__header">
        <span className="response-card__label">{result.model}</span>
        <div className="response-card__actions">
          <button onClick={() => copyText(result.response_text)}>Copy</button>
          <button onClick={() => exportText(result.model, result.response_text)}>Export</button>
        </div>
      </header>
      <div className="response-card__body" aria-label={`Response from ${result.model}`}>
        <pre className="response-card__text">{result.response_text}</pre>
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
