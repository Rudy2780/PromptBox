/**
 * Session-scoped persistence for the prompt workspace.
 *
 * WorkspaceProvider is memory-only by design, which also meant a refresh threw
 * away whatever the user had in flight. This module writes back the part of
 * that state which is safe to write down.
 *
 * sessionStorage, not localStorage: the draft should survive F5 and die with
 * the tab. localStorage would leave a user's prompts sitting on disk until
 * something explicitly cleared them.
 *
 * What gets persisted is an explicit allowlist rather than "everything except
 * the secrets". Provider API keys live in the same context object, so a field
 * added to the workspace later must not start being written to storage merely
 * because nobody remembered to exclude it.
 *
 * Deliberately never persisted:
 *   - `apiKeys` -- the secrets, and the reason the provider was memory-only.
 *   - `isKeyValid` -- only meaningful alongside the key it was checked against.
 *     Restoring it without the key would leave "Run prompt" enabled with
 *     nothing to run with, so validation starts over on every load.
 */

export const STORAGE_KEY = "promptbox.workspace.v1";

/** Editor tab names. Mirrors TABS in pages/Editor.jsx. */
export const TABS = ["Write", "Versions", "Results"];

/**
 * A fresh copy of the state a first-time visitor gets.
 * A function, not a frozen constant, so callers cannot share (and mutate) the
 * nested array and object across provider instances.
 * @returns {Object} Default workspace state.
 */
export function defaultWorkspaceState() {
  return {
    prompt: "",
    selectedModels: ["gpt-4o"],
    activeTab: "Write",
    results: [],
    currentVersionId: null,
    currentTag: null,
    versionDraft: { name: "", tag: "" },
  };
}

/**
 * sessionStorage, or null when it is unavailable.
 * Access itself throws in some privacy modes, so even reading the property
 * needs guarding.
 * @returns {Storage|null}
 */
function storage() {
  try {
    return globalThis.sessionStorage ?? null;
  } catch {
    return null;
  }
}

const isString = (value) => typeof value === "string";

/** A persisted result is only useful if ResponseDisplay can key and render it. */
function isResult(value) {
  return Boolean(value) && typeof value === "object" && isString(value.model);
}

/**
 * Read persisted workspace state back out of sessionStorage.
 *
 * Every field is validated against its expected type before use: the payload is
 * editable by anyone with devtools open, and a hand-mangled value should give a
 * clean workspace rather than crash the editor on first render.
 *
 * @returns {Object} Restored state, with defaults filling any missing or
 *   malformed field. Never throws.
 */
export function loadWorkspaceState() {
  const defaults = defaultWorkspaceState();
  const store = storage();
  if (!store) return defaults;

  let raw;
  try {
    raw = store.getItem(STORAGE_KEY);
  } catch {
    return defaults;
  }
  if (!raw) return defaults;

  let saved;
  try {
    saved = JSON.parse(raw);
  } catch {
    clearWorkspaceState();
    return defaults;
  }
  if (!saved || typeof saved !== "object" || Array.isArray(saved)) {
    clearWorkspaceState();
    return defaults;
  }

  const models = Array.isArray(saved.selectedModels)
    ? saved.selectedModels.filter(isString)
    : [];
  const draft = saved.versionDraft;

  return {
    prompt: isString(saved.prompt) ? saved.prompt : defaults.prompt,
    // ModelSelector keeps at least one model selected; an empty restore would
    // put the UI in a state it cannot reach on its own.
    selectedModels: models.length ? models : defaults.selectedModels,
    activeTab: TABS.includes(saved.activeTab) ? saved.activeTab : defaults.activeTab,
    results: Array.isArray(saved.results) ? saved.results.filter(isResult) : defaults.results,
    currentVersionId:
      typeof saved.currentVersionId === "number" ? saved.currentVersionId : null,
    currentTag: isString(saved.currentTag) ? saved.currentTag : null,
    versionDraft: {
      name: isString(draft?.name) ? draft.name : "",
      tag: isString(draft?.tag) ? draft.tag : "",
    },
  };
}

/**
 * Write the allowlisted slice of workspace state to sessionStorage.
 *
 * Persistence is a convenience, so every failure is swallowed -- a full quota
 * or disabled storage must never take the editor down with it.
 *
 * @param {Object} state - Current workspace state; extra fields are ignored.
 * @returns {boolean} Whether anything was stored.
 */
export function saveWorkspaceState(state) {
  const store = storage();
  if (!store) return false;

  const payload = {
    prompt: state.prompt,
    selectedModels: state.selectedModels,
    activeTab: state.activeTab,
    results: state.results,
    currentVersionId: state.currentVersionId,
    currentTag: state.currentTag,
    versionDraft: state.versionDraft,
  };

  try {
    store.setItem(STORAGE_KEY, JSON.stringify(payload));
    return true;
  } catch {
    // Most likely the quota: model responses are the only unbounded field here,
    // and a few long ones can fill it. Drop them and keep the draft prompt,
    // which is the part the user cannot get back by re-running.
    try {
      store.setItem(STORAGE_KEY, JSON.stringify({ ...payload, results: [] }));
      return true;
    } catch {
      return false;
    }
  }
}

/** Remove the persisted workspace. Never throws. */
export function clearWorkspaceState() {
  const store = storage();
  if (!store) return;
  try {
    store.removeItem(STORAGE_KEY);
  } catch {
    // Nothing useful to do -- the caller only wanted the data gone.
  }
}
