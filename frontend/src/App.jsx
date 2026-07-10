import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Login from "./components/Login";
import "./App.css";

function App() {
  const [user, setUser] = useState(undefined);

  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/"
          element={user !== undefined ? <Navigate to="/dashboard" replace /> : <Login onAuth={setUser} />}
        />
        <Route
          path="/dashboard"
          element={user !== undefined ? <Dashboard user={user} onLogout={() => setUser(undefined)} /> : <Navigate to="/" replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
