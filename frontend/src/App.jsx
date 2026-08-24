import { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Login from "./components/Login";
import { getMe, logout } from "./api/authApi";
import "./App.css";

function App() {
  // undefined = still restoring, null = signed out, object = active session.
  // The distinction matters: rendering the login screen before the session
  // check finishes would flash the login form at users who are already signed in.
  const [session, setSession] = useState(undefined);

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
      // to be signed in when the user asked to leave.
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

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={session ? <Navigate to="/dashboard" replace /> : <Login onAuth={setSession} />}
        />
        <Route
          path="/dashboard"
          element={session ? <Dashboard user={session} onLogout={handleLogout} /> : <Navigate to="/" replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
