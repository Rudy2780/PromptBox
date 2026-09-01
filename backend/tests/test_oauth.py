"""Google and GitHub sign-in.

Nothing here talks to Google or GitHub. Every outbound call is served by an
``httpx.MockTransport`` injected at ``oauth_service._http_client``, which is
the one seam the service makes those calls through. That is deliberately a
transport-level fake rather than a stubbed-out function: the URLs, form bodies
and Authorization headers the service builds are all exercised for real, and a
test fails if the service starts calling an endpoint it was not meant to.

Credentials come from the fake values pinned in conftest, and
``OAUTH_REDIRECT_BASE_URL`` is pinned there too, so the redirect_uri asserted
on below is fixed rather than derived from the test client's host.

Note the shape of a failure: the provider legs are browser navigations, so
they answer with a 302 back to the SPA carrying an ``auth_error`` slug, never
with a JSON error body. ``assert_auth_error`` is the assertion for that.
"""

from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from app.config import settings
from app.models.oauth_identity import OAuthIdentity
from app.models.user import UserInfo
from app.services import oauth_service
from app.utils.security import hash_password

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"

EXPECTED_REDIRECT_URI = {
    "google": "https://api.test/auth/callback/google",
    "github": "https://api.test/auth/callback/github",
}

CSRF = {"X-Requested-With": "PromptBox"}


class FakeProvider:
    """A stand-in for one provider's HTTP endpoints.

    Records every request it serves so tests can assert on what was sent --
    including that the client secret went to the token endpoint and nowhere
    else.
    """

    def __init__(self, responses):
        self.responses = responses
        self.requests = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        url = str(request.url).split("?")[0]
        self.requests.append(request)
        if url not in self.responses:
            raise AssertionError(f"unexpected outbound request to {url}")
        status, payload = self.responses[url]
        return httpx.Response(status, json=payload)

    def body_for(self, url):
        for request in self.requests:
            if str(request.url).split("?")[0] == url:
                return parse_qs(request.content.decode())
        raise AssertionError(f"no request was made to {url}")


@pytest.fixture
def provider_api(monkeypatch):
    """Install a fake provider API and hand the test its recorder."""

    def _install(responses):
        fake = FakeProvider(responses)
        transport = httpx.MockTransport(fake.handle)
        monkeypatch.setattr(
            oauth_service, "_http_client", lambda: httpx.Client(transport=transport)
        )
        return fake

    return _install


def google_api(email="ada@example.com", sub="google-sub-1", email_verified=True):
    return {
        GOOGLE_TOKEN_URL: (200, {"access_token": "google-access-token"}),
        GOOGLE_USERINFO_URL: (
            200,
            {"sub": sub, "email": email, "email_verified": email_verified},
        ),
    }


def github_api(emails=None, user_id="github-id-1", profile_email=None):
    if emails is None:
        emails = [{"email": "ada@example.com", "primary": True, "verified": True}]
    return {
        GITHUB_TOKEN_URL: (200, {"access_token": "github-access-token"}),
        GITHUB_USER_URL: (200, {"id": user_id, "login": "ada", "email": profile_email}),
        GITHUB_EMAILS_URL: (200, emails),
    }


def begin_login(client, provider):
    """Run the first leg and return the ``state`` sent to the provider.

    The state cookie lands in the client's jar here, which is what makes the
    callback below a faithful replay of what a browser does.
    """
    res = client.get(f"/auth/{provider}/login", follow_redirects=False)
    assert res.status_code == 302, res.text
    query = parse_qs(urlparse(res.headers["location"]).query)
    return query["state"][0]


def complete_login(client, provider, code="auth-code"):
    state = begin_login(client, provider)
    return client.get(
        f"/auth/callback/{provider}",
        params={"code": code, "state": state},
        follow_redirects=False,
    )


def assert_auth_error(response, code):
    """A failed provider leg is a redirect to the SPA, not a JSON error."""
    assert response.status_code == 302, response.text
    location = urlparse(response.headers["location"])

    assert f"{location.scheme}://{location.netloc}" == settings.FRONTEND_URL
    assert location.path == "/login"
    assert parse_qs(location.query)["auth_error"] == [code]

    # Nothing but the slug: no detail text, no provider wording, no email.
    assert set(parse_qs(location.query)) == {"auth_error"}


