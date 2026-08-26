import { NavLink } from "react-router-dom";

import { displayNameFor, initialsFor } from "../identity";
import "./AppShell.css";

/* Inline SVGs so the shell has no external asset or icon-font dependency. */
const icons = {
  editor: (
    <path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
  ),
  chains: (
    <>
      <circle cx="6" cy="6" r="3" />
      <circle cx="6" cy="18" r="3" />
      <circle cx="18" cy="12" r="3" />
      <path d="M9 6h3a3 3 0 0 1 3 3v0M9 18h3a3 3 0 0 0 3-3v0" />
    </>
  ),
  cost: (
    <>
      <path d="M4 20V10M10 20V4M16 20v-7M22 20H2" />
    </>
  ),
  community: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3a15 15 0 0 1 0 18a15 15 0 0 1 0-18Z" />
    </>
  ),
  settings: (
    <>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-2.9 1.2v.1a2 2 0 1 1-4 0v-.2a1.7 1.7 0 0 0-3-1.1l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0-1.2-2.9H3a2 2 0 1 1 0-4h.2a1.7 1.7 0 0 0 1.1-3l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 2.9-1.2V3a2 2 0 1 1 4 0v.2a1.7 1.7 0 0 0 3 1.1l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0 1.2 2.9h.1a2 2 0 1 1 0 4h-.2a1.7 1.7 0 0 0-1.5 1Z" />
    </>
  ),
};

function Icon({ name }) {
  return (
    <svg
      className="sidebar__icon"
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {icons[name]}
    </svg>
  );
}

const NAV_GROUPS = [
  {
    label: "Workspace",
    items: [
      { to: "/editor", label: "Editor", icon: "editor" },
      { to: "/chains", label: "Chains", icon: "chains" },
      { to: "/cost-forecast", label: "Cost forecast", icon: "cost" },
    ],
  },
  {
    label: "Discover",
    items: [
      { to: "/community", label: "Community", icon: "community" },
      { to: "/settings", label: "Settings", icon: "settings" },
    ],
  },
];

export default function AppShell({ user, children }) {
  const isGuest = Boolean(user?.isGuest);

  return (
    <div className="shell">
      <aside className="shell__sidebar">
        <div className="sidebar__brand">
          <span className="sidebar__dot" aria-hidden="true" />
          <span className="sidebar__wordmark">PromptBox</span>
        </div>

        <nav className="sidebar__nav" aria-label="Main">
          {NAV_GROUPS.map((group) => (
            <div className="sidebar__group" key={group.label}>
              <p className="sidebar__group-label">{group.label}</p>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    isActive ? "sidebar__link is-active" : "sidebar__link"
                  }
                >
                  <Icon name={item.icon} />
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>

        <div className="sidebar__footer">
          <span className="sidebar__avatar" aria-hidden="true">
            {initialsFor(user)}
          </span>
          <div className="sidebar__identity">
            <div className="sidebar__name">{displayNameFor(user)}</div>
            <div className="sidebar__plan">
              {isGuest ? "Not signed in" : "Free plan"}
            </div>
          </div>
        </div>
      </aside>

      <main className="shell__content">{children}</main>
    </div>
  );
}
