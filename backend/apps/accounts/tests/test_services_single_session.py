from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.test import TestCase

from apps.accounts.services import invalidate_previous_session

User = get_user_model()


def _new_session_key():
    store = SessionStore()
    store["placeholder"] = True
    store.save()
    return store.session_key


class SingleSessionPerMeseroTests(TestCase):
    """T17 — logging in on a new device invalidates the previous session (RF-9)."""

    def setUp(self):
        self.mesero = User.objects.create_user(
            username="mesero_unico", password="1234", role=User.Role.MESERO
        )

    def test_first_login_just_records_the_session_key(self):
        key_a = _new_session_key()
        invalidate_previous_session(self.mesero, key_a)
        self.mesero.refresh_from_db()
        self.assertEqual(self.mesero.current_session_key, key_a)
        self.assertTrue(SessionStore().exists(key_a))

    def test_second_login_invalidates_the_first_session(self):
        key_a = _new_session_key()
        invalidate_previous_session(self.mesero, key_a)

        key_b = _new_session_key()
        invalidate_previous_session(self.mesero, key_b)

        self.mesero.refresh_from_db()
        self.assertEqual(self.mesero.current_session_key, key_b)
        self.assertFalse(SessionStore().exists(key_a))
        self.assertTrue(SessionStore().exists(key_b))

    def test_relogin_with_the_same_session_key_is_a_no_op(self):
        key_a = _new_session_key()
        invalidate_previous_session(self.mesero, key_a)
        invalidate_previous_session(self.mesero, key_a)
        self.assertTrue(SessionStore().exists(key_a))
