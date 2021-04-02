"""
Provides GUI windows for changing settings from configuration file.
"""

import os
import PySimpleGUI as sg
from pmtrainer.profile_plotter import plot_blocks
from pmtrainer.workout_profile import Workout
from pmtrainer.strava_api import StravaApi, StravaData

def _validate_int_range(val, val_name, val_range, error_list):
    '''
    Checks if a value is an integer in a range and generates
    an error message string if it is not, or is not an integer.
    If an error message is generated, it is appended to the error_list.
    '''
    try:
        if int(val) not in val_range:
            raise ValueError
    except ValueError:
        error_list.append("Invalid {}: {} not between {}-{}".format(
            val_name, val, val_range[0], val_range[-1]))

def _set_workout_fields(window, workout_path):
    wkt = Workout(workout_path)
    window["-WKT-NAME-"].update("Name: " + wkt.name)
    window["-WKT-DUR-"].update("Duration: {:d}min".format(int(wkt.duration_s / 60)))
    window["-WKT-DESC-"].update(wkt.description)

def _set_strava_status(window, strava):
    if strava.is_authed():
        athlete_name = StravaData(strava).get_athlete_name()
        window["-STRAVA-AUTH-STATUS-"].Update("Connected to Strava as {}.".format(athlete_name))
    else:
        window["-STRAVA-AUTH-STATUS-"].Update("Not connected to Strava.")

def _highlight_active_workout(window, workouts, workout_path):
    for w in workouts.values():
        if workout_path == w["path"]:
            window[w["workout"].name+"-sel"].Widget.config(background="red")
        else:
            window[w["workout"].name+"-sel"].Widget.config(background="gray")

def _strava_client_info_popup():
    layout = [[sg.Text("Missing Strava Client info.\r\n" \
                       "Please get 'client_id' and 'client_secret' from Strava " \
                       "as described here:\r"\
                       "https://github.com/russery/pm-trainer#strava-api-access", (60,4))],
              [sg.T("client_id:", (15,1)),
               sg.I("", (6,1), key="-CLIENT-ID-", focus=True, tooltip="client_id")],
              [sg.T("client_secret:", (15,1)),
               sg.I("", (41,1), key="-CLIENT-SECRET-", tooltip="client_secret")],
              [sg.B("Save", key="-SAVE-"),sg.B("Cancel", key="-CANCEL-")]]
    window = sg.Window("Enter Strava Client Info", layout,
        use_ttk_buttons=True, modal=True, keep_on_top=True, finalize=True, element_padding=(5,5))

    while True:
        e, _ = window.read()
        if e in [sg.WIN_CLOSED, "-CANCEL-"]:
            window.close()
            return None, None
        elif e == "-SAVE-":
            client_id = window["-CLIENT-ID-"].get()
            client_secret = window["-CLIENT-SECRET-"].get()
            window.close()
            return client_id, client_secret

def workout_selection_popup(workout_path):
    '''
    Find all the workouts in the passed-in directory, plot them,
    and allow the user to select one.
    '''

    # Find all the valid workout files:
    workout_dir = os.path.dirname(workout_path)
    all_files = os.listdir(workout_dir)
    workouts = {}
    for f in all_files:
        if f.endswith(".yaml"):
            wpath = workout_dir + "/" + f
            w = Workout(wpath)
            workouts[w.name] = {"workout": w, "path": wpath}

    # Create a window with frames for each workout file:
    layout = []
    for w in workouts.values():
        workout = w["workout"]
        frame = sg.Frame(title=workout.name, key=workout.name,
            layout=[[
                    # Graph background color will indicate selected workout:
                    sg.Column([[sg.Graph(canvas_size=(8,60),
                                         graph_bottom_left=(0,0), graph_top_right=(8,60),
                                         key=workout.name+"-sel")]]),
                    sg.Column([
                        [sg.T("{} - {:3.0f}min".format(workout.description,
                                                       workout.duration_s/60))],
                        [sg.Graph(key=workout.name+"-graph",
                           canvas_size=(300,30),
                           graph_bottom_left=(0,0),
                           graph_top_right=(300,30),
                           enable_events=True)]])
                    ]])
        layout.extend([[frame]])
    layout.extend([[sg.B("Save", key="-SAVE-"),sg.B("Cancel", key="-CANCEL-")]])
    window = sg.Window("Select a Workout", layout,
        use_ttk_buttons=True, modal=True, keep_on_top=True, finalize=True, element_padding=(5,5))

    # Plot the workouts in each frame and highlight the active workout:
    for w in workouts.values():
        workout = w["workout"]
        _, max_power = workout.get_min_max_power()
        blocks = workout.get_all_blocks()
        plot_blocks(window[workout.name+"-graph"], blocks, (0.0, max_power))

    _highlight_active_workout(window, workouts, workout_path)

    new_workout_path = workout_path
    while True:
        e, _ = window.read()
        if e in (sg.WIN_CLOSED, "-CANCEL-"):
            window.close()
            return workout_path
        elif e == "-SAVE-":
            window.close()
            return new_workout_path
        elif "-graph" in e: # Click events on a workout graph
            # Highlight the active workout and set it as the newly selected workout:
            new_workout_name = e.rstrip("-graph")
            new_workout_path = workouts[new_workout_name]["path"]
            _highlight_active_workout(window, workouts, new_workout_path)
        else:
            print(e)