def assert_redirected_to(response, path):
    assert response.status_code == 302, response.text
    location = urlparse(response.headers["location"])
    assert f"{location.scheme}://{location.netloc}" == settings.FRONTEND_URL
    assert location.path == path


def register(client, email="ada@example.com", password="password123"):
    res = client.post("/auth/register", json={"email": email, "password": password})
    assert res.status_code == 201, res.text


# --- the consent-screen redirect -------------------------------------------


def test_google_login_redirects_to_the_consent_screen(client):
    res = client.get("/auth/google/login", follow_redirects=False)

    assert res.status_code == 302
    location = urlparse(res.headers["location"])
    assert f"{location.scheme}://{location.netloc}{location.path}" == (
        "https://accounts.google.com/o/oauth2/v2/auth"
    )

    query = parse_qs(location.query)
    assert query["client_id"] == ["test-google-client-id"]
    assert query["response_type"] == ["code"]
    assert query["redirect_uri"] == [EXPECTED_REDIRECT_URI["google"]]
    assert query["state"][0]


def test_github_login_requests_the_user_email_scope(client):
    res = client.get("/auth/github/login", follow_redirects=False)

    assert res.status_code == 302
    query = parse_qs(urlparse(res.headers["location"]).query)
    # Without user:email the /user/emails call is refused and there is no
    # verified address to link on -- so the scope is load-bearing, not decor.
    assert query["scope"] == ["user:email"]
    assert query["redirect_uri"] == [EXPECTED_REDIRECT_URI["github"]]


# --- scope: the parameter that decides whether /user/emails is readable -----
#
# A token granted without user:email cannot read /user/emails, GitHub answers
# 403, and the login fails at the point where it looks for a verified address.
# The failure is downstream and looks nothing like its cause, so the scope is
# pinned here from several directions.


def test_github_authorization_url_carries_the_scope(client):
    """The whole point: the parameter is on the URL the browser is sent to."""
    res = client.get("/auth/github/login", follow_redirects=False)
    location = res.headers["location"]

    # Present at all, and present *encoded* -- the colon in "user:email" has to
    # survive urlencode, and a raw colon here would be a different request.
    assert "scope=user%3Aemail" in location

    # And decodes back to exactly the scope GitHub needs.
    query = parse_qs(urlparse(location).query)
    assert query["scope"] == ["user:email"]
    assert query["scope"][0].strip() != ""


def test_github_scope_is_not_silently_empty():
    """An empty or missing scope must fail here rather than at /user/emails."""
    github = oauth_service.PROVIDERS["github"]

    assert github.scope, "GitHub provider has no scope configured"
    assert "user:email" in github.scope.split()


def test_authorization_url_includes_scope_for_every_provider():
    """The builder, directly -- one level below the route.

    ``authorization_url`` assembles the query for both providers from the same
    dict, so a regression that drops ``scope`` would silently affect both.
    """
    for name, provider in oauth_service.PROVIDERS.items():
        url = oauth_service.authorization_url(
            provider, f"https://api.test/auth/callback/{name}", "state-value"
        )
        query = parse_qs(urlparse(url).query)

        assert "scope" in query, f"{name} authorization URL has no scope parameter"
        assert query["scope"][0].strip(), f"{name} authorization URL has an empty scope"
        assert query["state"] == ["state-value"]
        assert query["client_id"] == [provider.client_id]


def test_google_scope_is_unaffected_and_independent(client):
    """Google's scope is its own value, set on its own provider entry.

    Confirming the two do not share a source: a change to GitHub's scope must
    not move Google's, and vice versa.
    """
    res = client.get("/auth/google/login", follow_redirects=False)
    query = parse_qs(urlparse(res.headers["location"]).query)

    # Space-delimited OIDC scopes, which is a different vocabulary from
    # GitHub's -- same query parameter, different values.
    assert query["scope"] == ["openid email profile"]
    assert set(query["scope"][0].split()) == {"openid", "email", "profile"}

    assert oauth_service.PROVIDERS["google"].scope != oauth_service.PROVIDERS["github"].scope


