import { createContext, useContext } from "react";

/**
 * Working state for the prompt workspace.
 *
 * Lifted out of the Editor because the sidebar turns the app into several
 * routes: without this, visiting Community (or any other page) would unmount
 * the Editor and silently discard the user's draft prompt, their selected
 * models, and the provider API keys they had just validated.
 *
 * The non-sensitive half of this state is mirrored to sessionStorage so a
 * refresh does not discard it either -- see workspaceStorage.js for what is
 * written and why the API keys and their validation status are not.
 */
export const WorkspaceContext = createContext(null);

export function useWorkspace() {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error("useWorkspace must be used inside a WorkspaceProvider");
  }
  return context;
}
