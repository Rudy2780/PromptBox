from pydantic import BaseModel, EmailStr, Field, field_validator

# bcrypt refuses any password longer than 72 bytes. The previous 128-character
# cap let longer values through to hashing, where bcrypt raised ValueError and
# the request became a 500 -- on register *and* on login.
MAX_PASSWORD_BYTES = 72


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def _within_bcrypt_limit(cls, value: str) -> str:
        """Reject passwords over bcrypt's 72-byte ceiling with a clear message.

        Measured in bytes, not characters: a 72-character password made of
        multi-byte characters (emoji, CJK) can be well over 72 bytes, and a
        character-based cap would let it through to the same crash.
        """
        encoded_length = len(value.encode("utf-8"))
        if encoded_length > MAX_PASSWORD_BYTES:
            raise ValueError(
                f"Password must be at most {MAX_PASSWORD_BYTES} bytes "
                f"(got {encoded_length}). Note that accented, emoji and "
                "non-Latin characters use more than one byte each."
            )
        return value
