from datetime import timedelta

import pytest
from jose import jwt
from pydantic import ValidationError
from sqlalchemy import make_url

from app.core.config import Settings, settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_temporary_password,
    get_password_hash,
    verify_password,
)


def test_bcrypt_does_not_truncate_unicode():
    password = "ñ" * 36
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password(password + "x", hashed)
    with pytest.raises(ValueError):
        get_password_hash(password + "x")
    assert not verify_password("incorrecta", "hash inválido")


def test_temporary_passwords_are_distinct():
    passwords = {generate_temporary_password() for _ in range(100)}
    assert len(passwords) == 100
    assert all(len(password) == 24 for password in passwords)


def test_tokens_validate_signature_expiration_and_required_claims():
    token = create_access_token({"sub": "1", "ver": 1})
    assert decode_access_token(token)["ver"] == 1
    assert decode_access_token(create_access_token({"sub": "1", "ver": 1}, timedelta(seconds=-1))) is None
    assert decode_access_token(jwt.encode({"sub": "1"}, settings.SECRET_KEY, algorithm="HS256")) is None
    assert (
        decode_access_token(
            jwt.encode({"sub": "1", "exp": 9999999999, "iat": 1}, "another-key", algorithm="HS256")
        )
        is None
    )


def test_database_password_is_url_encoded():
    config = Settings(POSTGRES_PASSWORD="a@b:c/%#?", _env_file=None)
    assert make_url(config.ASYNC_DATABASE_URL).password == "a@b:c/%#?"


@pytest.mark.parametrize(
    "values",
    [
        {"SECRET_KEY": "cambiar_en_cada_entorno"},
        {"SECRET_KEY": "a" * 40},
        {"ALGORITHM": "none"},
        {"ACCESS_TOKEN_EXPIRE_MINUTES": 0},
        {"CORS_ORIGINS": ["*"]},
    ],
)
def test_invalid_config(values):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)
