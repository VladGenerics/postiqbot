"""OAuth state: подпись, срок жизни и устойчивость к подделке."""
from __future__ import annotations

import time

import pytest
from cryptography.fernet import Fernet, InvalidToken

from bot.services import crypto
from bot.services.oauth_state import (
    STATE_TTL_SECONDS,
    decode_simple_state,
    decode_state,
    encode_simple_state,
    encode_state,
)


class TestRoundTrip:
    @pytest.mark.parametrize(
        "telegram_id,project_id",
        [(1, 1), (123456789, 7), (7_999_999_999, 28)],
    )
    def test_google_state(self, telegram_id, project_id):
        assert decode_state(encode_state(telegram_id, project_id)) == (
            telegram_id,
            project_id,
        )

    def test_tiktok_state(self):
        assert decode_simple_state(encode_simple_state(123456789)) == 123456789

    def test_state_is_not_readable(self):
        """В URL уезжает шифртекст, а не telegram_id открытым текстом."""
        state = encode_state(123456789, 7)
        assert "123456789" not in state

    def test_states_differ_between_calls(self):
        """Fernet добавляет IV — одинаковая пара даёт разные state (не следит за пользователем по повторяющейся строке в логах прокси)."""
        assert encode_state(1, 1) != encode_state(1, 1)


class TestRejects:
    @pytest.mark.parametrize("bad", ["", "hello", "not-a-token", "a" * 40])
    def test_garbage(self, bad):
        with pytest.raises(InvalidToken):
            decode_state(bad)

    def test_tampered_token(self):
        state = encode_state(123456789, 7)
        middle = len(state) // 2
        swapped = "b" if state[middle] == "a" else "a"
        forged = state[:middle] + swapped + state[middle + 1 :]
        with pytest.raises(InvalidToken):
            decode_state(forged)

    def test_token_signed_by_another_key(self):
        alien = Fernet(Fernet.generate_key()).encrypt(b"123456789:7").decode()
        with pytest.raises(InvalidToken):
            decode_state(alien)

    def test_expired_token(self):
        old = int(time.time()) - STATE_TTL_SECONDS - 5
        state = crypto._fernet().encrypt_at_time(b"123456789:7", old).decode()
        with pytest.raises(InvalidToken):
            decode_state(state)

    def test_token_within_ttl_still_works(self):
        recent = int(time.time()) - 5
        state = crypto._fernet().encrypt_at_time(b"123456789:7", recent).decode()
        assert decode_state(state) == (123456789, 7)

    def test_tiktok_state_is_not_a_google_state(self):
        """Подпись валидна, но начинки на два поля нет — должно падать, а не подставлять project_id наугад."""
        with pytest.raises(ValueError):
            decode_state(encode_simple_state(123456789))
