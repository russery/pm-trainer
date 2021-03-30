import os
import time
import PySimpleGUI as sg
import pmtrainer.settings as settings
from pmtrainer.profile_plotter import plot_blocks
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

def workout_selection_popup(workout_dir):
    '''
    Find all the workouts in the passed-in directory, plot them,
    and allow the user to select one.
    '''
    all_files = os.listdir(workout_dir)
    workout_files = []
    selector_layout = []
    
    # Find all the valid workout files:
    for f in all_files:
        if f.endswith(".yaml"):
            workout_files.extend([f])

    # Create a window with frames for each workout file:
    for w in workout_files:
        workout = Workout(workout_dir + "/" + w)
        graph = [[sg.Graph(key=workout.name,
                           canvas_size=(300,30),
                           graph_bottom_left=(0,0),
                           graph_top_right=(300,30))]]
        workout_frame = sg.Frame(title=workout.name, layout=graph)
        selector_layout.extend([[workout_frame]])
    selector_window = sg.Window("Select a Workout", selector_layout,
        use_ttk_buttons=True, modal=True, keep_on_top=True, finalize=True, element_padding=(5,5))
    
    # Plot the workouts in each frame:
    for w in workout_files:
        workout = Workout(workout_dir + "/" + w)
        _, max_power = workout.get_min_max_power()
        blocks = workout.get_all_blocks()
        plot_blocks(selector_window[workout.name], blocks, (0.0, max_power))

def settings_dialog_popup(config):
    '''
    A dialog box to change persistent settings saved in the config file.
    '''
    FTP_RANGE = range(1,1000)
    wkt = Workout(config.get("Workout"))
    log_directory = os.path.abspath(config.get("LogDirectory"))
    settings_layout = [
        [sg.Frame("User",
            [[sg.T("FTP:"),
              sg.Spin(values=list(FTP_RANGE), key="-FTP-",
                initial_value=config.get("FTPWatts"), size=(4,1)) ],
            [sg.T("Sensors:")]], vertical_alignment="t"),
        sg.Frame("Workout",
            [[sg.T("Name: " + wkt.name), sg.B("Select", key="-WORKOUT-SEL-")],
             [sg.T("Duration: {:d}min".format(int(wkt.duration_s / 60)))],
            [sg.T(wkt.description)]],
            vertical_alignment="t")],
        [sg.Frame("System",
            [[sg.T("Log Path:"), sg.Input(log_directory, k="-LOGDIRECTORY-"),
              sg.FolderBrowse(button_text="Select", initial_folder=log_directory,
                target="-LOGDIRECTORY-")]])],
        [sg.B("Save", key="-SAVE-"),sg.B("Cancel", key="-CANCEL-")]
    ]
    settings_window = sg.Window("Settings", settings_layout,
        use_ttk_buttons=True, modal=True, keep_on_top=True, finalize=True, element_padding=(5,5))

    while True:
        e, v = settings_window.read()
        #time.sleep(0.5)
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

            if errors:
                sg.Popup("\n".join(errors), title="Bad Settings")
            else:
                config.set("FTPWatts", str(v["-FTP-"]))
                config.set("LogDirectory", v["-LOGDIRECTORY-"])
                settings_window.close()
                config.write_settings(config.get("SettingsFile"))
                return
        if e == "-WORKOUT-SEL-":
            wkt_dir = os.path.dirname(config.get("Workout"))
            workout_selection_popup(wkt_dir)
            config.set("Workout", "asdf")
        else:
            print(e)
