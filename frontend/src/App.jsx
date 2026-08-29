import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Analytics } from "@vercel/analytics/react";

import AppShell from "./components/AppShell";
import Login from "./components/Login";
import Editor from "./pages/Editor";
import Chains from "./pages/Chains";
import CostForecast from "./pages/CostForecast";
import Community from "./pages/Community";
import Settings from "./pages/Settings";
import { WorkspaceProvider } from "./workspace";
import { clearWorkspaceState } from "./workspaceStorage";
import { getMe, logout } from "./api/authApi";
import "./theme.css";
import "./App.css";

function App() {
  // undefined = still restoring, null = signed out, object = active session.
  // The distinction matters: rendering the login screen before the session
  // check finishes would flash the login form at users who are already signed in.
  const [session, setSession] = useState(undefined);

  // Bumped on sign-out to remount the workspace provider. The workspace now
  // outlives a refresh, which also means the previous user's draft prompt would
  // otherwise still be sitting there for whoever signs in next on this machine.
  const [workspaceEpoch, setWorkspaceEpoch] = useState(0);

  useEffect(() => {
    let cancelled = false;

    // The session cookie is httpOnly, so the page cannot read it. Asking the
    // server who we are is the only way to restore sign-in state on load --
    // and it is what makes a refresh no longer log the user out.
    getMe()
      .then((user) => {
        if (!cancelled) setSession(user ?? null);
      })
      .catch(() => {
        if (!cancelled) setSession(null);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  async function handleLogout() {
    try {
      // Real logout: only the server can clear an httpOnly cookie.
      await logout();
    } finally {
      // Drop local state even if the request failed, so the UI never claims
      // to be signed in when the user asked to leave. The stored copy goes
      // first, so the remount below reads an empty slate rather than restoring
      // what was just discarded.
      clearWorkspaceState();
      setWorkspaceEpoch((epoch) => epoch + 1);
      setSession(null);
    }
  }

  if (session === undefined) {
    return (
      <div className="app-loading" data-testid="session-loading">
        Loading…
      </div>
    );
  }

  // Every signed-in route renders inside the sidebar shell.
  const shell = (page) =>
    session ? (
      <AppShell user={session}>{page}</AppShell>
    ) : (
      <Navigate to="/" replace />
    );

  return (
    <WorkspaceProvider key={workspaceEpoch}>
      <BrowserRouter>
        <Routes>
          <Route
            path="/"
            element={
              session ? <Navigate to="/editor" replace /> : <Login onAuth={setSession} />
            }
          />
          <Route path="/editor" element={shell(<Editor user={session} />)} />
          <Route path="/chains" element={shell(<Chains />)} />
          <Route path="/cost-forecast" element={shell(<CostForecast />)} />
          <Route path="/community" element={shell(<Community />)} />
          <Route
            path="/settings"
            element={shell(<Settings user={session} onLogout={handleLogout} />)}
          />
          {/* Kept so existing links and bookmarks continue to resolve. */}
          <Route path="/dashboard" element={<Navigate to="/editor" replace />} />
          <Route path="*" element={<Navigate to={session ? "/editor" : "/"} replace />} />
        </Routes>
      </BrowserRouter>
      <Analytics />
    </WorkspaceProvider>
  );
}

export default App;
