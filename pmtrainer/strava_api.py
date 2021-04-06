"""
Access the Strava API, including oauth2 authentication.

Copyright (C) 2021  Robert Ussery

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
from enum import Enum
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from threading import Thread
import time
import subprocess
import sys
import requests
from pmtrainer.assets import strava_auth_confirm_page as auth_page

class StravaApi():
    """
    Access the Strava API, including oauth2 authentication.
    """
    AUTH_URL = "http://www.strava.com/oauth/authorize"
    TOKEN_URL = "https://www.strava.com/oauth/token"
    ATHLETE_URL = "https://www.strava.com/api/v3/athlete"

    AUTH_SCOPE = ["activity:write", "activity:read_all"]

    SERVER_HOSTNAME = "localhost"
    SERVER_PORT = 8080
    SERVER_CALLBACK_URI = "http://{}:{}".format(SERVER_HOSTNAME,SERVER_PORT)

    class AuthError(Exception):
        """
        Exceptions for the authentication process
        """
        class ErrorType(Enum):
            """
            Type of error
            """
            UNKNOWN = 1
            HTTP_RESP = 2
            TIMEOUT = 3
            CLIENT = 4
            SCOPE = 5

        def __init__(self, expression=None, message="", err_type=ErrorType.UNKNOWN):
            super().__init__(message)
            self.expression = expression
            self.message = message
            self.err_type = err_type


    class AuthCodeHandler(BaseHTTPRequestHandler):
        '''
        Handles redirect from Strava Oauth2 interface, captures auth code
        and displays a nice page for the user.
        '''
        callback_received = False
        auth_code = None
        auth_scopes = []

        def reset():
            '''
            Resets static members of this class.
            '''
            StravaApi.AuthCodeHandler.callback_received = False
            StravaApi.AuthCodeHandler.auth_code = None
            StravaApi.AuthCodeHandler.auth_scopes = []

        def do_GET(self):
            '''
            Handles page request from Strava Oauth2 redirect.
            '''
            # Ignore favicon requests
            if self.path.endswith("favicon.ico"):
                return

            # Parse response and extract auth code and scopes:
            resp = self.path.lstrip("/?").split("&")
            code = None
            scopes = None
            for r in resp:
                if "code=" in r:
                    code = r.replace("code=", "")
                if "scope=" in r:
                    scopes = r.replace("scope=", "").split(",")
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            if code and all(x in scopes for x in StravaApi.AUTH_SCOPE):
                self.wfile.write(bytes(auth_page.strava_auth_confirm_page.format(
                    success_msg="You've successfully authenticated",
                    action_msg="Please close this window and return to PM Trainer"),
                    "utf-8"))
            else:
                self.wfile.write(bytes(auth_page.strava_auth_confirm_page.format(
                    success_msg="Failed to authenticate",
                    action_msg="Please close this window, return to PM Trainer, and try again."),
                    "utf-8"))

            if code and scopes:
                StravaApi.AuthCodeHandler.auth_code = code
                StravaApi.AuthCodeHandler.auth_scopes = scopes
            StravaApi.AuthCodeHandler.callback_received = True


    def __init__(self, secrets_store):
        self.secrets_store = secrets_store
        self.httpd = None # Only instantiate this if/when we need it
        self.httpd_thread = None

    def _do_server(self, _):
        '''
        Thread function for http daemon thread.
        '''
        self.httpd.serve_forever()

    def _kill_httpd(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        time.sleep(1) # Make sure the server is closed...
        self.httpd_thread.join()
        StravaApi.AuthCodeHandler.reset()

    def check_secrets(self):
        '''
        Checks that client ID and client secret are present in the secrets store.
        '''
        try:
            _ = self.secrets_store.get("client_id")
            _ = self.secrets_store.get("client_secret")
        except KeyError as e:
            if str(e) in ["'client_id'", "'client_secret'"]:
                raise StravaApi.AuthError(err_type=StravaApi.AuthError.ErrorType.CLIENT,
                    message="Could not find {}".format(str(e)))

    def api_request(self, url, method="get", data=None, auth=True, post_file=None):
        '''
        Issues an API request, and checks returned headers and response.
        Returns API response.
        '''
        method = method.lower()
        assert method in ["get", "post", "put"]

        if auth:
            try:
                token = self.secrets_store.get("access_token")
            except KeyError as e:
                raise StravaApi.AuthError(err_type=StravaApi.AuthError.ErrorType.CLIENT,
                        message="Could not find {}".format(str(e)))
            headers = {"Authorization": "Bearer " + token}
        else:
            headers = None

        if method == "get":
            response = requests.get(url, headers=headers, verify=True)
        elif method == "post":
            file_dict = None
            if post_file:
                file_dict = {'file': open(post_file, 'rb')}
            response = requests.post(url, data=data, headers=headers, verify=True, files=file_dict)
        elif method == "put":
            response = requests.put(url, data=data, headers=headers, verify=True)

        response_data = json.loads(response.text)
        if response.status_code  not in [200, 201]:
            raise StravaApi.AuthError(err_type=StravaApi.AuthError.ErrorType.HTTP_RESP,
                message="API request got response:\r\n\n{}\r\n\n{}".format(
                    response.headers, response_data))
        return response_data

    def is_authed(self):
        '''
        Check to see if we have a valid access token and return True/False.
        Checks tokens, and tries an API transaction
        '''
        try:
            token = self.secrets_store.get("access_token")
            expiry = datetime.fromtimestamp(int(self.secrets_store.get("access_token_expire_time")),
                                            tz=timezone.utc)
        except KeyError:
            token = None
            expiry = None

        if ((not token) or (not expiry) or
            (expiry <= (datetime.now(timezone.utc) + timedelta(minutes=5)))):
            # No token, or the token will expire in a few minutes
            return False

        self.api_request(StravaApi.ATHLETE_URL)

        return True

    def get_auth(self):
        '''
        Get auth token, either by renewing an existing auth, or getting auth from scratch.
        '''
        try:
            # If we have a refresh token, try using it:
            _ = self.secrets_store.get("refresh_token")
            self.renew_auth()
        except KeyError as e:
            if str(e) == "'refresh_token'":
                # No refresh token in secret store, so have to start from scratch
                self.get_tokens()
            else:
                raise e

    def remove_auth(self):
        '''
        Removes auth and refresh tokens from the secrets store if they exist.
        '''
        try:
            self.secrets_store.delete("access_token")
        except KeyError:
            pass
        try:
            self.secrets_store.delete("access_token_expire_time")
        except KeyError:
            pass
        try:
            self.secrets_store.delete("refresh_token")
        except KeyError:
            pass

    def get_tokens(self):
        '''
        Get an auth code and exchange for auth and refresh tokens.
        '''
        self.check_secrets() # No need to proceed if we don't have these.
        # Launch the webserver thread to monitor for API response
        self.httpd = HTTPServer((StravaApi.SERVER_HOSTNAME,
            StravaApi.SERVER_PORT), StravaApi.AuthCodeHandler)
        self.httpd_thread = Thread(target=self._do_server, args=(1,), daemon=True)
        self.httpd_thread.start()
        auth_url = StravaApi.AUTH_URL + "?response_type=code" + \
                            "&client_id=" + self.secrets_store.get("client_id") + \
                            "&redirect_uri=" + StravaApi.SERVER_CALLBACK_URI + \
                            "&scope="+",".join(StravaApi.AUTH_SCOPE) + "&approval_prompt=auto"

        # Open web browser with authorization URL
            #webbrowser.open(authorization_redirect_url)
            # Using "webbrowser" causes XQuartz to launch, so do it a hacky way instead:
            # see: https://bugs.python.org/issue43111
        if sys.platform=="win32":
            os.startfile(auth_url)
        elif sys.platform=="darwin":
            subprocess.run(["open", auth_url], check=True)
        else:
            try:
                subprocess.run(["xdg-open", auth_url], check=True)
            except OSError:
                print("Please open this link in a browser: " + auth_url)
        # Wait for Strava API to reply with auth code
        auth_timeout_seconds_remaining = 30
        while not StravaApi.AuthCodeHandler.callback_received:
            time.sleep(1.0)
            auth_timeout_seconds_remaining -= 1
            if auth_timeout_seconds_remaining <= 0:
                self._kill_httpd()
                raise StravaApi.AuthError("Timed out waiting for auth code",
                                          err_type=StravaApi.AuthError.ErrorType.TIMEOUT)
        if not StravaApi.AuthCodeHandler.auth_code:
            self._kill_httpd()
            raise StravaApi.AuthError("Auth code not received.",
                                        err_type=StravaApi.AuthError.ErrorType.HTTP_RESP)
        if not all(x in StravaApi.AuthCodeHandler.auth_scopes for x in StravaApi.AUTH_SCOPE):
            self._kill_httpd()
            raise StravaApi.AuthError("Authorization scope error. Expected {} got {}".format(
                                        StravaApi.AUTH_SCOPE,
                                        StravaApi.AuthCodeHandler.auth_scopes),
                                        err_type=StravaApi.AuthError.ErrorType.SCOPE)
        auth_code = StravaApi.AuthCodeHandler.auth_code
        self._kill_httpd()

        # Exchange auth code for access token and refresh token
        self._send_token_request({
            "grant_type": "authorization_code",
            "code": auth_code,
            "client_id": self.secrets_store.get("client_id"),
            "client_secret": self.secrets_store.get("client_secret")})

    def renew_auth(self):
        '''
        Renew access token with refresh token.
        '''
        self._send_token_request({
            "grant_type": "refresh_token",
            "refresh_token": self.secrets_store.get("refresh_token"),
            "client_id": self.secrets_store.get("client_id"),
            "client_secret": self.secrets_store.get("client_secret")})

    def _send_token_request(self, data):
        response = self.api_request(StravaApi.TOKEN_URL, method="post",
                                data=data, auth=False)
        self.secrets_store.set("access_token", response["access_token"])
        self.secrets_store.set("refresh_token", response["refresh_token"])
        self.secrets_store.set("access_token_expire_time", str(response["expires_at"]))

class StravaData():
    """
    Interacts with the Strava API to perform various tasks.
    """
    ATHLETE_URL = "https://www.strava.com/api/v3/athlete"
    ACTIVITY_UPLOAD_URL = "https://www.strava.com/api/v3/uploads"
    ACTIVITY_URL = "https://www.strava.com/api/v3/activities"

    def __init__(self, api):
        self.api = api

    def get_athlete_name(self):
        '''
        Get the athlete first and last name (e.g. "Berto Lucci").
        '''
        resp = self.api.api_request(StravaData.ATHLETE_URL, method="get")
        return resp["firstname"] + " " + resp["lastname"]

    def upload_activity(self, activity_file, name, description="",
                     trainer=True, commute=False, activity_type="VirtualRide",
                     data_type="tcx", external_id=None, gear_id="PM Trainer"):
        '''
        Upload an activity to Strava, and return the Strava activity_id if successful.
        '''
        assert os.path.isfile(activity_file)
        assert data_type in ["fit", "fit.gz", "tcx", "tcx.gz", "gpx", "gpx.gz"]
        if not external_id:
            external_id=name
        # Upload the activity to Strava:
        data = {
            "name": name,
            "description": description,
            "trainer": str(trainer),
            "commute": str(commute),
            "data_type": data_type,
            "external_id": external_id
        }
        resp = self.api.api_request(StravaData.ACTIVITY_UPLOAD_URL, method="post",
                                    data=data, post_file=activity_file)
        # Wait for it to finish processing
        upload_id = resp["id"]
        timeout_seconds_remaining = 60
        while True:
            TIME_STEP_SECONDS = 10 # Strava says mean processing time is 8s for uploads
            time.sleep(TIME_STEP_SECONDS)
            timeout_seconds_remaining -= TIME_STEP_SECONDS

            resp = self.api.api_request(StravaData.ACTIVITY_UPLOAD_URL+"/"+str(upload_id),
                                        method="get")
            activity_id = resp["activity_id"]
            error = resp["error"]
            if activity_id:
                break
            if error:
                raise StravaApi.AuthError("Received an error from Strava: {}".format(error))
            if timeout_seconds_remaining <= 0:
                raise StravaApi.AuthError("Timed out waiting for response",
                                          err_type=StravaApi.AuthError.ErrorType.TIMEOUT)

        # Update activity with correct type and other fields
        data = {
            "name": name,
            "description": description,
            "trainer": str(trainer),
            "commute": str(commute),
            "type": activity_type,
            "gear_id": gear_id
        }
        resp = self.api.api_request(StravaData.ACTIVITY_URL+"/"+str(activity_id),
                                   method="put", data=data)
        return resp
