import { useState } from "react";
import { saveVersion } from "../api/versionsApi";
import { useWorkspace } from "../workspaceContext";
import "./SaveVersion.css";

export default function SaveVersion({ promptText, responseText, responseModel, responseLatency}) {
    // Held in the workspace rather than locally: this panel unmounts whenever
    // the user leaves the Versions tab, and a half-typed version name should
    // survive that -- and a refresh -- the same way the draft prompt does.
    const { versionDraft, setVersionDraft } = useWorkspace();
    const { name, tag } = versionDraft;

    const [includeResponse, setIncludeResponse] = useState(false)
    const [message, setMessage] = useState(null);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);

    const setField = (field, value) =>
        setVersionDraft((prev) => ({ ...prev, [field]: value }));

    const handleSave = async () => {
        setMessage(null);
        setError(null);
        setLoading(true);

        const payload = {
            name,
            tag: tag || null,
            prompt_text: promptText,
            response_text: includeResponse ? responseText : null,
            response_model: includeResponse ? responseModel: null,
            response_latency: includeResponse ? responseLatency: null,
        }

        try {
            await saveVersion(payload);
            setMessage("Version Saved!");
            setVersionDraft({ name: "", tag: "" });
        } catch(err) {
            setError(err.message || "Failed to save version");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="save-version">
            <p className="save-version__title">Save version</p>
            <input
            type="text"
            placeholder="Version name"
            value={name}
            onChange={(e) => setField("name", e.target.value)}
            />
            <input
            type="text"
            placeholder="Tag (optional)"
            value={tag}
            onChange={(e) => setField("tag", e.target.value)}
            maxLength={32}
            />
            <label className="save-version__check">
                <input
                type="checkbox"
                checked={includeResponse}
                onChange={(e) => setIncludeResponse(e.target.checked)}
                disabled={!responseText}
                />
                Include response
            </label>
            <button className="pb-btn pb-btn--primary" onClick={handleSave} disabled={!name || loading}>
                {loading ? "Saving..." : "Save Version"}
            </button>
            {message && <p className="pb-status pb-status--ok">{message}</p>}
            {error && <p className="pb-status pb-status--error">{error}</p>}
        </div>
    );
}
