import { useMemo, useState } from "react";
import { validateKey } from "../api/client";
import "./ModelSelector.css";

// Copy of the supported-model list; source of truth is backend/app/supported_models.py
const MODEL_GROUPS = {
  openai: ["gpt-4o", "gpt-4o-mini"],
  anthropic: ["claude-opus-4-7", "claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
  gemini: ["gemini-2.5-flash", "gemini-2.5-pro"],
};

const MODEL_PROVIDER = Object.entries(MODEL_GROUPS).reduce((acc, [provider, models]) => {
  models.forEach((m) => (acc[m] = provider));
  return acc;
}, {});

export default function ModelSelector({
  // new multi-provider props
  apiKeys,
  setApiKeys,
  selectedModels,
  setSelectedModels,
  onValidated,
  // legacy single-provider props (kept for backward compatibility & tests)
  provider,
  setProvider,
  model,
  setModel,
  apiKey,
  setApiKey,
}) {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);

  // Memoised: without this the fallback allocates a new array on every render,
  // which invalidates the selectedProviders useMemo below every time.
  const safeSelectedModels = useMemo(
    () => selectedModels ?? (model ? [model] : []),
    [selectedModels, model]
  );

  const toggleModel = (model) => {
    setSelectedModels?.((prev = safeSelectedModels) => {
      if (prev.includes(model)) {
        const next = prev.filter((m) => m !== model);
        return next.length ? next : [model]; // keep at least one selected
      }
      return [...prev, model];
    });
  };

  const selectedProviders = useMemo(() => {
    const providers = new Set();
    safeSelectedModels.forEach((m) => {
      const p = MODEL_PROVIDER[m];
      if (p) providers.add(p);
    });
    return Array.from(providers);
  }, [safeSelectedModels]);

  const hasMultiKey = apiKeys && setApiKeys;

  const handleValidate = async () => {
    if (!selectedProviders.length) return;

    setLoading(true);
    setStatus(null);

    try {
      const results = await Promise.all(
        selectedProviders.map((p) => {
          const key =
            (hasMultiKey ? apiKeys?.[p] : apiKey) ||
            "";
          return validateKey(p, key).then((r) => ({ provider: p, ok: r.status === 200 }));
        })
      );

      const allValid = results.every((r) => r.ok);
      setStatus(allValid ? "valid" : "invalid");
      onValidated?.(allValid);
    } catch {
      // A rejected request -- offline, CORS, or a Render cold-start timeout --
      // used to skip setLoading(false) entirely, pinning the button at
      // "Validating..." forever and leaving Execute gated until a reload.
      // Reported as its own state rather than "invalid" so a transport failure
      // is not misattributed to the user's key.
      setStatus("error");
      onValidated?.(false);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="model-config">
      {setProvider && setModel ? (
        <div className="model-config__legacy">
          <label className="pb-label" htmlFor="provider-select">
            Provider
          </label>
          <select
            id="provider-select"
            className="pb-select"
            value={provider || "openai"}
            onChange={(e) => setProvider(e.target.value)}
          >
            {Object.keys(MODEL_GROUPS).map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>

          <label className="pb-label" htmlFor="model-select">
            Model
          </label>
          <select
            id="model-select"
            className="pb-select"
            value={model || MODEL_GROUPS[provider || "openai"][0]}
            onChange={(e) => setModel(e.target.value)}
          >
            {(MODEL_GROUPS[provider || "openai"] || []).map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      <section className="model-config__section">
        <span className="pb-label">Model</span>
        <div className="model-config__groups">
          {Object.entries(MODEL_GROUPS).map(([prov, models]) => (
            <div className="model-config__group" key={prov}>
              <span className="model-config__group-name">{prov}</span>
              <div className="model-config__pills">
                {models.map((m) => (
                  <button
                    key={m}
                    type="button"
                    className="pb-pill"
                    aria-pressed={safeSelectedModels.includes(m)}
                    onClick={() => toggleModel(m)}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="model-config__section">
        <span className="pb-label">API keys</span>
        {hasMultiKey ? (
          <div className="model-config__keys">
            {Object.keys(MODEL_GROUPS).map((prov) => (
              <div key={prov} className="model-config__key-row">
                <label className="model-config__key-label" htmlFor={`key-${prov}`}>
                  {prov}
                </label>
                <input
                  id={`key-${prov}`}
                  type="password"
                  className="pb-input"
                  placeholder={`Key for ${prov}`}
                  value={apiKeys?.[prov] || ""}
                  onChange={(e) =>
                    setApiKeys?.((prev) => ({ ...prev, [prov]: e.target.value }))
                  }
                />
              </div>
            ))}
          </div>
        ) : (
          <input
            type="password"
            className="pb-input"
            placeholder="Enter API Key"
            value={apiKey || ""}
            onChange={(e) => setApiKey?.(e.target.value)}
          />
        )}

        <button
          className="pb-btn pb-btn--sm model-config__validate"
          onClick={handleValidate}
          disabled={!selectedProviders.length || loading}
        >
          {loading
            ? "Validating..."
            : hasMultiKey
              ? "Validate Selected Providers"
              : "Validate Key"}
        </button>

        {status === "valid" && (
          <p className="pb-status pb-status--ok">API key is valid</p>
        )}
        {status === "invalid" && (
          <p className="pb-status pb-status--error">Invalid API key</p>
        )}
        {status === "error" && (
          <p className="pb-status pb-status--error">
            Could not reach the server to validate. Check your connection and try
            again.
          </p>
        )}
      </section>
    </div>
  );
}