def test_the_two_providers_do_not_share_scope_state():
    google = oauth_service.PROVIDERS["google"]
    github = oauth_service.PROVIDERS["github"]

    assert "user:email" not in google.scope
    assert "openid" not in github.scope


def test_login_sets_an_httponly_state_cookie(client):
    res = client.get("/auth/google/login", follow_redirects=False)

    header = res.headers["set-cookie"]
    assert settings.OAUTH_STATE_COOKIE_NAME in header
    assert "HttpOnly" in header
    assert "samesite=lax" in header.lower()


def test_unknown_provider_redirects_rather_than_serving_json(client):
    res = client.get("/auth/myspace/login", follow_redirects=False)
    assert_auth_error(res, "provider_unavailable")


def test_an_unconfigured_provider_redirects_too(client, monkeypatch):
    """A deployment with no GitHub credentials must say so, not half-start.

    conftest pins credentials for both providers, so this removes GitHub's for
    the length of the test rather than asserting on whatever the machine's
    environment happens to hold.
    """
    import dataclasses

    unconfigured = dataclasses.replace(
        oauth_service.PROVIDERS["github"], client_id=None, client_secret=None
    )
    monkeypatch.setitem(oauth_service.PROVIDERS, "github", unconfigured)

    assert_auth_error(
        client.get("/auth/github/login", follow_redirects=False), "provider_unavailable"
    )
    # Google is untouched.
    assert client.get("/auth/google/login", follow_redirects=False).status_code == 302


# --- account creation and repeat sign-in -----------------------------------


def test_new_user_is_created_on_first_oauth_login(client, db_session, provider_api):
    provider_api(google_api(email="newcomer@example.com", sub="google-sub-new"))

    res = complete_login(client, "google")

    assert res.status_code == 302
    assert res.headers["location"] == settings.FRONTEND_URL

    user = db_session.query(UserInfo).filter(UserInfo.email == "newcomer@example.com").one()
    # No password, and specifically NULL rather than an empty string: there is
    # nothing to verify a password attempt against.
    assert user.hashed_password is None

    identity = db_session.query(OAuthIdentity).one()
    assert (identity.provider, identity.provider_user_id) == ("google", "google-sub-new")
    assert identity.user_id == user.id


def test_oauth_login_issues_the_same_session_cookie_as_password_login(
    client, provider_api
):
    provider_api(google_api(email="ada@example.com"))

    complete_login(client, "google")

    # The proof the session is the ordinary one: /auth/me accepts it.
    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "ada@example.com"
    assert settings.SESSION_COOKIE_NAME in client.cookies


def test_second_login_reuses_the_linked_identity(client, db_session, provider_api):
    provider_api(google_api(email="ada@example.com", sub="google-sub-ada"))

    first = complete_login(client, "google")
    assert first.status_code == 302
    user_id = db_session.query(UserInfo).one().id

    second = complete_login(client, "google")
    assert second.status_code == 302

    # Nothing new was created the second time round.
    assert db_session.query(UserInfo).count() == 1
    assert db_session.query(UserInfo).one().id == user_id
    assert db_session.query(OAuthIdentity).count() == 1


def test_identity_is_matched_by_provider_id_not_email(client, db_session, provider_api):
    """A user who changes their email at the provider keeps their account."""
    provider_api(google_api(email="ada@example.com", sub="stable-sub"))
    complete_login(client, "google")
    user_id = db_session.query(UserInfo).one().id

    provider_api(google_api(email="ada-new@example.com", sub="stable-sub"))
    assert complete_login(client, "google").status_code == 302

    assert db_session.query(UserInfo).count() == 1
    assert db_session.query(UserInfo).one().id == user_id


# --- auto-linking: the passwordless case -----------------------------------


def test_two_oauth_providers_auto_link_to_one_account(client, db_session, provider_api):
    """The safe case, linked without asking for anything.

    The account Google created has no password, so there is no credential for
    the GitHub identity to gain access *around* -- both providers have
    independently vouched for the same verified address, and joining them adds
    no authority that was not already there.
    """
    provider_api(google_api(email="ada@example.com", sub="google-sub-ada"))
    assert complete_login(client, "google").status_code == 302
    assert db_session.query(UserInfo).one().hashed_password is None

    provider_api(github_api(emails=[{"email": "ada@example.com", "primary": True, "verified": True}]))
    res = complete_login(client, "github")

    # Straight to the app: no confirmation step.
    assert res.headers["location"] == settings.FRONTEND_URL
    assert db_session.query(UserInfo).count() == 1
    assert {i.provider for i in db_session.query(OAuthIdentity).all()} == {"google", "github"}


