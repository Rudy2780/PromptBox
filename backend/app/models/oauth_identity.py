from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from app.database import Base


class OAuthIdentity(Base):
    """A third-party login linked to a PromptBox account.

    Modelled as its own table rather than as ``google_id``/``github_id``
    columns on ``users`` because the relationship is genuinely one-to-many: one
    account can be reachable through a password *and* Google *and* GitHub, and
    adding a fourth provider later is then a row, not a migration.

    The natural key is (provider, provider_user_id) -- the provider's own
    immutable id for the account, never the email address. Emails get changed
    and re-assigned; ``sub`` (Google) and the numeric ``id`` (GitHub) do not.
    Email is used only once, to decide which existing account a *new* identity
    should attach to.
    """

    __tablename__ = "oauth_identities"
    __table_args__ = (
        # Two PromptBox accounts must never claim the same provider account:
        # that is what would let one user sign in as another. Enforced in the
        # database rather than only in the service, so a concurrent double
        # callback fails on the constraint instead of racing.
        UniqueConstraint(
            "provider", "provider_user_id", name="uq_oauth_identity_provider_user"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider = Column(String(32), nullable=False)
    provider_user_id = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
