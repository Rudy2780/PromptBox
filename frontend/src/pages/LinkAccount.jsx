import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getPendingLink, confirmLink, cancelLink } from "../api/oauthApi";
import { authErrorMessage, RETRYABLE_ERRORS } from "../oauthErrors";
import "../components/Login.css";

const PROVIDER_NAMES = { google: "Google", github: "GitHub" };

/**
 * The confirmation step for linking a provider to an existing password
 * account.
 *
 * Reached only by redirect from the API callback, and only when a provider
 * login matched an address that already has a password. At this point nothing
 * has been written and there is no session: the sign-in is parked in an
 * httpOnly cookie, and proving the password is what releases it. That is why
 * this page asks rather than the backend just linking — a verified email shows
 * the person controls the mailbox today, which is not the same as showing they
 * own this account.
 */
const LinkAccount = ({ onAuth }) => {
  const navigate = useNavigate();
  // undefined = still loading, null = nothing pending, object = ready to ask.
  const [pending, setPending] = useState(undefined);
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  // Terminal failures go back to the sign-in screen carrying the same code the
  // API's own redirects use, so the user reads the identical sentence however
  // the failure arrived.
  function abandon(code) {
    navigate(`/login?auth_error=${encodeURIComponent(code)}`, { replace: true });
  }

  useEffect(() => {
    let cancelled = false;

    getPendingLink()
      .then((data) => {
        if (!cancelled) setPending(data);
      })
      .catch((err) => {
        if (!cancelled) abandon(err.authError || "link_expired");
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleConfirm() {
    if (busy || !password) return;

    setBusy(true);
    setMessage("");
    try {
      const data = await confirmLink(password);
      // The API set the ordinary session cookie; the page cannot read it, so
      // the email it returns is what seeds local sign-in state.
      onAuth({ email: data?.email ?? pending?.email });
      navigate("/editor", { replace: true });
    } catch (err) {
      const code = err.authError;
      if (code && !RETRYABLE_ERRORS.has(code)) {
        // Expired or otherwise spent: there is nothing left here to retry.
        abandon(code);
        return;
      }
      setPassword("");
      setMessage(authErrorMessage(code) || err.message || "Could not confirm");
    } finally {
      setBusy(false);
    }
  }

  async function handleCancel() {
    // `catch`, not `finally`: a bare try/finally re-throws, which leaves an
    // unhandled rejection floating whenever the request fails. Swallowing it
    // is the right call here -- the pending link expires on its own, and
    // staying on this page after the user asked to leave would be worse than
    // a cookie that lapses in ten minutes.
    try {
      await cancelLink();
    } catch {
      // Nothing to report: the user is leaving either way.
    }
    navigate("/", { replace: true });
  }

  if (pending === undefined) {
    return (
      <div className="auth">
        <div className="auth__card" data-testid="link-loading">
          Loading…
        </div>
      </div>
    );
  }

  const providerName = PROVIDER_NAMES[pending.provider] || pending.provider;

  return (
    <div className="auth">
      <div className="auth__card">
        <div className="auth__brand">
          <span className="auth__dot" aria-hidden="true" />
          <span className="auth__wordmark">PromptBox</span>
        </div>

        <p className="auth__subtitle" data-testid="link-explainer">
          An account already exists for <strong>{pending.email}</strong>.
          <br />
          Enter its password to add {providerName} sign-in to it.
        </p>

        <div className="auth__email">
          <input
            type="password"
            className="pb-input"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleConfirm()}
            data-testid="link-password"
          />

          <div className="auth__actions">
            <button
              type="button"
              className="pb-btn pb-btn--primary pb-btn--block"
              onClick={handleConfirm}
              disabled={busy}
              data-testid="link-confirm"
            >
              {busy ? "Confirming…" : `Link ${providerName}`}
            </button>
          </div>
        </div>

        {message && (
          <div className="auth__message" data-testid="link-error">
            {message}
          </div>
        )}

        <div className="auth__guest">
          <button
            type="button"
            className="auth__toggle"
            onClick={handleCancel}
            data-testid="link-cancel"
          >
            Cancel and go back
          </button>
        </div>
      </div>
    </div>
  );
};

export default LinkAccount;
