from __future__ import annotations

import base64

from spiritvpn_bot.application.builders.subscription_content_builder import (
    build_subscription_content,
)
from spiritvpn_bot.application.ports.vpn_gateway import AccessLink


def test_includes_only_ready_links() -> None:
    links = [
        AccessLink(kind="FREEDOM", state="READY", uri="vless://a"),
        AccessLink(kind="FREEDOM", state="PENDING"),
        AccessLink(kind="BRIDGE", state="BLOCKED", block_reason="TIME_EXPIRED"),
        AccessLink(kind="BRIDGE", state="READY", uri="vless://b"),
    ]

    content = build_subscription_content(links)

    decoded = base64.b64decode(content).decode("utf-8")
    assert decoded == "vless://a\nvless://b"


def test_empty_link_list_gives_empty_body() -> None:
    content = build_subscription_content([])
    assert base64.b64decode(content) == b""


def test_output_is_valid_base64() -> None:
    links = [AccessLink(kind="FREEDOM", state="READY", uri="vless://a?x=1&y=2#Name")]
    content = build_subscription_content(links)
    # не бросает — b64decode кидает binascii.Error на невалидном вводе
    base64.b64decode(content, validate=True)
