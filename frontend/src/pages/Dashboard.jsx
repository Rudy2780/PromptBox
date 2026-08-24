import { useState } from "react";
import ModelSelector from "../components/ModelSelector";
import PromptEditor from "../components/PromptEditor";
import ResponseDisplay from "../components/ResponseDisplay";
import SaveVersion from "../components/SaveVersion";
import VersionSelector from "../components/VersionSelector";
import DiffVersionPicker from "../components/DiffVersionPicker";
import DiffView from "../components/DiffView";
import ExportDropdown from "../components/ExportDropdown";
import TemplateLibrary from '../components/TemplateLibrary'

export default function Dashboard({ user, onLogout }) {
  // A guest has no session, so every authenticated call would 401. Rather than
  // rendering panels that silently fail (or, as before, vanish with no
  // explanation), guests get the one thing that genuinely works unauthenticated
  // -- the template library -- and a clear prompt to sign in.
  const isGuest = Boolean(user?.isGuest);
  const isAuthenticated = Boolean(user) && !isGuest;

  const [selectedModels, setSelectedModels] = useState(["gpt-4o"]);
  const [apiKeys, setApiKeys] = useState({ openai: "", gemini: "", anthropic: "" });
  const [isKeyValid, setIsKeyValid] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [results, setResults] = useState([]);
  const [error, setError] = useState(null);
  const [versionA, setVersionA] = useState(null);
  const [versionB, setVersionB] = useState(null);
  const [totalVersions, setTotalVersions] = useState(0);
  const [currentVersionId, setCurrentVersionId] = useState(null);
  const [versionsRefreshSignal, setVersionsRefreshSignal] = useState(0);

  const handleSelectVersion = (version) => {
    setCurrentVersionId(version.id);
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

  function handleSelectTemplate(content) {
  setPrompt(content)
}

  function handleVersionDeleted(deletedVersionId) {
    setVersionsRefreshSignal((prev) => prev + 1);
    if (currentVersionId === deletedVersionId) {
      setCurrentVersionId(null);
    }
  }

  return (
    <div className="app">
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1>PromptBox Dashboard</h1>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span style={{ fontSize: "0.9rem" }}>
            {isAuthenticated ? `Signed in as ${user.email}` : "Browsing as guest"}
          </span>
          <button onClick={onLogout}>{isAuthenticated ? "Log out" : "Sign in"}</button>
        </div>
      </header>

      {isGuest && (
        <p className="guest-notice" data-testid="guest-notice">
          You are browsing as a guest. Running prompts, saving versions and
          exporting all require an account -- sign in to enable them.
        </p>
      )}

      <main>
        <ModelSelector
          selectedModels={selectedModels}
          setSelectedModels={setSelectedModels}
          apiKeys={apiKeys}
          setApiKeys={setApiKeys}
          onValidated={setIsKeyValid}
        />

        <PromptEditor
          models={selectedModels}
          apiKey={apiKeys}
          isKeyValid={isKeyValid}
          onResults={setResults}
          onError={setError}
          prompt={prompt}
          setPrompt={setPrompt}
        />
      </main>

      <ResponseDisplay results={results} />

      {isAuthenticated && (
        <SaveVersion
          promptText={prompt}
          responseText={results?.[0]?.response_text || null}
          responseModel={results?.[0]?.model || null}
          responseLatency={results?.[0]?.latency || null}
        />
      )}
      {isAuthenticated && (
        <ExportDropdown versionId={currentVersionId} />
      )}

      <aside>
        {isAuthenticated && (
          <VersionSelector
            onSelectVersion={handleSelectVersion}
            onVersionDeleted={handleVersionDeleted}
          />
        )}
        {isAuthenticated && (
          <DiffVersionPicker
            onCompare={handleCompare}
            refreshSignal={versionsRefreshSignal}
          />
        )}
            <TemplateLibrary                          
              onSelectTemplate={handleSelectTemplate}
              currentPrompt={prompt}
          />
      </aside>
      {error && <p style={{ color: "red" }}>{error}</p>}

      

      {versionA && versionB && (
        <DiffView versionA={versionA} versionB={versionB} totalVersions={totalVersions} />
      )}


    </div>
  );
}