def test_auto_link_signs_the_user_in_immediately(client, provider_api):
    provider_api(google_api(email="ada@example.com", sub="google-sub-ada"))
    complete_login(client, "google")
    client.cookies.clear()

    provider_api(github_api())
    complete_login(client, "github")

    assert client.get("/auth/me").json()["email"] == "ada@example.com"


# --- linking to a password-protected account: confirmation required --------


def test_matching_a_password_account_does_not_link_or_sign_in(
    client, db_session, provider_api
):
    register(client, "ada@example.com")
    client.cookies.clear()

    provider_api(google_api(email="ada@example.com", sub="google-sub-ada"))
    res = complete_login(client, "google")

    # Parked at the confirmation step, not signed in.
    assert_redirected_to(res, "/link-account")
    assert settings.SESSION_COOKIE_NAME not in client.cookies
    assert client.get("/auth/me").status_code == 401

    # And crucially: nothing was written.
    assert db_session.query(OAuthIdentity).count() == 0
    assert db_session.query(UserInfo).count() == 1


def test_the_pending_link_is_described_without_putting_it_in_a_url(
    client, provider_api
):
    register(client, "ada@example.com")
    client.cookies.clear()

    provider_api(google_api(email="ada@example.com", sub="google-sub-ada"))
    res = complete_login(client, "google")

    # The redirect carries no token, no email, no provider -- only a path. The
    # SPA asks for those over a normal request, using the httpOnly cookie.
    assert urlparse(res.headers["location"]).query == ""
    assert settings.OAUTH_LINK_COOKIE_NAME in client.cookies

    pending = client.get("/auth/link/pending")
    assert pending.status_code == 200
    assert pending.json() == {"provider": "google", "email": "ada@example.com"}


def test_the_link_cookie_is_httponly_and_cross_site_capable(client, provider_api):
    register(client, "ada@example.com")
    client.cookies.clear()
    provider_api(google_api(email="ada@example.com"))

    res = complete_login(client, "google")

    header = next(
        value
        for key, value in res.headers.items()
        if key.lower() == "set-cookie" and settings.OAUTH_LINK_COOKIE_NAME in value
    )
    assert "HttpOnly" in header
    # SameSite=None, unlike the state cookie: the SPA confirms over a
    # cross-site fetch(), which Lax would not carry.
    assert "samesite=none" in header.lower()
    assert "Secure" in header


def test_the_correct_password_completes_the_link(client, db_session, provider_api):
    register(client, "ada@example.com", "password123")
    original = db_session.query(UserInfo).one()
    original_hash = original.hashed_password
    client.cookies.clear()

    provider_api(google_api(email="ada@example.com", sub="google-sub-ada"))
    complete_login(client, "google")

    res = client.post(
        "/auth/link/confirm", json={"password": "password123"}, headers=CSRF
    )

    assert res.status_code == 200
    assert res.json()["email"] == "ada@example.com"

    # Now linked, to the account that already existed -- not to a new one.
    db_session.expire_all()
    assert db_session.query(UserInfo).count() == 1
    identity = db_session.query(OAuthIdentity).one()
    assert identity.user_id == original.id
    assert identity.provider_user_id == "google-sub-ada"

    # The password is untouched: linking adds a way in, it does not replace one.
    assert db_session.query(UserInfo).one().hashed_password == original_hash

    # And a real session was issued, by the ordinary mechanism.
    assert settings.SESSION_COOKIE_NAME in client.cookies
    assert client.get("/auth/me").json()["email"] == "ada@example.com"
    # The pending link is spent.
    assert settings.OAUTH_LINK_COOKIE_NAME not in client.cookies


