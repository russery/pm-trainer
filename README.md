
# PM Trainer
This is a simple indoor bicycle training application, similar to a very stripped-down version of TrainerRoad or Zwift.

It has the following major features:

- Creates target-power workout profiles for the user to follow
- Displays and logs ANT+ heartrate and power data
- Uploads your workout to Strava

# Installation Guide

*TODO - dependencies installation*


## Quickstart:

1. Configure [Strava API access](#strava-api-access) as described below (if you want automatic uploads)
1. Plug in your ANT+ dongle and wake up your heartrate and power sensors
1. Launch PM trainer: `python pm_trainer.py`
	- Your ANT+ dongle and sensors should automatically be detected.
1. Select a workout:
	- Click the gear icon (settings)
	- Under the "Workout" section click "Select"
	- Click on the profile of the workout you want, then click "Select"
	- Click "Save" on the settings dialog
1. **Ride your heart out!**
1. When the workout is over, close PM Trainer, and you'll be prompted if you want to save your workout to Strava (if you've configured Strava API access).
	- If you don't want to link your Strava account there will be a \*.tcx file in the log directory configured in the Settings dialog. You can manually upload this file to Strava.



## Strava API Access
I expect each user to set up their own Strava API client, so to use the Strava integration there are a few annoying steps required:

1. Follow instructions on [Strava API Getting Started](https://developers.strava.com/docs/getting-started/) to configure an app. Briefly:
	- Go to [Strava API Settings](https://www.strava.com/settings/api) in your Strava account, and fill out the required fields.
	- Get the `Client ID` and the `Client Secret` from the page after you've registered your API.
1. Enter these items in the PM Trainer settings dialog:
	- Launch PM Trainer, click the Settings button (gear icon)
	- Click the "Strava Connect" button in this dialog
	- There will then be a popup window prompting you to enter these values. Enter them in the required fields, and then click "Save"
1. That's all folks! At this point, PM Trainer will open a browser window requesting you to authenticate the app with Strava (standard Oauth2 workflow).

## Connecting Sensors


# Running and Using
[] TODO

## Compatible Sensors and Dongles


# Creating Workouts
[] TODO

TODO:

- Refactor pm_trainer as a class, to make data sharing between functions less clunky. Maybe refactor into multiple classes, too?
- Rename / Refactor AuthError and error codes to cover both authorization and other API errors
- Figure out why replay mode uses so much CPU
- Handle USB disconnect during ride (can happen when computer goes to sleep)