

# Installation Guide

*TODO - dependencies installation*

## Strava API Access
1. Follow instructions on [Strava API Getting Started](https://developers.strava.com/docs/getting-started/) to configure an app.
	Briefly:
	- Go to [Strava API Settings](https://www.strava.com/settings/api) in your Strava account, and fill out the required fields.
	- Get the `Client ID` and the `Client Secret` from the page after you've registered your API.



TODO:
- Flesh out README with details of initial setup (client secrets, etc)
- Refactor pm_trainer as a class, to make data sharing between functions less clunky. Maybe refactor into multiple classes, too?
- Rename / Refactor AuthError and error codes to cover both authorization and other API errors
- Figure out why replay mode uses so much CPU
- Handle USB disconnect during ride (can happen when computer goes to sleep)
