import { createContext, useContext } from "react";

/**
 * Working state for the prompt workspace.
 *
 * Lifted out of the Editor because the sidebar turns the app into several
 * routes: without this, visiting Community (or any other page) would unmount
 * the Editor and silently discard the user's draft prompt, their selected
 * models, and the provider API keys they had just validated.
 *
 * Deliberately in memory only -- API keys are held here, and they should not
 * outlive the tab or reach storage.
 */
export const WorkspaceContext = createContext(null);

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error("useWorkspace must be used inside a WorkspaceProvider");
  }
  return context;
}
