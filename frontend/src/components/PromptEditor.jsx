import { useState } from "react";
import { executeBatch } from "../api/executeApi";

export default function PromptEditor({
  models,
  apiKey,
  isKeyValid,
  onResults,
  onError,
  prompt,
  setPrompt,
}) {
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async () => {
    onError?.(null);
    setIsLoading(true);

    const hasModels = Array.isArray(models) && models.length > 0;

    try {
      if (!hasModels) {
        throw new Error("No model selected");
      }
      // /api/prompt handles one model as well as several, so there is a single
      // request path. The former /api/execute endpoint has been removed.
      const results = await executeBatch({ prompt, models, apiKeys: apiKey });
      onResults?.(results);
    } catch (error) {
      onError?.(error.message || "Execution failed.");
    } finally {
      setIsLoading(false);
    }
  };

  const isDisabled =
    !isKeyValid || !prompt || isLoading || !models || models.length === 0;

  return (
    <div className="prompt-editor textarea">
      <label htmlFor="prompt-input">Prompt</label>
      <textarea
        id="prompt-input"
        aria-label="Prompt"
        value={prompt}
        onChange={(event) => setPrompt(event.target.value)}
        rows={6}
      />
      <button onClick={handleSubmit} disabled={isDisabled}>
        {isLoading ? "Running..." : "Execute"}
      </button>
    </div>
  );
}
