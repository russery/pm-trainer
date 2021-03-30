import os
import time
import PySimpleGUI as sg
import pmtrainer.settings as settings
from pmtrainer.workout_profile import Workout


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


def settings_dialog_popup(config):
    '''
    A dialog box to change persistent settings saved in the config file.
    '''
    FTP_RANGE = range(1,1000)
    UPDATE_HZ_RANGE = range(1,16,1)
    temp_workout = Workout(config.get("Workout"))
    log_directory = os.path.abspath(config.get("LogDirectory"))
    settings_layout = [
        [sg.Frame("User",
            [[sg.T("FTP:"),
              sg.Spin(values=list(FTP_RANGE), key="-FTP-",
                initial_value=config.get("FTPWatts"), size=(4,1)) ],
            [sg.T("Sensors")]], vertical_alignment="t"),
        sg.Frame("Workout",
            [[sg.T("Workout:"), sg.Input(config.get("Workout"), key="-WORKOUTPATH-", visible=False),
              sg.T(temp_workout.name), sg.B("Select", key="-WORKOUT-SEL-")],
            [sg.Multiline(temp_workout.description, size=(30,3), disabled=True)]],
            vertical_alignment="t")],
        [sg.Frame("System",
            [[sg.T("Log Path:"), sg.Input(log_directory, k="-LOGDIRECTORY-"),
              sg.FolderBrowse(button_text="Select", initial_folder=log_directory,
                target="-LOGDIRECTORY-")],
            [sg.T("Update Rate (Hz):"),
             sg.Spin(values=list(UPDATE_HZ_RANGE), initial_value=config.get("UpdateRateHz"),
                size=(3,1), key="-UPDATEHZ-")]])],
        [sg.B("Save", key="-SAVE-"),sg.B("Cancel", key="-CANCEL-")]
    ]
    settings_window = sg.Window("Settings", settings_layout,
        use_ttk_buttons=True, modal=True, keep_on_top=True, finalize=True, element_padding=(5,5))

    while True:
        e, v = settings_window.read()
        time.sleep(0.5)
        if e in (sg.WIN_CLOSED, "-CANCEL-"):
            settings_window.close()
            return
        if e == "-SAVE-":
            errors = []
            # Validate and save all values to config
            _validate_int_range(v["-FTP-"], "FTP Value", FTP_RANGE, errors)
            if not os.path.exists(v["-LOGDIRECTORY-"]):
                errors.append("Invalid log path: {}".format(v["-LOGDIRECTORY-"]))
            # TODO: Validate workout
            _validate_int_range(v["-UPDATEHZ-"], "Update Rate", UPDATE_HZ_RANGE, errors)

            if errors:
                sg.Popup("\n".join(errors), title="Bad Settings")
            else:
                config.set("FTPWatts", str(v["-FTP-"]))
                config.set("LogDirectory", v["-LOGDIRECTORY-"])
                config.set("Workout", v["-WORKOUTPATH-"])
                config.set("UpdateRateHz", str(v["-UPDATEHZ-"]))
                settings_window.close()
                config.write_settings(config.get("SettingsFile"))
                return
        else:
            print(e)