def test_a_wrong_password_links_nothing_and_opens_no_session(
    client, db_session, provider_api
):
    register(client, "ada@example.com", "password123")
    client.cookies.clear()

    provider_api(google_api(email="ada@example.com", sub="google-sub-ada"))
    complete_login(client, "google")

    res = client.post(
        "/auth/link/confirm", json={"password": "not-the-password"}, headers=CSRF
    )

    assert res.status_code == 401
    assert res.json()["auth_error"] == "invalid_password"
    assert db_session.query(OAuthIdentity).count() == 0
    assert settings.SESSION_COOKIE_NAME not in client.cookies


def test_a_wrong_password_leaves_the_attempt_open_to_retry(client, provider_api):
    """A typo should not cost the user the whole OAuth round trip."""
    register(client, "ada@example.com", "password123")
    client.cookies.clear()

    provider_api(google_api(email="ada@example.com", sub="google-sub-ada"))
    complete_login(client, "google")

    client.post("/auth/link/confirm", json={"password": "wrong"}, headers=CSRF)
    assert settings.OAUTH_LINK_COOKIE_NAME in client.cookies

    retried = client.post(
        "/auth/link/confirm", json={"password": "password123"}, headers=CSRF
    )
    assert retried.status_code == 200


def test_an_expired_pending_link_is_rejected(client, db_session, provider_api, monkeypatch):
    register(client, "ada@example.com", "password123")
    client.cookies.clear()

    # Issue the token already expired rather than waiting ten minutes for it.
    monkeypatch.setattr(settings, "OAUTH_PENDING_LINK_TTL_SECONDS", -1)
    provider_api(google_api(email="ada@example.com", sub="google-sub-ada"))
    complete_login(client, "google")

    res = client.post(
        "/auth/link/confirm", json={"password": "password123"}, headers=CSRF
    )

    assert res.status_code == 400
    assert res.json()["auth_error"] == "link_expired"
    assert db_session.query(OAuthIdentity).count() == 0
    assert settings.SESSION_COOKIE_NAME not in client.cookies
    # Spent, so a retry cannot resurrect it.
    assert settings.OAUTH_LINK_COOKIE_NAME not in client.cookies


def test_an_expired_pending_link_is_rejected_at_the_describe_step_too(
    client, provider_api, monkeypatch
):
    register(client, "ada@example.com")
    client.cookies.clear()

    monkeypatch.setattr(settings, "OAUTH_PENDING_LINK_TTL_SECONDS", -1)
    provider_api(google_api(email="ada@example.com"))
    complete_login(client, "google")

    res = client.get("/auth/link/pending")
    assert res.status_code == 400
    assert res.json()["auth_error"] == "link_expired"


def test_confirming_with_no_pending_link_at_all_is_rejected(client, db_session):
    register(client, "ada@example.com", "password123")
    client.cookies.clear()

    res = client.post(
        "/auth/link/confirm", json={"password": "password123"}, headers=CSRF
    )

    assert res.status_code == 400
    assert res.json()["auth_error"] == "link_expired"
    assert db_session.query(OAuthIdentity).count() == 0


def test_a_forged_link_cookie_is_rejected(client, db_session):
    """The token is signed; an attacker-chosen one must not name an account."""
    register(client, "ada@example.com", "password123")
    victim = db_session.query(UserInfo).one()
    client.cookies.clear()

    client.cookies.set(
        settings.OAUTH_LINK_COOKIE_NAME, f"not.a.real.token.for.{victim.id}"
    )
    res = client.post(
        "/auth/link/confirm", json={"password": "password123"}, headers=CSRF
    )

    assert res.status_code == 400
    assert res.json()["auth_error"] == "link_expired"
    assert db_session.query(OAuthIdentity).count() == 0


def test_a_session_token_is_not_accepted_as_a_pending_link(client, db_session):
    """The two tokens share a signing key; only ``typ`` tells them apart."""
    register(client, "ada@example.com", "password123")
    user = db_session.query(UserInfo).one()

    from app.services.auth_service import create_access_token

    client.cookies.clear()
    client.cookies.set(settings.OAUTH_LINK_COOKIE_NAME, create_access_token(user.id))

    res = client.post(
        "/auth/link/confirm", json={"password": "password123"}, headers=CSRF
    )
    assert res.status_code == 400
    assert db_session.query(OAuthIdentity).count() == 0


