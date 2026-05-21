import { useMemo, useState } from "react";
import { validateKey } from "../api/client";

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

  const safeSelectedModels = selectedModels ?? (model ? [model] : []);

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

    setLoading(false);
  };

  return (
    <div className="model-config">
      <label>Model Configuration</label>

      {setProvider && setModel ? (
        <>
          <label htmlFor="provider-select">Provider</label>
          <select
            id="provider-select"
            value={provider || "openai"}
            onChange={(e) => setProvider(e.target.value)}
          >
            {Object.keys(MODEL_GROUPS).map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>

          <label htmlFor="model-select">Model</label>
          <select
            id="model-select"
            value={model || MODEL_GROUPS[provider || "openai"][0]}
            onChange={(e) => setModel(e.target.value)}
          >
            {(MODEL_GROUPS[provider || "openai"] || []).map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </>
      ) : null}

      <label>Models (mix providers freely)</label>
      <div className="model-checkboxes">
        {Object.entries(MODEL_GROUPS).map(([prov, models]) => (
          <div key={prov}>
            <strong style={{ fontSize: "0.95rem" }}>{prov}</strong>
            {models.map((m) => (
              <label key={m} className="model-option">
                <input
                  type="checkbox"
                  checked={safeSelectedModels.includes(m)}
                  onChange={() => toggleModel(m)}
                />
                {m}
              </label>
            ))}
          </div>
        ))}
      </div>

      <label>API Keys (per provider)</label>
      {hasMultiKey ? (
        <div className="api-keys-grid">
          {Object.keys(MODEL_GROUPS).map((prov) => (
            <div key={prov} className="api-key-row">
              <span className="api-key-label">{prov}</span>
              <input
                type="password"
                placeholder={`Key for ${prov}`}
                value={apiKeys?.[prov] || ""}
                onChange={(e) => setApiKeys?.((prev) => ({ ...prev, [prov]: e.target.value }))}
                className="api-key-input"
              />
            </div>
          ))}
        </div>
      ) : (
        <input
          type="password"
          placeholder="Enter API Key"
          value={apiKey || ""}
          onChange={(e) => setApiKey?.(e.target.value)}
          className="api-key-input"
        />
      )}

      <button onClick={handleValidate} disabled={!selectedProviders.length || loading}>
        {loading ? "Validating..." : hasMultiKey ? "Validate Selected Providers" : "Validate Key"}
      </button>

      {status === "valid" && <p style={{ color: "green", fontSize: "0.9rem" }}>API key is valid</p>}
      {status === "invalid" && <p style={{ color: "red", fontSize: "0.9rem" }}>Invalid API key</p>}
    </div>
  );
}
