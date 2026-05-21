from app.utils.security import hash_password, verify_password

def test_hash_is_not_plaintext():
	hashed = hash_password("secret")
	assert hashed != "secret"

def test_verify_correct_password():
	hashed = hash_password("secret")
	assert verify_password("secret", hashed) is True

def test_verify_wrong_password():
	hashed = hash_password("secret")
	assert verify_password("wrong", hashed) is False