def test_the_pending_link_token_is_not_a_usable_session(client, provider_api):
    register(client, "ada@example.com")
    client.cookies.clear()
    provider_api(google_api(email="ada@example.com"))
    complete_login(client, "google")

    link_token = client.cookies[settings.OAUTH_LINK_COOKIE_NAME]

    res = client.get("/auth/me", headers={"Authorization": f"Bearer {link_token}"})
    assert res.status_code == 401


def test_confirming_requires_the_csrf_header(client, db_session, provider_api):
    """A cookie-driven POST, so it needs what every other one needs."""
    register(client, "ada@example.com", "password123")
    client.cookies.clear()

    provider_api(google_api(email="ada@example.com"))
    complete_login(client, "google")

    res = client.post("/auth/link/confirm", json={"password": "password123"})

    assert res.status_code == 403
    assert db_session.query(OAuthIdentity).count() == 0


def test_a_pending_link_can_be_abandoned(client, provider_api):
    register(client, "ada@example.com")
    client.cookies.clear()
    provider_api(google_api(email="ada@example.com"))
    complete_login(client, "google")

    res = client.post("/auth/link/cancel", headers=CSRF)

    assert res.status_code == 200
    assert settings.OAUTH_LINK_COOKIE_NAME not in client.cookies


def test_the_account_email_must_still_match_at_confirmation_time(
    client, db_session, provider_api
):
    """The token is a claim about ten minutes ago; the row is now.

    If the address moved to a different account in between, the link must not
    land on whoever holds that row today.
    """
    register(client, "ada@example.com", "password123")
    client.cookies.clear()

    provider_api(google_api(email="ada@example.com", sub="google-sub-ada"))
    complete_login(client, "google")

    moved = db_session.query(UserInfo).one()
    moved.email = "somebody-else@example.com"
    moved.hashed_password = hash_password("password123")
    db_session.commit()

    res = client.post(
        "/auth/link/confirm", json={"password": "password123"}, headers=CSRF
    )

    assert res.status_code == 400
    assert res.json()["auth_error"] == "link_expired"
    assert db_session.query(OAuthIdentity).count() == 0


def test_confirmation_is_required_for_github_too(client, db_session, provider_api):
    """The rule is about the matched account, not about which provider asked."""
    register(client, "ada@example.com", "password123")
    client.cookies.clear()

    provider_api(github_api())
    res = complete_login(client, "github")

    assert_redirected_to(res, "/link-account")
    assert db_session.query(OAuthIdentity).count() == 0


def test_email_case_still_matches_but_now_requires_confirmation(
    client, db_session, provider_api
):
    register(client, "Ada@Example.com", "password123")
    client.cookies.clear()

    provider_api(google_api(email="ada@example.com", sub="google-sub-case"))
    res = complete_login(client, "google")

    assert_redirected_to(res, "/link-account")

    confirmed = client.post(
        "/auth/link/confirm", json={"password": "password123"}, headers=CSRF
    )
    assert confirmed.status_code == 200
    assert db_session.query(UserInfo).count() == 1
    assert db_session.query(OAuthIdentity).count() == 1


# --- state / CSRF ----------------------------------------------------------


def test_callback_rejects_a_state_that_does_not_match(client, db_session, provider_api):
    fake = provider_api(google_api())
    begin_login(client, "google")  # a real state cookie is in the jar

    res = client.get(
        "/auth/callback/google",
        params={"code": "auth-code", "state": "not-the-state-we-issued"},
        follow_redirects=False,
    )

    assert_auth_error(res, "invalid_state")
    # Rejected before the code was spent: no call reached the provider at all.
    assert fake.requests == []
    assert db_session.query(UserInfo).count() == 0
    assert settings.SESSION_COOKIE_NAME not in client.cookies


def test_callback_rejects_a_missing_state_cookie(client, db_session, provider_api):
    fake = provider_api(google_api())

    # No /login leg, so nothing set the cookie -- this is the forged-callback
    # case, where an attacker sends a victim straight to the callback URL.
    res = client.get(
        "/auth/callback/google",
        params={"code": "auth-code", "state": "attacker-chosen-state"},
        follow_redirects=False,
    )

    assert_auth_error(res, "invalid_state")
    assert fake.requests == []
    assert db_session.query(UserInfo).count() == 0


