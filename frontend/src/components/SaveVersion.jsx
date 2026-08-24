import { useState } from "react";
import { saveVersion } from "../api/versionsApi";
import "./SaveVersion.css";

export default function SaveVersion({ promptText, responseText, responseModel, responseLatency}) {
    const [name, setName] = useState("");
    const [tag, setTag] = useState("");
    const [includeResponse, setIncludeResponse] = useState(false)
    const [message, setMessage] = useState(null);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);

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
            setName("");
            setTag("");
        } catch(err) {
            setError(err.message || "Failed to save version");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="save-version">
            <input
            type="text"
            placeholder="Version name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            />
            <input
            type="text"
            placeholder="Tag (optional)"
            value={tag}
            onChange={(e) => setTag(e.target.value)}
            maxLength={32}
            />
            <label>
                <input
                type="checkbox"
                checked={includeResponse}
                onChange={(e) => setIncludeResponse(e.target.checked)}
                disabled={!responseText}
                />
                Include response
            </label>
            <button onClick={handleSave} disabled={!name || loading}>
                {loading ? "Saving..." : "Save Version"}
            </button>
            {message && <p style={{ color: "green", fontSize: "0.9rem" }}>{message}</p>}
            {error && <p style={{ color: "red", fontSize: "0.9rem" }}>{error}</p>}
        </div>
    );
}
