"""
Access the Strava API, including oauth2 authentication.
"""
from enum import Enum
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import re
from threading import Thread
import time
import subprocess
import sys
import requests


class StravaApi():
    """
    Access the Strava API, including oauth2 authentication.
    """
    AUTH_URL = "http://www.strava.com/oauth/authorize"
    TOKEN_URL = "https://www.strava.com/oauth/token"
    ATHLETE_URL = "https://www.strava.com/api/v3/athlete"

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
        auth_code = None
        def do_GET(self):
            '''
            Handles page request from Strava Oauth2 redirect.
            '''
            p = re.compile(r"code=(.+)&")
            code = p.findall(self.path)
            if code:
                StravaApi.AuthCodeHandler.auth_code = code[0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(bytes("<html><head><title>Strava Authentication Successful!</title></head>", "utf-8"))
            self.wfile.write(bytes("<p>authcode: {}</p></html>".format(StravaApi.AuthCodeHandler.auth_code), "utf-8"))

    def __init__(self, secrets_store):
        self.secrets_store = secrets_store
        self.httpd = None # only instantiate this if/when we need it
        self.httpd_thread = Thread(target=self._do_server, args=(1,), daemon=True)

    def _do_server(self, _):
        '''
        Thread function for http daemon thread.
        '''
        self.httpd.serve_forever()

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

    def api_request(self, url):
        '''
        Issues an API request, and checks returned headers and response.
        Returns API response.
        '''
        token = self.secrets_store.get("access_token")
        headers = {'Authorization': 'Bearer ' + token}
        response = requests.get(url, headers=headers, verify=True)
        response_data = json.loads(response.text)
        if ((response.status_code != 200) or
            ("Authorization Error" in response_data.values())):
            raise StravaApi.AuthError(err_type=StravaApi.AuthError.ErrorType.HTTP_RESP,
                message="Auth request got response:\r\n\n{}\r\n\n{}".format(response.headers, response_data))
        return response

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

    def get_tokens(self):
        '''
        Get an auth code and exchange for auth and refresh tokens.
        '''
        self.check_secrets() # No need to proceed if we don't have these.
        # Launch the webserver thread to monitor for API response
        self.httpd = HTTPServer((StravaApi.SERVER_HOSTNAME,
            StravaApi.SERVER_PORT), StravaApi.AuthCodeHandler)
        self.httpd_thread.start()
        authorization_redirect_url = StravaApi.AUTH_URL + "?response_type=code" + \
                            "&client_id=" + self.secrets_store.get("client_id") + \
                            "&redirect_uri=" + StravaApi.SERVER_CALLBACK_URI + \
                            "&scope=activity:write&approval_prompt=auto"
        # Open web browser with authorization URL
        #webbrowser.open(authorization_redirect_url)
        # Using "webbrowser" causes XQuartz to launch, so do it a hacky way instead:
        # see: https://bugs.python.org/issue43111
        if sys.platform=="win32":
            os.startfile(authorization_redirect_url)
        elif sys.platform=="darwin":
            subprocess.Popen(["open", authorization_redirect_url])
        else:
            try:
                subprocess.Popen(["xdg-open", authorization_redirect_url])
            except OSError:
                print("Please open this link in a browser: " + authorization_redirect_url)
        # Wait for Strava API to reply with auth code
        while not StravaApi.AuthCodeHandler.auth_code:
            #TODO: Timeout here? What happens if there is no internet?
            time.sleep(0.5)
        self.secrets_store.set("authorization_code", StravaApi.AuthCodeHandler.auth_code)
        self.httpd.server_close()
        self.httpd.shutdown()

        # Exchange auth code for access token and refresh token
        self._send_token_request({
            "grant_type": "authorization_code",
            "code": self.secrets_store.get("authorization_code"),
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

    def _send_token_request(self, post_data):
        response = requests.post(StravaApi.TOKEN_URL, data=post_data,
                                verify=True, allow_redirects=False)
        response_data = json.loads(response.text)
        if ((response.status_code != 200) or
            ("Authorization Error" in response_data.values())):
            raise StravaApi.AuthError(err_type=StravaApi.AuthError.ErrorType.HTTP_RESP,
                message="Auth request got response:\r\n\n{}\r\n\n{}".format(response.headers, response_data))
        
        self.secrets_store.set("access_token", response_data["access_token"])
        self.secrets_store.set("refresh_token", response_data["refresh_token"])
        self.secrets_store.set("access_token_expire_time", str(response_data["expires_at"]))

        assert self.is_authed()