def settings_dialog_popup(config):
    '''
    A dialog box to change persistent settings saved in the config file.
    '''
    FTP_RANGE = range(1,1000)
    WEIGHT_RANGE = range(5,250)
    log_directory = os.path.abspath(config.get("LogDirectory"))
    settings_layout = [
        [sg.Frame("User",
            [[sg.T("FTP watts:", (12,1)),
              sg.Spin(values=list(FTP_RANGE), key="-FTP-",
                initial_value=config.get("FTPWatts"), size=(5,1)) ],
              [sg.T("Rider kilograms:", (12,1)),
              sg.Spin(values=list(WEIGHT_RANGE), key="-RIDER-KG-",
                initial_value=config.get("RiderWeightKg"), size=(5,1)) ],
              [sg.T("Bike kilograms:", (12,1)),
              sg.Spin(values=list(WEIGHT_RANGE), key="-BIKE-KG-",
                initial_value=config.get("BikeWeightKg"), size=(5,1)) ]],
              vertical_alignment="t"),
        sg.Frame("Workout",
            [[sg.T("name", (30,1), key="-WKT-NAME-"), sg.B("Select", key="-WKT-SEL-BTTN-")],
             [sg.T("duration", (30,1), key="-WKT-DUR-")],
             [sg.T("description", (40,2), key="-WKT-DESC-")]],
             vertical_alignment="t")],
        [sg.Frame("Activity Tracking",
            [[sg.B("Strava Connect", key="-STRAVA-BTTN-"),
              sg.T("Auth status", (30,1), key="-STRAVA-AUTH-STATUS-")],
             [sg.T("Local Log Path:"), sg.Input(log_directory, k="-LOGDIRECTORY-"),
              sg.FolderBrowse(button_text="Select", initial_folder=log_directory,
                              target="-LOGDIRECTORY-")]])],
        [sg.B("Save", key="-SAVE-"),sg.B("Cancel", key="-CANCEL-")]
    ]
    window = sg.Window("Settings", settings_layout,
        use_ttk_buttons=True, modal=True, keep_on_top=True, finalize=True, element_padding=(5,5))

    # Initialize workout info:
    _set_workout_fields(window, config.get("Workout"))

    # Initialize Strava link status:
    strava = StravaApi(config)
    _set_strava_status(window, strava)

    window.refresh()

    while True:
        e, v = window.read()
        if e in (sg.WIN_CLOSED, "-CANCEL-"):
            window.close()
            return
        if e == "-SAVE-":
            errors = []
            # Validate and save all values to config
            _validate_int_range(v["-FTP-"], "FTP Value", FTP_RANGE, errors)
            if not os.path.exists(v["-LOGDIRECTORY-"]):
                errors.append("Invalid log path: {}".format(v["-LOGDIRECTORY-"]))
            # TODO: Validate workout

            if errors:
                sg.Popup("\n".join(errors), title="Bad Settings")
            else:
                config.set("FTPWatts", str(v["-FTP-"]))
                config.set("RiderWeightKg", str(v["-RIDER-KG-"]))
                config.set("BikeWeightKg", str(v["-BIKE-KG-"]))
                config.set("LogDirectory", v["-LOGDIRECTORY-"])
                window.close()
                return
        if e == "-WKT-SEL-BTTN-":
            new_workout_path = workout_selection_popup(config.get("Workout"))
            _set_workout_fields(window, new_workout_path)
            config.set("Workout", new_workout_path)
        if e == "-STRAVA-BTTN-":
            strava.remove_auth()
            while not strava.is_authed():
                try:
                    strava.get_auth()
                except StravaApi.AuthError as e:
                    if e.err_type == StravaApi.AuthError.ErrorType.CLIENT:
                        client_id, client_secret = _strava_client_info_popup()
                        if client_id and client_secret:
                            config.set("client_id", client_id)
                            config.set("client_secret", client_secret)
                        else:
                            break
                    elif e.err_type in [StravaApi.AuthError.ErrorType.HTTP_RESP,
                                        StravaApi.AuthError.ErrorType.TIMEOUT,
                                        StravaApi.AuthError.ErrorType.SCOPE]:
                        try_again = sg.PopupYesNo("Could not reach Strava. Try again?")
                        if try_again == "No":
                            break
                    else:
                        raise e
            _set_strava_status(window, strava)
        else:
            print(e)
