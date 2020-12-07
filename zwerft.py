"""
Logs trainer rides or something.
"""
import os
import sys
import time
from datetime import datetime as dt
import PySimpleGUI as sg
import profile_plotter
import settings
from ant_sensors import AntSensors
import assets.icons
from workout_profile import Workout
from tcx_file import Tcx, Point

TEST_MODE = True

DEFAULT_SETTINGS = {
   # User / session settings:
   "FTPWatts": 200,
   "Workout": "workouts/sweet_spot.yaml",

   # Window / system settings
   "LogDirectory": "./logs",
   "SettingsFile": "zwerft_settings.ini",
   "UpdateRateHz": 10
}

PLOT_MARGINS_PERCENT = 10 # Percent of plot to show beyond limits
HEART_RATE_LIMITS = (100, 200)

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

def _exit_zwerft(status=0):
    """
    Exit cleanly, closing window, writing logfile, and freeing ANT+ resources.
    """
    if logfile:
        logfile.flush()
    if window:
        window.close()
    if sensors:
        sensors.close()
    sys.exit(status)

def _update_sensor_status_indicator(element, sensor_status):
    """
    Change color of the selected element based on the status of an ANT+ sensor.
    """
    if sensor_status == AntSensors.SensorStatus.State.NOTCONNECTED:
        element.update(background_color="red")
    elif sensor_status == AntSensors.SensorStatus.State.CONNECTED:
        element.update(background_color="green")
    elif sensor_status == AntSensors.SensorStatus.State.STALE:
        element.update(background_color="yellow")

