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
from tcx_file import Tcx

CONFIG_FILENAME = "zwerft_settings.ini"
DEFAULT_SETTINGS = {
   # User / session settings:
   "FTPWatts": 200,
   "Workout": "workouts/short_stack.yaml",

   # Window / system settings
   "LogDirectory": "logs",
   "UpdateRateHz": 10
}

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
    config_bak = config
    settings_layout = [[sg.T("Hello is this the krusty krab?")],
        [sg.B("Save", key="-SAVE-"),sg.B("Cancel", key="-CANCEL-")]]
    settings_window = sg.Window("Settings", settings_layout, grab_anywhere=True,
        use_ttk_buttons=True, modal=True, keep_on_top=True)
    settings_window.Finalize()

    while True:
        event, values = settings_window.read()
        if (event == sg.WIN_CLOSED) or (event == "-CANCEL-"):
            settings_window.close()
            return config_bak
        if event == "-SAVE-":
            settings_window.close()
            return config

# Load settings
cfg = settings.Settings()
if os.path.isfile(CONFIG_FILENAME):
    cfg.load_settings(filename=CONFIG_FILENAME)
else:
    cfg.load_settings(defaults=DEFAULT_SETTINGS)

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
sg.SetOptions(element_padding=(0,0))
layout = [[sg.T("Time:"), sg.T("HH:MM:SS",relief="raised",
                             key="-TIME-",justification="L"),
           sg.T("HR:"), sg.T("000",(3,1),relief="raised",
                             key="-HEARTRATE-",justification="L"),
           sg.T("Watts:"),sg.T("0000",(4,1),relief="raised",
                               key="-POWER-",justification="L"),
           sg.T("Cadence:"),sg.T("000",(3,1),relief="raised",
                                 key="-CADENCE-",justification="L"),
           sg.T("Target Power:"),sg.T("0000",(4,1),relief="raised",
                                 key="-TARGET-",justification="L"),
           sg.T("Remaining:"),sg.T("MM:SS",(4,1),relief="raised",
                                 key="-REMAINING-",justification="L"),
           sg.Button('', image_data=assets.icons.settings,
                button_color=(sg.theme_background_color(),sg.theme_background_color()),
                border_width=0, key='-SETTINGS-')],
           [sg.Graph(canvas_size=(800, 100), graph_bottom_left=(0, 0),
                     graph_top_right=(800, 100), background_color='black',
                     key='-PROFILE-')]]
window = sg.Window("Zwerft", layout, grab_anywhere=True, use_ttk_buttons=True, alpha_channel=0.9)
window.Finalize()
window.BringToFront()


# Initialize workout plot with workout profile
workout = Workout(cfg.get_setting("Workout"))
blocks = workout.get_all_blocks()
max_power = profile_plotter.get_max_power(blocks) * 1.2
profile_plotter.plot_blocks(window["-PROFILE-"], blocks, max_power)


log_dir = cfg.get_setting("LogDirectory")
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
logfile = Tcx(file_name="{}/{}.tcx".format(
    log_dir, dt.now().strftime("%Y%m%d_%H%M%S")))
logfile.start_activity(activity_type=Tcx.ActivityType.OTHER)
start_time = dt.now()

# Main loop
update_ms = 1000 / float(cfg.get_setting("UpdateRateHz"))
while True:
    try:
        # Handle window events
        event, values = window.read(timeout=update_ms)
        if event == sg.WIN_CLOSED:
            _exit_zwerft()
        if event == "-SETTINGS-":
            _settings_dialog(cfg)

        # Update text display
        heartrate = sensors.heartrate_bpm
        power = sensors.power_watts
        cadence = sensors.cadence_rpm
        elapsed_time = dt.now() - start_time
        window["-HEARTRATE-"].update(heartrate)
        window["-POWER-"].update(power)
        window["-CADENCE-"].update(cadence)
        window["-TIME-"].update("{:02d}:{:02d}:{:02d}".format(
            int(elapsed_time.seconds/3600),
            int(elapsed_time.seconds/60),
            elapsed_time.seconds % 60))

        # Handle sensor status:
        _update_sensor_status_indicator(window["-HEARTRATE-"], sensors.heart_rate_status)
        _update_sensor_status_indicator(window["-POWER-"], sensors.power_meter_status)
        _update_sensor_status_indicator(window["-CADENCE-"], sensors.power_meter_status)

        # Update workout params:
        window['-TARGET-'].update("{:4.0f}".format(
            workout.power_target(elapsed_time.seconds)*float(cfg.get_setting("FTPWatts"))))
        remain_s = workout.block_time_remaining(elapsed_time.seconds)
        window['-REMAINING-'].update("{:2.0f}:{:02.0f}".format(
            remain_s / 60, remain_s % 60))

        # Update plot:
        if power:
            print(elapsed_time.seconds,workout.duration_s)
            time_percent = elapsed_time.seconds / workout.duration_s
            profile_plotter.plot_trace(window['-PROFILE-'], (time_percent,power), max_power)

        # Update log file
        if ((sensors.heart_rate_status == AntSensors.SensorStatus.State.CONNECTED) and
            (sensors.power_meter_status == AntSensors.SensorStatus.State.CONNECTED)):
            logfile.add_point(heartrate_bpm=heartrate, cadence_rpm=cadence, power_watts=power)
            logfile.lap_stats(total_time_s=elapsed_time.seconds)

    except AntSensors.SensorError as e:
        if e.err_type == AntSensors.SensorError.ErrorType.USB:
            print("Could not connect to ANT+ dongle - check USB connection")
        elif e.err_type == AntSensors.SensorError.ErrorType.TIMEOUT:
            print("Starting search for sensors again...")
            sensors.connect()
            continue
        else:
            print("Caught sensor error {}".format(e.err_type))
