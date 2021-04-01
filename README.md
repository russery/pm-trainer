

# Installation Guide

*TODO - dependencies installation*

## Strava API Access
1. Follow instructions on [Strava API Getting Started](https://developers.strava.com/docs/getting-started/) to configure an app.
	Briefly:
	- Go to [Strava API Settings](https://www.strava.com/settings/api) in your Strava account, and fill out the required fields.
	- Get the `Client ID` and the `Client Secret` from the page after you've registered your API.


### Get access token, refresh token:
Response for expired code:
{
  "message": "Bad Request",
  "errors": [
    {
      "resource": "AuthorizationCode",
      "field": "",
      "code": "expired"
    }
  ]
}

Good response:
{
  "token_type": "Bearer",
  "expires_at": 1617168773,
  "expires_in": 21219,
  "refresh_token": "",
  "access_token": "",
  "athlete": {
...
  }
}


TODO:
- handle timeout on receiving auth code (no internet, etc.)
- handle settings file without client secrets (prompt user to enter secrets)
- Add settings button to do initial auth
- handle refresh of tokens
- unit tests!!
- Display a nice page after oauth redirect
- Handle user not giving proper permissions on auth page


