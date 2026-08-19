from __future__ import annotations

from spiritvpn_bot.application.subscription_token import SubscriptionTokenSigner


def test_sign_then_verify_roundtrips() -> None:
    signer = SubscriptionTokenSigner(b"secret-key")

    token = signer.sign("tg:12345")

    assert signer.verify(token) == "tg:12345"


def test_tampered_payload_is_rejected() -> None:
    signer = SubscriptionTokenSigner(b"secret-key")
    token = signer.sign("tg:12345")
    payload, signature = token.split(".", 1)

    tampered = signer.sign("tg:99999").split(".", 1)[0] + "." + signature

    assert signer.verify(tampered) is None


def test_wrong_signing_key_is_rejected() -> None:
    signed_with_a = SubscriptionTokenSigner(b"key-a").sign("tg:12345")

    assert SubscriptionTokenSigner(b"key-b").verify(signed_with_a) is None


def test_malformed_token_is_rejected() -> None:
    signer = SubscriptionTokenSigner(b"secret-key")

    assert signer.verify("not-a-valid-token") is None
    assert signer.verify("") is None


def test_different_customers_get_different_tokens() -> None:
    signer = SubscriptionTokenSigner(b"secret-key")

    assert signer.sign("tg:1") != signer.sign("tg:2")
