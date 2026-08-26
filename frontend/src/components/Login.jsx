import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { login, register } from "../api/authApi";
import { GUEST_SESSION } from "../session";
import "./Login.css";

function GitHubIcon() {
  return (
    <svg
      className="auth__provider-icon"
      width="18"
      height="18"
      viewBox="0 0 16 16"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M8 0C3.58 0 0 3.58 0 8a8 8 0 0 0 5.47 7.59c.4.07.55-.17.55-.38l-.01-1.34c-2.23.48-2.7-1.07-2.7-1.07-.36-.93-.89-1.18-.89-1.18-.73-.5.05-.49.05-.49.8.06 1.23.83 1.23.83.72 1.23 1.88.87 2.34.67.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.6 7.6 0 0 1 4 0c1.53-1.03 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.28.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48l-.01 2.2c0 .21.15.46.55.38A8 8 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
    </svg>
  );
}

function GoogleIcon() {
  return (
    <svg
      className="auth__provider-icon"
      width="18"
      height="18"
      viewBox="0 0 18 18"
      aria-hidden="true"
    >
      <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62Z" />
      <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18Z" />
      <path fill="#FBBC05" d="M3.97 10.72a5.4 5.4 0 0 1 0-3.44V4.95H.96a9 9 0 0 0 0 8.1l3.01-2.33Z" />
      <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58Z" />
    </svg>
  );
}

const Login = ({ onAuth }) => {
  const navigate = useNavigate();
  const [action, setAction] = useState("Sign Up");
  const [showEmail, setShowEmail] = useState(false);
  const [form, setForm] = useState({ email: "", password: "" });
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [messageKey, setMessageKey] = useState(0);

  const handleChange = (field) => (e) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const extractError = (detail) => {
    if (!detail) return "Request failed";
    if (Array.isArray(detail)) return detail[0]?.msg || "Request failed";
    if (typeof detail === "object") return detail.msg || JSON.stringify(detail);
    return String(detail);
  };

  const showMessage = (msg) => {
    setMessageKey((k) => k + 1);
    setMessage(msg);
  };

  const handleSubmit = async () => {
    // `loading` was previously write-only. Reading it here stops a second
    // click from firing a duplicate register/login request while the first
    // is still in flight.
    if (loading) return;

    if (!form.email.trim()) {
      showMessage("Email is required");
      return;
    }
    if (form.password.length < 8) {
      showMessage("Password must be at least 8 characters");
      return;
    }

    setMessage("");
    setLoading(true);
    try {
      if (action === "Sign Up") {
        // The server deliberately answers the same way whether or not the
        // address was already taken, so show its message rather than asserting
        // an account was created.
        const data = await register(form.email, form.password);
        showMessage(data?.detail || "Registration submitted. You can now sign in.");
        setTimeout(() => setMessage(""), 6000);
      } else {
        // Login sets an httpOnly session cookie. There is no token in the
        // response for us to keep -- the cookie IS the session.
        const data = await login(form.email, form.password);
        onAuth({ email: data?.email ?? form.email });
        navigate("/editor");
      }
    } catch (err) {
      showMessage(extractError(err.message) || "Request failed");
    } finally {
      setLoading(false);
    }
  };

  const handleGuest = () => {
    // An explicit guest marker rather than null: the shell needs to tell
    // "guest" apart from "signed in", and null read as the latter.
    onAuth(GUEST_SESSION);
    navigate("/editor");
  };

  return (
    <div className="auth">
      <div className="auth__card">
        <div className="auth__brand">
          <span className="auth__dot" aria-hidden="true" />
          <span className="auth__wordmark">PromptBox</span>
        </div>
        <p className="auth__subtitle">
          The prompt workspace for AI developers.
          <br />
          Sign in to save, version, and share your prompts.
        </p>

        <div className="auth__providers">
          {/* Disabled: no OAuth provider is configured on the backend. These
              attempt no request -- there is nothing to call yet. */}
          <button
            type="button"
            className="auth__provider"
            disabled
            data-testid="github-btn"
          >
            <GitHubIcon />
            Continue with GitHub
          </button>
          <button
            type="button"
            className="auth__provider"
            disabled
            data-testid="google-btn"
          >
            <GoogleIcon />
            Continue with Google
          </button>
        </div>
        <p className="auth__soon">OAuth coming soon</p>

        <p className="auth__divider">
          <button
            type="button"
            className="auth__toggle"
            onClick={() => setShowEmail((open) => !open)}
            data-testid="email-toggle"
            aria-expanded={showEmail}
          >
            or continue with email
          </button>
        </p>

        {showEmail && (
          <div className="auth__email" data-testid="email-form">
            <input
              type="email"
              className="pb-input"
              placeholder="Email Id"
              value={form.email}
              onChange={handleChange("email")}
            />
            <input
              type="password"
              className="pb-input"
              placeholder="Password"
              value={form.password}
              onChange={handleChange("password")}
            />

            {/* Each button selects its mode on first click and submits on the
                next, which is the interaction this form has always had. */}
            <div className="auth__actions">
              <button
                type="button"
                className={
                  action === "Sign Up"
                    ? "pb-btn pb-btn--primary pb-btn--block"
                    : "pb-btn pb-btn--block"
                }
                onClick={() =>
                  action === "Sign Up" ? handleSubmit() : setAction("Sign Up")
                }
                data-testid="signup-btn"
              >
                Sign Up
              </button>
              <button
                type="button"
                className={
                  action === "Login"
                    ? "pb-btn pb-btn--primary pb-btn--block"
                    : "pb-btn pb-btn--block"
                }
                onClick={() =>
                  action === "Login" ? handleSubmit() : setAction("Login")
                }
                data-testid="login-btn"
              >
                Login
              </button>
            </div>
          </div>
        )}

        {message && (
          <div className="auth__message" key={messageKey}>
            {message}
          </div>
        )}

        <div className="auth__guest">
          <button
            type="button"
            className="auth__toggle"
            onClick={handleGuest}
            data-testid="guest-btn"
          >
            Continue as guest
          </button>
        </div>
      </div>
    </div>
  );
};

export default Login;
