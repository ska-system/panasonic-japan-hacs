"""Test script for Web Push header parsing and decryption patch in push.py."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

for _mod in ("fcntl", "grp", "termios", "tty", "pty", "resource"):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from unittest.mock import patch

from custom_components.panasonic_japan.push import (
    PanasonicPushHandler,
    _extract_header_param,
)


class TestWebPushParsing(unittest.TestCase):
    def test_parse_sliced_crypto_key(self):
        # fcmpushclient slices [3:], so "dh=" is gone, but "; p256ecdsa=..." remains
        raw_header = "BPp0q96PDAQKC3O7HtKSdYjzLidNcghosrEB9Yzwecp0-VlSk_c106jUeeFUmGQUgBjA6dxvtnLNIIZ39v3x4dY; p256ecdsa=BDOU99-h67HcA6JefXHbSNMu7e2yNNu3RzoMj8TM4W88jITfq7ZmPvIM1lv-4_I2LXQcYwhqby2xGPwwzjfAnG4=="
        dh = _extract_header_param(raw_header, "dh")
        self.assertEqual(
            dh,
            "BPp0q96PDAQKC3O7HtKSdYjzLidNcghosrEB9Yzwecp0-VlSk_c106jUeeFUmGQUgBjA6dxvtnLNIIZ39v3x4dY=",
        )

    def test_parse_explicit_crypto_key(self):
        raw_header = "dh=BPp0q96PDAQKC3O7HtKSdYjzLidNcghosrEB9Yzwecp0; p256ecdsa=BDOU99"
        dh = _extract_header_param(raw_header, "dh")
        self.assertEqual(dh, "BPp0q96PDAQKC3O7HtKSdYjzLidNcghosrEB9Yzwecp0")

    def test_parse_quoted_crypto_key(self):
        raw_header = 'dh="BPp0q96PDAQKC3O7HtKSdYjzLidNcghosrEB9Yzwecp0"; p256ecdsa="BDOU99"'
        dh = _extract_header_param(raw_header, "dh")
        self.assertEqual(dh, "BPp0q96PDAQKC3O7HtKSdYjzLidNcghosrEB9Yzwecp0")

    def test_parse_reversed_order(self):
        raw_header = "p256ecdsa=BDOU99; dh=BPp0q96PDAQKC3O7HtKSdYjzLidNcghosrEB9Yzwecp0"
        dh = _extract_header_param(raw_header, "dh")
        self.assertEqual(dh, "BPp0q96PDAQKC3O7HtKSdYjzLidNcghosrEB9Yzwecp0")

    def test_parse_salt_sliced(self):
        raw_salt = "abcd1234efgh5678; keyid=foo"
        salt = _extract_header_param(raw_salt, "salt")
        self.assertEqual(salt, "abcd1234efgh5678")

    def test_padding(self):
        self.assertEqual(_extract_header_param("abc", "dh"), "abc=")
        self.assertEqual(_extract_header_param("ab", "dh"), "ab==")
        self.assertEqual(_extract_header_param("abcd", "dh"), "abcd")


class TestPushHandlerAutoRecovery(unittest.TestCase):
    def test_decrypt_failure_triggers_recovery(self):
        hass = MagicMock()
        api = MagicMock()
        config_entry = MagicMock()
        config_entry.data = {
            "push_term_id": "old_term",
            "fcm_credentials": {"dummy": "creds"},
            "appliances": [],
        }

        handler = PanasonicPushHandler(hass, api, config_entry)

        # Simulate 2 failures -> no recovery triggered yet
        handler._record_decrypt_failure()
        handler._record_decrypt_failure()
        self.assertEqual(handler._decrypt_error_count, 2)

        # 3rd failure -> triggers auto-recovery with force_reregister=True
        coros = []
        def capture_task(coro):
            coros.append(coro)
            return MagicMock()

        hass.async_create_task.side_effect = capture_task
        handler._record_decrypt_failure()
        self.assertEqual(handler._decrypt_error_count, 0)
        hass.async_create_task.assert_called_once()
        for c in coros:
            c.close()

    def test_on_message_handles_raw_bytes_as_decrypt_failure(self):
        hass = MagicMock()
        api = MagicMock()
        config_entry = MagicMock()
        handler = PanasonicPushHandler(hass, api, config_entry)
        handler._record_decrypt_failure = MagicMock()

        # Push payload where decryption failed (returns message as raw bytes)
        handler._on_message({"message": b"undecrypted_raw_data"}, "sender_id")
        handler._record_decrypt_failure.assert_called_once()


if __name__ == "__main__":
    unittest.main()
