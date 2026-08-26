/**
 * Display identity derived from an account.
 *
 * The backend stores an email and a password hash -- there is no name column --
 * so the local part of the address is title-cased rather than inventing a
 * profile field.
 */

export function displayNameFor(user) {
  if (!user || user.isGuest) return "Guest";
  const local = String(user.email || "").split("@")[0];
  if (!local) return "Account";
  return local
    .split(/[._-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function initialsFor(user) {
  const name = displayNameFor(user);
  const parts = name.split(" ").filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}
