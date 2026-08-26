import { useState } from "react";

import ModelSelector from "../components/ModelSelector";
import PromptEditor from "../components/PromptEditor";
import ResponseDisplay from "../components/ResponseDisplay";
import SaveVersion from "../components/SaveVersion";
import VersionSelector from "../components/VersionSelector";
import DiffVersionPicker from "../components/DiffVersionPicker";
import DiffView from "../components/DiffView";
import ExportDropdown from "../components/ExportDropdown";
import { useWorkspace } from "../workspaceContext";
import "./Editor.css";

const TABS = ["Write", "Versions", "Results"];

export default function Editor({ user }) {
  // A guest has no session, so every authenticated call would 401. Rather than
  // rendering panels that silently fail (or, as before, vanish with no
  // explanation), guests get a clear prompt to sign in.
  const isGuest = Boolean(user?.isGuest);
  const isAuthenticated = Boolean(user) && !isGuest;

  // Shared with the rest of the shell so navigating to Community and back does
  // not discard the draft prompt or the validated API keys.
  const {
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
  } = useWorkspace();

  const [activeTab, setActiveTab] = useState("Write");
  const [error, setError] = useState(null);
  const [versionA, setVersionA] = useState(null);
  const [versionB, setVersionB] = useState(null);
  const [totalVersions, setTotalVersions] = useState(0);
  const [versionsRefreshSignal, setVersionsRefreshSignal] = useState(0);

  const handleSelectVersion = (version) => {
    setCurrentVersionId(version.id);
    setCurrentTag(version.tag || null);
    setPrompt(version.prompt_text);
    if (version.response_text) {
      setResults([
        {
          model: version.response_model,
          response_text: version.response_text,
          latency: version.response_latency,
        },
      ]);
    } else {
      setResults([]);
    }
  };

  function handleCompare(a, b, total) {
    setVersionA(a);
    setVersionB(b);
    setTotalVersions(total);
  }

  function handleVersionDeleted(deletedVersionId) {
    setVersionsRefreshSignal((prev) => prev + 1);
    if (currentVersionId === deletedVersionId) {
      setCurrentVersionId(null);
      setCurrentTag(null);
    }
  }

  function handleResults(next) {
    setResults(next);
    // Land the user on the output they just asked for.
    setActiveTab("Results");
  }

  return (
    <div className="editor">
      <div className="editor__tabs" role="tablist" aria-label="Editor sections">
        {TABS.map((tab) => (
          <button
            key={tab}
            role="tab"
            id={`tab-${tab.toLowerCase()}`}
            aria-selected={activeTab === tab}
            aria-controls={`panel-${tab.toLowerCase()}`}
            className="editor__tab"
            onClick={() => setActiveTab(tab)}
          >
            {tab}
            {tab === "Results" && results.length > 0 && (
              <span className="editor__tab-count">{results.length}</span>
            )}
          </button>
        ))}
      </div>

      {isGuest && (
        <p className="editor__banner" data-testid="guest-notice">
          You are browsing as a guest. Running prompts, saving versions and
          exporting all require an account -- sign in to enable them.
        </p>
      )}

      {activeTab === "Write" && (
        <div
          className="editor__write"
          role="tabpanel"
          id="panel-write"
          aria-labelledby="tab-write"
        >
          <div className="editor__col">
            <section className="editor__section">
              <PromptEditor
                models={selectedModels}
                apiKey={apiKeys}
                isKeyValid={isKeyValid}
                onResults={handleResults}
                onError={setError}
                prompt={prompt}
                setPrompt={setPrompt}
              />
            </section>

            {error && <p className="editor__error">{error}</p>}
          </div>

          <div className="editor__col">
            <ModelSelector
              selectedModels={selectedModels}
              setSelectedModels={setSelectedModels}
              apiKeys={apiKeys}
              setApiKeys={setApiKeys}
              onValidated={setIsKeyValid}
            />

            {/* Only rendered when the loaded version actually carries a tag --
                PromptVersion.tag is a single optional string, and there is no
                tagging feature beyond it. */}
            {currentTag && (
              <section className="editor__section">
                <span className="pb-label">Tags</span>
                <div className="pb-row">
                  <span className="pb-tag">{currentTag}</span>
                </div>
              </section>
            )}
          </div>
        </div>
      )}

      {activeTab === "Versions" && (
        <div
          className="editor__panel-stack"
          role="tabpanel"
          id="panel-versions"
          aria-labelledby="tab-versions"
        >
          {!isAuthenticated ? (
            <p className="pb-empty">Sign in to save and compare versions.</p>
          ) : (
            <>
              <div className="editor__panel-grid">
                <SaveVersion
                  promptText={prompt}
                  responseText={results?.[0]?.response_text || null}
                  responseModel={results?.[0]?.model || null}
                  responseLatency={results?.[0]?.latency || null}
                />
                <ExportDropdown versionId={currentVersionId} />
              </div>

              <div className="editor__panel-grid">
                <VersionSelector
                  onSelectVersion={handleSelectVersion}
                  onVersionDeleted={handleVersionDeleted}
                />
                <DiffVersionPicker
                  onCompare={handleCompare}
                  refreshSignal={versionsRefreshSignal}
                />
              </div>

              {versionA && versionB && (
                <DiffView
                  versionA={versionA}
                  versionB={versionB}
                  totalVersions={totalVersions}
                />
              )}
            </>
          )}
        </div>
      )}

      {activeTab === "Results" && (
        <div
          role="tabpanel"
          id="panel-results"
          aria-labelledby="tab-results"
        >
          {results.length === 0 ? (
            <p className="pb-empty">
              No responses yet. Run a prompt from the Write tab.
            </p>
          ) : (
            <ResponseDisplay results={results} />
          )}
        </div>
      )}
    </div>
  );
}
