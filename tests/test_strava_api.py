import unittest
import os
from datetime import datetime, timedelta, timezone
from pprint import pprint
from pmtrainer.settings import Settings
from pmtrainer.strava_api import StravaApi, StravaData

CONFIG_PATH = os.path.expanduser("~/pmtrainer/pm_trainer_settings.ini")

class TestStravaApi(unittest.TestCase):
    def setUp(self):
        self.secrets = Settings(CONFIG_PATH)
        self.api = StravaApi(self.secrets)
        try:
            if not self.api.is_authed():
                print("Not authenticated.... going for auth")
                self.api.get_auth()
                self.secrets.write_settings(CONFIG_PATH)
            else:
                print("Using cached auth token.")
        except StravaApi.AuthError as e:
            if e.err_type == StravaApi.AuthError.ErrorType.CLIENT:
                print("Couldn't authenticate with given client secrets. " \
                      "Check that they exist and are correct.")
            raise e

    def test_force_auth(self):
        self.api.remove_auth()
        self.assertFalse(self.api.is_authed())
        self.api.get_auth()
        self.assertIsNotNone(self.secrets.get("access_token"))
        self.assertIsNotNone(self.secrets.get("access_token_expire_time"))
        self.assertIsNotNone(self.secrets.get("refresh_token"))
        self.assertTrue(self.api.is_authed())

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
        resp = self.api.api_request(StravaApi.ATHLETE_URL)
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

    def test_renew_auth(self):
        self.api.get_auth()
        old_expiry = int(self.secrets.get("access_token_expire_time"))
        expected_expiry = int((datetime.now(timezone.utc) +
                               timedelta(minutes=5)).timestamp())
        self.api.renew_auth()
        new_expiry = int(self.secrets.get("access_token_expire_time"))
        self.assertTrue(new_expiry >= old_expiry)
        self.assertTrue(new_expiry >= expected_expiry)

    def test_auth_timeout(self):
        url_bak = StravaApi.AUTH_URL
        StravaApi.AUTH_URL = "http://fakeurl/"
        with self.assertRaises(StravaApi.AuthError) as e:
            self.api.get_tokens()
        self.assertEqual(e.exception.err_type, StravaApi.AuthError.ErrorType.TIMEOUT)
        StravaApi.AUTH_URL = url_bak

    def test_auth_scope(self):
        # Requires user interaction to pass... To do this correctly:
        # When the Strava auth browser window pops up, de-select permissions for activity upload
        # and then click Authorize.
        with self.assertRaises(StravaApi.AuthError) as e:
            self.api.get_tokens()
        self.assertEqual(e.exception.err_type, StravaApi.AuthError.ErrorType.SCOPE)

    def test_remove_auth(self):
        self.api.remove_auth()
        self.assertFalse(self.api.is_authed())
        with self.assertRaises(KeyError):
            self.secrets.get("access_token")
        with self.assertRaises(KeyError):
            self.secrets.get("access_token_expire_time")
        with self.assertRaises(KeyError):
            self.secrets.get("refresh_token")

class TestStravaData(unittest.TestCase):
    def setUp(self):
        self.secrets = Settings(CONFIG_PATH)
        self.api = StravaApi(self.secrets)
        try:
            if not self.api.is_authed():
                print("Not authenticated.... going for auth")
                self.api.get_auth()
                self.secrets.write_settings(CONFIG_PATH)
            else:
                print("Using cached auth token")
        except StravaApi.AuthError as e:
            if e.err_type == StravaApi.AuthError.ErrorType.CLIENT:
                print("Couldn't authenticate with given client secrets. " \
                      "Check that they are correct.")
            raise e
        self.strava_data = StravaData(self.api)

    def test_athlete_name(self):
        name = self.strava_data.get_athlete_name()
        print(name)
        self.assertIsNotNone(name)

    def test_upload_activity(self):
        activity_file = os.path.dirname(__file__) + "/fixtures/sample_tcx_files/20210325_160413.tcx"
        name = "20201205_091538"
        description = "test upload"
        trainer = True
        commute = False
        data_type = "tcx"
        try:
            resp = self.strava_data.upload_activity(activity_file=activity_file, name=name,
                                                      description=description, trainer=trainer,
                                                      commute=commute, data_type=data_type,
                                                      activity_type="VirtualRide")
            pprint(resp)
            self.assertIsNotNone(resp["id"])
        except StravaApi.AuthError as e:
            # This type of error can occur for duplicate activity uploads. To prevent it
            # make sure that the test activity being uploaded is unique.
            self.assertEqual(e.err_type, StravaApi.AuthError.ErrorType.UNKNOWN)