def _settings_dialog(config):
    FTP_RANGE = range(1,1000)
    UPDATE_HZ_RANGE = range(1,16,1)
    temp_workout = Workout(config.get("Workout"))
    log_directory = os.path.abspath(config.get("LogDirectory"))
    settings_layout = [
        [sg.Frame("User",
            [[sg.T("FTP:"),
              sg.Spin(values=[i for i in FTP_RANGE], key="-FTP-",
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
             sg.Spin(values=[i for i in UPDATE_HZ_RANGE], initial_value=config.get("UpdateRateHz"),
                size=(3,1), key="-UPDATEHZ-")]])],
        [sg.B("Save", key="-SAVE-"),sg.B("Cancel", key="-CANCEL-")]
    ]
    settings_window = sg.Window("Settings", settings_layout,
        use_ttk_buttons=True, modal=True, keep_on_top=True, finalize=True, element_padding=(5,5))

    while True:
        e, v = settings_window.read()
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

def _get_workout_from_config(config):
    # Initialize workout plot with workout profile
    wkout = Workout(config.get("Workout"))
    min_p, max_p = profile_plotter.get_min_max_power(wkout.get_all_blocks())
    return wkout, min_p, max_p

def _start_log(ldir):
    if not os.path.exists(ldir):
        os.makedirs(ldir)
    lfile = Tcx()
    lfile.start_log("{}/{}.tcx".format(
        ldir, dt.now().strftime("%Y%m%d_%H%M%S")))
    lfile.start_activity(activity_type=Tcx.ActivityType.OTHER)
    return lfile

def _scale_plot_margins(y_lims):
    return ((y_lims[0]*(1 - PLOT_MARGINS_PERCENT/100)),
                y_lims[1]*(1 + PLOT_MARGINS_PERCENT/100))

def _plot_workout(graph, wkout, y_lims):
    y_lims = _scale_plot_margins(y_lims)
    profile_plotter.plot_blocks(graph, wkout.get_all_blocks(), y_lims)

def _plot_trace(graph, val, y_lims, size=3, color='red'):
    y_lims = _scale_plot_margins(y_lims)
    profile_plotter.plot_trace(graph, val, y_lims, size=size, color=color)

# Load settings
cfg = settings.Settings()
if os.path.isfile(DEFAULT_SETTINGS["SettingsFile"]):
    cfg.load_settings(filename=DEFAULT_SETTINGS["SettingsFile"])
else:
    cfg.load_settings(defaults={"DEFAULT": DEFAULT_SETTINGS})

sg.theme("DarkBlack")

# Attach to ANT+ dongle and start searching for sensors
while True:
    try:
        sensors = AntSensors()
        sensors.connect()
        break
    except AntSensors.SensorError as e:
        if e.err_type == AntSensors.SensorError.ErrorType.USB:
            sg.Popup("USB Dongle Error", "Could not connect to ANT+ dongle "
             "- check USB connection and try again",
                custom_text="Exit", line_width=50, keep_on_top=True, any_key_closes=True)
            # TODO: Keep the application open and try again - this should be recoverable
            _exit_zwerft(-1)
        else:
            print("Caught sensor error {}".format(e.err_type))
            _exit_zwerft(-1)
    time.sleep(1)
    sensors.close()
    del sensors

# Set up main window
layout = [[sg.T("Time:"), sg.T("HH:MM:SS", (8,1), relief="raised",
                             key="-TIME-",justification="L", font="20"),
           sg.T("HR:"), sg.T("000",(3,1),relief="raised",
                             key="-HEARTRATE-",justification="L",
                             text_color="black", font="20"),
           sg.T("Watts:"),sg.T("0000",(4,1),relief="raised",
                               key="-POWER-",justification="L",
                               text_color="black", font="20"),
           sg.T("Cadence:"),sg.T("000",(3,1),relief="raised",
                                 key="-CADENCE-",justification="L",
                                 text_color="black", font="20"),
           sg.T("Target Power:"),sg.T("0000",(4,1),relief="raised",
                                 key="-TARGET-",justification="L", font="20"),
           sg.T("Remaining:"),sg.T("MM:SS",(5,1),relief="raised",
                                 key="-REMAINING-",justification="L", font="20"),
           sg.Button('', image_data=assets.icons.settings,
                button_color=(sg.theme_background_color(),sg.theme_background_color()),
                border_width=0, key='-SETTINGS-')],
           [sg.Graph(canvas_size=(800, 100), graph_bottom_left=(0, 0),
                     graph_top_right=(800, 100), background_color='black',
                     key='-PROFILE-')]]
window = sg.Window("Zwerft", layout, keep_on_top=True, use_ttk_buttons=True,
    alpha_channel=0.9, finalize=True, element_padding=(0,0))


workout, min_power, max_power = _get_workout_from_config(cfg)
_plot_workout(window["-PROFILE-"], workout, (min_power, max_power))

log_dir = cfg.get("LogDirectory")
logfile = _start_log(log_dir)

start_time = dt.now()

# Main loop
# HACKY TESTING CODE
if TEST_MODE:
    test_data = Tcx()
    test_data.open_log("sample_files/20201205_091538.tcx")
    test_data.get_activity()
    p = test_data.get_next_point()
    test_start_time = p.time

update_ms = 1000 / float(cfg.get("UpdateRateHz"))
ftp_watts = float(cfg.get("FTPWatts"))
while True:
    try:
        # Handle window events
        event, _ = window.read(timeout=update_ms)
        if event == sg.WIN_CLOSED:
            _exit_zwerft()
        if event == "-SETTINGS-":
            window.Disappear()
            _settings_dialog(cfg)
            window.Reappear()
            # Update workout plot:
            w_new, min_new, max_new = _get_workout_from_config(cfg)
            if w_new.name != workout.name:
                workout, min_power, max_power = w_new, min_new, max_new
                _plot_workout(window["-PROFILE-"], workout, (min_power, max_power))
            # Update log directory and start new log if it's changed:
            dir_new = cfg.get("LogDirectory")
            if dir_new != log_dir:
                log_dir = dir_new
                logfile = _start_log(log_dir)
            # Update other values:
            update_ms = 1000 / float(cfg.get("UpdateRateHz"))
            ftp_watts = float(cfg.get("FTPWatts"))

        # Update text display:
        heartrate = sensors.heartrate_bpm
        power = sensors.power_watts
        cadence = sensors.cadence_rpm


        elapsed_time = dt.now() - start_time
        # HACKY TEST CODE:
        if TEST_MODE:
            while (p.time - test_start_time) <= elapsed_time:
                heartrate = p.heartrate_bpm
                power = p.power_watts
                cadence = p.cadence_rpm
                p = test_data.get_next_point()

        window["-HEARTRATE-"].update(heartrate)
        window["-POWER-"].update(power)
        window["-CADENCE-"].update(cadence)
        window["-TIME-"].update("{:02d}:{:02d}:{:02d}".format(
            int(elapsed_time.seconds/3600) % 24,
            int(elapsed_time.seconds/60) % 60,
            elapsed_time.seconds % 60))

        # Handle sensor status:
        _update_sensor_status_indicator(window["-HEARTRATE-"], sensors.heart_rate_status)
        _update_sensor_status_indicator(window["-POWER-"], sensors.power_meter_status)
        _update_sensor_status_indicator(window["-CADENCE-"], sensors.power_meter_status)

        # Update workout params:
        power_target = workout.power_target(elapsed_time.seconds)
        if power_target:
            power_target = "{:4.0f}".format(power_target*ftp_watts)
        else:
            power_target = ""
        window['-TARGET-'].update(power_target)
        remain_s = workout.block_time_remaining(elapsed_time.seconds)
        window['-REMAINING-'].update("{:2.0f}:{:02.0f}".format(
            int(remain_s / 60) % 60, remain_s % 60))

        # Update plot:
        norm_time = elapsed_time.seconds / workout.duration_s
        if power:
            _plot_trace(window["-PROFILE-"],
                (norm_time, power / ftp_watts),
                (min_power, max_power), color="red")
        if heartrate:
            _plot_trace(window["-PROFILE-"],
                (norm_time, (heartrate-HEART_RATE_LIMITS[0])/HEART_RATE_LIMITS[1]),
                (0,0.5), color="cyan")

        # Update log file
        if ((sensors.heart_rate_status == AntSensors.SensorStatus.State.CONNECTED) and
            (sensors.power_meter_status == AntSensors.SensorStatus.State.CONNECTED)):
            logfile.add_point(heartrate_bpm=heartrate, cadence_rpm=cadence, power_watts=power)
            logfile.lap_stats(total_time_s=elapsed_time.seconds)
            logfile.flush()

    except AntSensors.SensorError as e:
        if e.err_type == AntSensors.SensorError.ErrorType.USB:
            print("Could not connect to ANT+ dongle - check USB connection")
        elif e.err_type == AntSensors.SensorError.ErrorType.TIMEOUT:
            print("Starting search for sensors again...")
            sensors.connect()
            continue
        else:
            print("Caught sensor error {}".format(e.err_type))
