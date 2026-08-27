import { useEffect, useMemo, useState } from "react";

import { WorkspaceContext } from "./workspaceContext";
import { loadWorkspaceState, saveWorkspaceState } from "./workspaceStorage";

export function WorkspaceProvider({ children }) {
  // Read storage once, during the first render, so the restored draft is what
  // the editor mounts with. Restoring from an effect instead would render the
  // empty state first and visibly blank the textarea for a frame.
  const [restored] = useState(loadWorkspaceState);

  const [prompt, setPrompt] = useState(restored.prompt);
  const [selectedModels, setSelectedModels] = useState(restored.selectedModels);
  const [activeTab, setActiveTab] = useState(restored.activeTab);
  const [results, setResults] = useState(restored.results);
  const [currentVersionId, setCurrentVersionId] = useState(restored.currentVersionId);
  const [currentTag, setCurrentTag] = useState(restored.currentTag);
  const [versionDraft, setVersionDraft] = useState(restored.versionDraft);

  // Not restored, on purpose. Keys are never written to storage, and a
  // "validated" badge without the key it belongs to is a lie -- so a refresh
  // puts the user back in front of the same gate as a first-time visitor.
  // See workspaceStorage.js.
  const [apiKeys, setApiKeys] = useState({ openai: "", gemini: "", anthropic: "" });
  const [isKeyValid, setIsKeyValid] = useState(false);

  useEffect(() => {
    saveWorkspaceState({
      prompt,
      selectedModels,
      activeTab,
      results,
      currentVersionId,
      currentTag,
      versionDraft,
    });
  }, [
    prompt,
    selectedModels,
    activeTab,
    results,
    currentVersionId,
    currentTag,
    versionDraft,
  ]);

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
      activeTab,
      setActiveTab,
      versionDraft,
      setVersionDraft,
    }),
    [
      prompt,
      selectedModels,
      apiKeys,
      isKeyValid,
      results,
      currentVersionId,
      currentTag,
      activeTab,
      versionDraft,
    ]
  );

  return (
    <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>
  );
}