def test_callback_rejects_a_missing_state_parameter(client, provider_api):
    provider_api(google_api())
    begin_login(client, "google")

    res = client.get(
        "/auth/callback/google", params={"code": "auth-code"}, follow_redirects=False
    )

    assert_auth_error(res, "invalid_state")


def test_state_issued_for_one_provider_is_not_valid_at_the_other(client, provider_api):
    provider_api(github_api())
    state = begin_login(client, "google")

    res = client.get(
        "/auth/callback/github",
        params={"code": "auth-code", "state": state},
        follow_redirects=False,
    )

    assert_auth_error(res, "invalid_state")


def test_state_cookie_is_not_a_usable_session(client):
    """The state token shares a signing key with the session token.

    It carries no ``sub`` claim, which is what stops it being replayed as a
    session cookie -- worth pinning, because the two tokens are otherwise
    signed identically.
    """
    client.get("/auth/google/login", follow_redirects=False)
    state_token = client.cookies[settings.OAUTH_STATE_COOKIE_NAME]

    res = client.get("/auth/me", headers={"Authorization": f"Bearer {state_token}"})
    assert res.status_code == 401


def test_state_is_single_use(client, provider_api):
    """The cookie is cleared on the way out, so a replayed callback fails."""
    provider_api(google_api())
    state = begin_login(client, "google")

    first = client.get(
        "/auth/callback/google",
        params={"code": "auth-code", "state": state},
        follow_redirects=False,
    )
    assert first.status_code == 302
    assert first.headers["location"] == settings.FRONTEND_URL

    replayed = client.get(
        "/auth/callback/google",
        params={"code": "auth-code", "state": state},
        follow_redirects=False,
    )
    assert_auth_error(replayed, "invalid_state")


def test_a_failed_callback_spends_the_state(client, provider_api):
    """State is single-use whether or not the login worked."""
    provider_api(google_api(email="ada@example.com", email_verified=False))
    state = begin_login(client, "google")

    rejected = client.get(
        "/auth/callback/google",
        params={"code": "auth-code", "state": state},
        follow_redirects=False,
    )
    assert_auth_error(rejected, "email_unverified")
    assert settings.OAUTH_STATE_COOKIE_NAME not in client.cookies

    provider_api(google_api(email="ada@example.com", email_verified=True))
    retried = client.get(
        "/auth/callback/google",
        params={"code": "auth-code", "state": state},
        follow_redirects=False,
    )
    assert_auth_error(retried, "invalid_state")


# --- verified email --------------------------------------------------------


def test_google_unverified_email_is_rejected(client, db_session, provider_api):
    provider_api(
        google_api(email="impostor@example.com", sub="google-sub-x", email_verified=False)
    )

    res = complete_login(client, "google")

    assert_auth_error(res, "email_unverified")
    assert db_session.query(UserInfo).count() == 0
    assert db_session.query(OAuthIdentity).count() == 0
    assert settings.SESSION_COOKIE_NAME not in client.cookies


def test_google_email_verified_must_be_true_not_merely_present(client, provider_api):
    """A falsy-but-present flag is not a verification."""
    provider_api(
        google_api(email="impostor@example.com", sub="google-sub-y", email_verified="no")
    )

    assert_auth_error(complete_login(client, "google"), "email_unverified")


def test_unverified_google_email_cannot_claim_an_existing_account(
    client, db_session, provider_api
):
    """The takeover the verification check exists to stop."""
    register(client, "ada@example.com")
    client.cookies.clear()

    provider_api(
        google_api(email="ada@example.com", sub="attacker-sub", email_verified=False)
    )
    assert_auth_error(complete_login(client, "google"), "email_unverified")

    assert db_session.query(OAuthIdentity).count() == 0
    assert settings.OAUTH_LINK_COOKIE_NAME not in client.cookies


def test_github_uses_the_primary_verified_email(client, db_session, provider_api):
    fake = provider_api(
        github_api(
            # The profile email is public and unverified; the list holds a
            # verified secondary and a verified primary. Only the last is
            # acceptable.
            profile_email="public@example.com",
            emails=[
                {"email": "secondary@example.com", "primary": False, "verified": True},
                {"email": "unverified@example.com", "primary": True, "verified": False},
                {"email": "ada@example.com", "primary": True, "verified": True},
            ],
        )
    )

    res = complete_login(client, "github")

    assert res.status_code == 302
    assert db_session.query(UserInfo).one().email == "ada@example.com"
    # It really did ask the emails endpoint rather than trusting /user.email.
    assert any(str(r.url) == GITHUB_EMAILS_URL for r in fake.requests)


