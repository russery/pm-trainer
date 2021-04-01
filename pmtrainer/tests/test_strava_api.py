import unittest
import json
from datetime import datetime, timedelta, timezone
from ..settings import Settings
from ..strava_api import StravaApi


class TestStravaApi(unittest.TestCase):
    def setUp(self):
        secrets_file = "secrets.ini"
        self.secrets = Settings()
        self.secrets.load_settings(secrets_file)
        self.api = StravaApi(self.secrets)
        try:
            if not self.api.is_authed():
                print("Not authenticated.... going for auth")
                self.api.get_auth()
                self.secrets.write_settings(secrets_file)
            else:
                print("Using cached auth token")
        except StravaApi.AuthError as e:
            if e.exception.err_type == StravaApi.AuthError.ErrorType.CLIENT:
                print("Couldn't authenticate with given client secrets. " \
                      "Check that they are correct.")
            raise e

    def test_no_secrets(self):
        client = self.secrets.get("client_id")
        self.secrets.delete("client_id")
        with self.assertRaises(StravaApi.AuthError) as e:
            self.api.check_secrets()
        self.assertEqual(e.exception.err_type, StravaApi.AuthError.ErrorType.CLIENT)
        self.secrets.set("client_id", client)
        self.secrets.delete("client_secret")
        with self.assertRaises(StravaApi.AuthError) as e:
            self.api.check_secrets()
        self.assertEqual(e.exception.err_type, StravaApi.AuthError.ErrorType.CLIENT)

    def test_api_request(self):
        resp = json.loads(self.api.api_request(StravaApi.ATHLETE_URL).text)
        # Just check that a response was received and that a key is present:
        self.assertTrue("id" in resp.keys())

    def test_api_request_bad_token(self):
        self.secrets.set("access_token", "badtoken")
        with self.assertRaises(StravaApi.AuthError) as e:
            _ = self.api.api_request(StravaApi.ATHLETE_URL)
        self.assertEqual(e.exception.err_type, StravaApi.AuthError.ErrorType.HTTP_RESP)

    def test_api_request_bad_url(self):
        bad_url = "https://www.strava.com/api/v3/badathlete"
        with self.assertRaises(StravaApi.AuthError) as e:
            _ = self.api.api_request(bad_url)
        self.assertEqual(e.exception.err_type, StravaApi.AuthError.ErrorType.HTTP_RESP)

    def test_is_not_authed(self):
        # Back up secrets
        token = self.secrets.get("access_token")
        expiry = self.secrets.get("access_token_expire_time")
        # Check that we're authenticated:
        self.assertTrue(self.api.is_authed())
        # Delete token and verify auth fails:
        self.secrets.delete("access_token")
        self.assertFalse(self.api.is_authed())
        # Restore token and set expiry in the past and verify auth fails:
        self.secrets.set("access_token", token)
        self.secrets.set("access_token_expire_time", "1617303107")
        self.assertFalse(self.api.is_authed())
        # Restore expiry time and verify auth succeeds once again
        self.secrets.set("access_token_expire_time", expiry)
        self.assertTrue(self.api.is_authed())

    def test_force_auth(self):
        self.secrets.delete("access_token")
        self.secrets.delete("access_token_expire_time")
        self.secrets.delete("refresh_token")
        self.api.get_auth()
        self.assertIsNotNone(self.secrets.get("access_token"))
        self.assertIsNotNone(self.secrets.get("access_token_expire_time"))
        self.assertIsNotNone(self.secrets.get("refresh_token"))

    def test_renew_auth(self):
        self.api.get_auth()
        old_expiry = int(self.secrets.get("access_token_expire_time"))
        expected_expiry = int((datetime.now(timezone.utc) +
                               timedelta(minutes=5)).timestamp())
        self.api.renew_auth()
        new_expiry = int(self.secrets.get("access_token_expire_time"))
        self.assertTrue(new_expiry >= old_expiry)
        self.assertTrue(new_expiry >= expected_expiry)
