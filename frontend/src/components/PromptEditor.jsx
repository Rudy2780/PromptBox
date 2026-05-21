import { useState } from "react";
import { executeBatch, executePrompt } from "../api/executeApi";

export default function PromptEditor({
  models,
  model, // legacy single model
  apiKey,
  isKeyValid,
  onResults,
  onResult, // legacy single result
  onError,
  prompt,
  setPrompt,
}) {
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async () => {
    onError?.(null);
    setIsLoading(true);

    const hasModels = Array.isArray(models) && models.length > 0;
    const singleModel = model || (hasModels ? models[0] : null);

    try {
      if (hasModels) {
        const results = await executeBatch({ prompt, models, apiKeys: apiKey });
        onResults?.(results);
      } else if (singleModel) {
        const result = await executePrompt({ prompt, model: singleModel, apiKey });
        onResult?.(result);
      } else {
        throw new Error("No model selected");
      }
    } catch (error) {
      onError?.(error.message || "Execution failed.");
    } finally {
      setIsLoading(false);
    }
  };

  const isDisabled =
    !isKeyValid ||
    !prompt ||
    isLoading ||
    (!model && (!models || models.length === 0));

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
