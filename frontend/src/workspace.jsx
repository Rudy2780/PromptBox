import { useMemo, useState } from "react";

import { WorkspaceContext } from "./workspaceContext";

export function WorkspaceProvider({ children }) {
  const [prompt, setPrompt] = useState("");
  const [selectedModels, setSelectedModels] = useState(["gpt-4o"]);
  const [apiKeys, setApiKeys] = useState({ openai: "", gemini: "", anthropic: "" });
  const [isKeyValid, setIsKeyValid] = useState(false);
  const [results, setResults] = useState([]);
  const [currentVersionId, setCurrentVersionId] = useState(null);
  const [currentTag, setCurrentTag] = useState(null);

  const value = useMemo(
    () => ({
      prompt,
      setPrompt,
      selectedModels,
      setSelectedModels,
      apiKeys,
      setApiKeys,
      isKeyValid,
      setIsKeyValid,
      results,
      setResults,
      currentVersionId,
      setCurrentVersionId,
      currentTag,
      setCurrentTag,
    }),
    [prompt, selectedModels, apiKeys, isKeyValid, results, currentVersionId, currentTag]
  );

  return (
    <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>
  );
}
