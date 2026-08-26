import { useNavigate } from "react-router-dom";

/*
 * Account settings.
 *
 * The backend stores an email and a password hash and nothing else, so this
 * shows exactly that plus the sign-out action. No preferences, plans or
 * profile fields are invented.
 */
export default function Settings({ user, onLogout }) {
  const navigate = useNavigate();
  const isGuest = Boolean(user?.isGuest);

  return (
    <div className="settings">
      <h1 className="pb-page-title">Settings</h1>
      <p className="pb-page-lede">Account details for this session.</p>

      <div className="pb-card" style={{ maxWidth: 520 }}>
        {isGuest ? (
          <div className="pb-stack">
            <div>
              <span className="pb-label">Account</span>
              <p className="pb-empty">
                You are browsing as a guest. Sign in to save versions, export,
                and run prompts.
              </p>
            </div>
            <button
              type="button"
              className="pb-btn pb-btn--primary"
              onClick={() => navigate("/")}
            >
              Sign in
            </button>
          </div>
        ) : (
          <div className="pb-stack">
            <div>
              <span className="pb-label">Signed in as</span>
              <p style={{ margin: 0 }}>{user?.email}</p>
            </div>
            <button type="button" className="pb-btn" onClick={onLogout}>
              Log out
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
