import { useState } from "react";
import ModelSelector from "../components/ModelSelector";
import PromptEditor from "../components/PromptEditor";
import ResponseDisplay from "../components/ResponseDisplay";
import SaveVersion from "../components/SaveVersion";
import VersionSelector from "../components/VersionSelector";
import DiffVersionPicker from "../components/DiffVerisonPicker";
import DiffView from "../components/DiffView";
import ExportDropdown from "../components/ExportDropdown";
import TemplateLibrary from '../components/TemplateLibrary'

export default function DashBoard({ user, onLogout }) {
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
        {user && (
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <span style={{ fontSize: "0.9rem" }}>Signed in as {user.email}</span>
            <button onClick={onLogout}>Log out</button>
          </div>
        )}
      </header>

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

      {user && (
        <SaveVersion
          token={user.token}
          promptText={prompt}
          responseText={results?.[0]?.response_text || null}
          responseModel={results?.[0]?.model || null}
          responseLatency={results?.[0]?.latency || null}
        />
      )}
      {user && (
        <ExportDropdown token={user.token} versionId={currentVersionId} />
      )}

      <aside>
        {user && (
          <VersionSelector
            token={user.token}
            onSelectVersion={handleSelectVersion}
            onVersionDeleted={handleVersionDeleted}
          />
        )}
        {user && (
          <DiffVersionPicker
            token={user.token}
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