def test_github_rejects_an_account_with_no_verified_primary_email(
    client, db_session, provider_api
):
    provider_api(
        github_api(
            emails=[
                {"email": "ada@example.com", "primary": True, "verified": False},
                {"email": "other@example.com", "primary": False, "verified": True},
            ]
        )
    )

    assert_auth_error(complete_login(client, "github"), "email_unverified")
    assert db_session.query(UserInfo).count() == 0


def test_github_rejects_an_empty_email_list(client, provider_api):
    provider_api(github_api(emails=[]))
    assert_auth_error(complete_login(client, "github"), "email_unverified")


# --- secret handling -------------------------------------------------------


def test_the_client_secret_goes_only_to_the_token_endpoint(client, provider_api):
    fake = provider_api(google_api())

    complete_login(client, "google")

    token_body = fake.body_for(GOOGLE_TOKEN_URL)
    assert token_body["client_secret"] == ["test-google-client-secret"]
    assert token_body["grant_type"] == ["authorization_code"]
    assert token_body["redirect_uri"] == [EXPECTED_REDIRECT_URI["google"]]

    # Every other outbound call carries the access token, never the secret.
    for request in fake.requests:
        if str(request.url).split("?")[0] == GOOGLE_TOKEN_URL:
            continue
        assert "test-google-client-secret" not in request.content.decode()
        assert "test-google-client-secret" not in str(request.headers)


def test_no_response_to_the_browser_contains_a_client_secret(client, provider_api):
    provider_api(google_api())

    redirect = client.get("/auth/google/login", follow_redirects=False)
    callback = complete_login(client, "google")

    for response in (redirect, callback):
        rendered = f"{response.headers}{response.text}"
        assert "test-google-client-secret" not in rendered
        assert "test-github-client-secret" not in rendered


def test_provider_error_body_is_not_echoed_into_the_url(client, provider_api):
    """The token endpoint's error body quotes the request, code included."""
    provider_api(
        {
            GOOGLE_TOKEN_URL: (
                400,
                {"error": "invalid_grant", "error_description": "code=secret-code-value"},
            )
        }
    )

    res = complete_login(client, "google", code="secret-code-value")

    assert_auth_error(res, "provider_error")
    assert "secret-code-value" not in res.headers["location"]
    assert "invalid_grant" not in res.headers["location"]


def test_only_known_codes_can_reach_a_url():
    """The guard that keeps free text out of the redirect."""
    from app.api.routes_oauth import _error_redirect

    with pytest.raises(ValueError):
        _error_redirect("something-a-later-edit-made-up")


# --- interaction with password login ---------------------------------------


def test_an_oauth_only_account_cannot_be_signed_into_with_a_password(
    client, provider_api
):
    provider_api(google_api(email="ada@example.com"))
    complete_login(client, "google")

    res = client.post(
        "/auth/login", json={"email": "ada@example.com", "password": "password123"}
    )

    # 401 and the same wording as any other failure: a NULL hash must not be
    # mistaken for a blank password, and must not answer "this address uses
    # Google" to anyone who asks.
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid email or password"


def test_password_login_still_works_after_linking(client, provider_api):
    register(client, "ada@example.com", "password123")
    client.cookies.clear()

    provider_api(google_api(email="ada@example.com"))
    complete_login(client, "google")
    client.post("/auth/link/confirm", json={"password": "password123"}, headers=CSRF)
    client.cookies.clear()

    res = client.post(
        "/auth/login", json={"email": "ada@example.com", "password": "password123"}
    )
    assert res.status_code == 200


def test_user_denying_consent_is_rejected(client, db_session, provider_api):
    provider_api(google_api())
    state = begin_login(client, "google")

    res = client.get(
        "/auth/callback/google",
        params={"state": state, "error": "access_denied"},
        follow_redirects=False,
    )

    assert_auth_error(res, "access_denied")
    assert db_session.query(UserInfo).count() == 0
