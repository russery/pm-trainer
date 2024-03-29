'''
Power-Mode Trainer:
Logs bike trainer rides, enables displaying a workout profile with
target power segments, and interfaces to bike trainer sensors over ANT+.

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
'''

import argparse
import os
import sys
import time
import datetime as dt
import PySimpleGUI as sg

import profile_plotter as profile_plotter
import settings as settings
from strava_api import StravaApi, StravaData
from ant_sensors import AntSensors
import assets.icons as icons
from workout_profile import Workout
from tcx_file import Tcx, Point
from bug_indicator import BugIndicator
from bike_sim import BikeSim
from settings_dialog import settings_dialog_popup, \
                                      set_strava_status, handle_strava_auth_button

DFT_PMTRAINER_DIR = os.path.expanduser("~/pmtrainer/")

DEFAULT_SETTINGS = {
   # User / session settings:
   "FTPWatts": 230,
   "RiderWeightKg": 70,
   "BikeWeightKg": 10,
   "Workout": "workouts/short_stack.yaml",

   # Window / system settings
   "LogDirectory": DFT_PMTRAINER_DIR+"logs",
   "SettingsFile": DFT_PMTRAINER_DIR+"pm_trainer_settings.ini",
}

PLOT_MARGINS_PERCENT = 10 # Percent of plot to show beyond limits
HEART_RATE_LIMITS = (100, 200)
POWER_BUG_LIMITS_WATTS = 100 # Vertical size of power bug in watts
UPDATE_RATE_MS = 100

parser = argparse.ArgumentParser(description='Command line options')
parser.add_argument("-r", "--replay", default=None,
                    help="Enable replay mode and pass in file to replay")
parser.add_argument("-s", "--speed", default=1.0, type=float,
                    help="Enable replay mode and pass in file to replay")
args = parser.parse_args()
if args.replay:
    REPLAY_MODE = True
    if not os.path.isfile(args.replay):
        print("\nERROR: Invalid file {}".format(args.replay))
        sys.exit()
    print("\nReplaying {} at {:2.1f}x speed".format(args.replay, args.speed))
else:
    REPLAY_MODE = False

class Timer():
    '''
    A timer that returns time as a datetime timedelta. The timer only updates
    when the update() method is called, so that the same time can be used in
    multiple places in a loop.
    '''
    def __init__(self, replay=False, tick_ms=100.0):
        self.replay=replay
        self.start_time = None
        self.elapsed_time = None
        self.tick_ms = tick_ms

    def start(self, current_time=dt.datetime.now()):
        '''
        Start the timer.
        '''
        self.start_time = current_time
        self.elapsed_time = dt.timedelta(seconds=0)

    def get_time(self):
        '''
        Return the timedelta from when the timer was started to
        when it was updated.
        '''
        return self.elapsed_time

    def update(self):
        '''
        Update the elapsed time.
        '''
        if self.replay:
            self.elapsed_time += dt.timedelta(seconds=self.tick_ms / 1000.0)
        else:
            self.elapsed_time = dt.datetime.now() - self.start_time

def _avg_val(running_avg_val, new_val, avg_window=10):
    '''
    Keeps a running average of values, weighted by the window length
    '''
    diff = new_val - running_avg_val
    return running_avg_val + (diff / avg_window)

def _convert_string_time(strtime):
    '''
    Convert string time to datetime
    '''
    return dt.datetime.strptime(strtime, "%Y-%m-%dT%H:%M:%SZ")

def _exit_app(status=0):
    '''
    Exit cleanly, closing window, writing logfile, and freeing ANT+ resources.
    '''
    try:
        window.close()
    except NameError:
        pass
    try:
        sensors.close()
    except NameError:
        pass
    sys.exit(status)

def _update_sensor_status_indicator(element, sensor_status):
    '''
    Change color of the selected element based on the status of an ANT+ sensor.
    '''
    if sensor_status == AntSensors.SensorStatus.State.NOTCONNECTED:
        element.update(background_color="red")
    elif sensor_status == AntSensors.SensorStatus.State.CONNECTED:
        element.update(background_color=sg.theme_background_color())
    elif sensor_status == AntSensors.SensorStatus.State.STALE:
        element.update(background_color="yellow")

def _get_workout_from_config(config):
    '''
    Initialize workout plot with workout profile
    '''
    wkout = Workout(config.get("Workout"))
    min_p, max_p = wkout.get_min_max_power()
    return wkout, min_p, max_p

def _start_log(ldir):
    '''
    Initialize and return a TCX logfile.
    '''
    if not os.path.exists(ldir):
        os.makedirs(ldir)
    lfile = Tcx()
    lfile.start_log("{}/{}.tcx".format(
        ldir, dt.datetime.now().strftime("%Y%m%d_%H%M%S")))
    lfile.start_activity(activity_type=Tcx.ActivityType.OTHER)
    return lfile

def _upload_activity(config, logfile, workout):
    layout = [[sg.T("Upload activity to Strava?")],
              [sg.B("Strava Connect", key="-STRAVA-BTTN-"),
               sg.T("Auth status", (30,1), key="-STRAVA-AUTH-STATUS-")],
              [sg.Frame("Summary", layout=[
                  [sg.T("Distance", (24,1), key="-DIST-"),
                   sg.T("Time", (24,1), key="-TIME-")],
                  [sg.T("Activity Name:", (15,1)),
                   sg.I(workout.name, text_color="gray",
                        size=(40,1), key="-NAME-", metadata="default")],
                  [sg.T("Description:", (15,1)),
                   sg.I(workout.description, text_color="gray",
                        size=(40,1), key="-DESC-", metadata="default")]])],
              [sg.B("Upload", key="-UPLOAD-", bind_return_key=True, disabled=True),
               sg.B("Discard", key="-DISCARD-")]]
    window = sg.Window("Upload Activity", layout=layout)

    window.finalize()
    # Update Strava status:
    strava_api = StravaApi(config)
    set_strava_status(window, strava_api)
    if strava_api.is_authed():
        window["-UPLOAD-"].update(disabled=False)
    # Update workout info:
    time_s, distance_m = logfile.get_lap_stats()
    window["-DIST-"].update("Distance: {:4.1f}miles".format(float(distance_m)/1609.34))
    window["-TIME-"].update("Time: {:4.0f} minutes".format(float(time_s)/60))
    window.refresh()

    # Bind focus events on input boxes, to delete default value automatically for user
    window["-NAME-"].bind("<FocusIn>", "")
    window["-DESC-"].bind("<FocusIn>", "")

    while True:
        e, _ = window.read()
        if e in [sg.WIN_CLOSED, "-DISCARD-"]:
            if sg.PopupYesNo("Really discard this activity?") == "Yes":
                break
        elif e == "-STRAVA-BTTN-":
            handle_strava_auth_button(strava_api, config)
            config.write_settings(config.get("settingsfile"))
            set_strava_status(window, strava_api)
            if strava_api.is_authed():
                window["-UPLOAD-"].update(disabled=False)
        elif e in ["-NAME-", "-DESC-"]:
            if window[e].metadata == "default":
                window[e].update(value="",text_color="White")
                window[e].metadata = ""
        elif e == "-UPLOAD-":
            try:
                StravaData(strava_api).upload_activity(activity_file=logfile.file_name,
                                        name=window["-NAME-"].get(),
                                        description=window["-DESC-"].get(),
                                        trainer=True, commute=False,
                                        activity_type="VirtualRide", gear_id="PM Trainer")
                sg.Popup("Uploaded successfully!")
            except StravaApi.AuthError as e:
                sg.Popup("Upload failed: \r\n{}".format(e.message))
            break
    window.close()

def _scale_plot_margins(y_lims):
    '''
    Scale the vertical plot and apply standard margins to it.
    '''
    return ((y_lims[0]*(1 - PLOT_MARGINS_PERCENT/100)),
                y_lims[1]*(1 + PLOT_MARGINS_PERCENT/100))

def _plot_workout(graph, wkout, y_lims):
    '''
    Plot a workout on the graph.
    '''
    y_lims = _scale_plot_margins(y_lims)
    graph.erase()
    profile_plotter.plot_blocks(graph, wkout.get_all_blocks(), y_lims)

def _plot_trace(graph, val, y_lims, size=3, color='red'):
    '''
    Plot a trace on the graph.
    '''
    y_lims = _scale_plot_margins(y_lims)
    profile_plotter.plot_trace(graph, val, y_lims, size=size, color=color)

# Load settings
cfg = settings.Settings()
if os.path.isfile(DEFAULT_SETTINGS["SettingsFile"]):
    print("Loading config from file")
    cfg.load_settings(filename=DEFAULT_SETTINGS["SettingsFile"])
else:
    print("Loading default config")
    cfg.load_settings(defaults=DEFAULT_SETTINGS)
    cfg.write_settings(filename=DEFAULT_SETTINGS["SettingsFile"])

sg.theme("DarkBlack")

# Attach to ANT+ dongle and start searching for sensors
if not REPLAY_MODE:
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
                _exit_app(-1)
            else:
                print("Caught sensor error {}".format(e.err_type))
                _exit_app(-1)
        time.sleep(1)
        sensors.close()
        del sensors

# Set up main window
FONT = "Helvetica 22"
LABEL_FONT = "Helvetica 14"
layout = [[sg.T("HH:MM:SS", (8,1), pad=((20,20),(5,0)),
                key="-TIME-",justification="L", font="Helvetica 30"),
           sg.Frame("Sensors", pad=(5,0), layout=[
           [sg.T("HR:", key="-HR-LABEL-", pad=((10,0),(0,0)), font=LABEL_FONT),
                sg.T("000",(3,1),
                     key="-HEARTRATE-",justification="L", font=FONT),
           sg.T("Watts:", key="-PWR-LABEL-", pad=((10,0),(0,0)), font=LABEL_FONT),
                sg.T("0000",(4,1),
                     key="-POWER-",justification="L", font=FONT)]]),
           sg.Frame("Performance", pad=(5,0), layout=[
           [sg.T("Speed:", pad=((10,0),(0,0)), font=LABEL_FONT),
                sg.T("0.0",(4,1),
                     key="-SPEED-",justification="L", font=FONT),
           sg.T("Distance:", pad=((10,0),(0,0)), font=LABEL_FONT),
                sg.T("000",(4,1),
                     key="-DISTANCE-",justification="L", font=FONT)]]),
           sg.Frame("Workout", pad=(5,0), layout=[
            [sg.T("Target Power:", pad=((10,0),(0,0)), font=LABEL_FONT),
                sg.T("0000",(4,1),
                     key="-TARGET-",justification="L", font=FONT),
           sg.T("Remaining:", pad=((10,0),(0,0)), font=LABEL_FONT),
                sg.T("MM:SS",(5,1),
                     key="-REMAINING-",justification="L", font=FONT)]]),
           sg.Button('', pad=((5,5),(10,0)), image_data=icons.settings,
                button_color=(sg.theme_background_color(),sg.theme_background_color()),
                border_width=0, key="-SETTINGS-")],
           [sg.Graph(canvas_size=(30,60), graph_bottom_left=(0,0), graph_top_right=(20,60),
                     background_color="black", key="-BUG-"),
           sg.Graph(canvas_size=(1000,60), graph_bottom_left=(0,0),
                     graph_top_right=(1000,60), background_color="black",
                     key="-PROFILE-")]]
window = sg.Window("PM Trainer", layout, keep_on_top=True, use_ttk_buttons=True,
    alpha_channel=0.9, finalize=True, element_padding=(0,0))
power_bug = BugIndicator(window["-BUG-"])
power_bug.add_bug("TARGET_POWER", level_percent=0.5, color="blue")
power_bug.add_bug("CURRENT_POWER", level_percent=0.5,
                  height_px=20, width_px=25, left=False, color="red")

workout, min_power, max_power = _get_workout_from_config(cfg)
_plot_workout(window["-PROFILE-"], workout, (min_power, max_power))

log_dir = cfg.get("LogDirectory")
logfile = _start_log(log_dir)

# Main loop
t = Timer(replay=REPLAY_MODE, tick_ms=args.speed * UPDATE_RATE_MS)
if REPLAY_MODE:
    replay_data = Tcx()
    replay_data.open_log(args.replay)
    p = replay_data.get_next_point()
    t.start(current_time=_convert_string_time(p.time))
else:
    t.start()

total_weight_kg = (float(cfg.get("RiderWeightKg"))+float(cfg.get("BikeWeightKg")))
sim = BikeSim(weight_kg=total_weight_kg)

iters = 0
avg_hr = None
avg_power = None
ftp_watts = float(cfg.get("FTPWatts"))
last_log_time = t.get_time()

while True:
    try:
        # Handle window events
        event, _ = window.read(timeout=UPDATE_RATE_MS)
        if event == sg.WIN_CLOSED:
            if logfile:
                logfile.flush()
                time_s, _ = logfile.get_lap_stats()
                if time_s and float(time_s) > 30:
                    _upload_activity(cfg, logfile, workout)
            _exit_app()
        if event == "-SETTINGS-":
            settings_dialog_popup(cfg)
            cfg.write_settings(cfg.get("SettingsFile"))
            # Update workout plot and start new workout if changed:
            w_new, min_new, max_new = _get_workout_from_config(cfg)
            if w_new.name != workout.name:
                workout, min_power, max_power = w_new, min_new, max_new
                _plot_workout(window["-PROFILE-"], workout, (min_power, max_power))
                #TODO: popup asking if we want to restart the workout or continue from the current time
            # Update log directory and start new log if it's changed:
            dir_new = cfg.get("LogDirectory")
            if dir_new != log_dir:
                log_dir = dir_new
                logfile = _start_log(log_dir)
            # Update other values:
            ftp_watts = float(cfg.get("FTPWatts"))
            new_total_weight_kg = float(cfg.get("RiderWeightKg"))+float(cfg.get("BikeWeightKg"))
            if total_weight_kg != new_total_weight_kg:
                total_weight_kg = new_total_weight_kg
                sim.weight_kg = new_total_weight_kg

        # Update current time:
        t.update()

        # Update sensor variables:
        if not REPLAY_MODE:
            heartrate = sensors.heartrate_bpm
            power = sensors.power_watts
            cadence = sensors.cadence_rpm
            hr_status = sensors.heart_rate_status
            pwr_status = sensors.power_meter_status
        else:
            while (p is not None) and (
                (_convert_string_time(p.time) - t.start_time) <= t.get_time()):
                heartrate = p.heartrate_bpm
                if heartrate:
                    hr_status = AntSensors.SensorStatus.State.CONNECTED
                else:
                    hr_status = AntSensors.SensorStatus.State.NOTCONNECTED
                power = p.power_watts
                if power:
                    pwr_status = AntSensors.SensorStatus.State.CONNECTED
                else:
                    pwr_status = AntSensors.SensorStatus.State.NOTCONNECTED
                cadence = p.cadence_rpm
                p = replay_data.get_next_point()

        # Update speed and distance simulator:
        if pwr_status == AntSensors.SensorStatus.State.CONNECTED:
            sim.update(power, t.get_time().seconds)

        # Update text display:
        window["-HEARTRATE-"].update(heartrate)
        window["-POWER-"].update(power)
        window["-TIME-"].update("{:02d}:{:02d}:{:02d}".format(
            int(t.get_time().seconds/3600) % 24,
            int(t.get_time().seconds/60) % 60,
            t.get_time().seconds % 60))
        window["-SPEED-"].update("{:3.1f}".format(sim.speed_miph))
        window["-DISTANCE-"].update("{:3.1f}".format(sim.total_distance_mi))

        # Handle sensor status:
        _update_sensor_status_indicator(window["-HR-LABEL-"], hr_status)
        _update_sensor_status_indicator(window["-PWR-LABEL-"], pwr_status)

        # Update workout params:
        power_target = workout.power_target(t.get_time().seconds)
        if power_target is not None:
            power_target = power_target * ftp_watts
        window['-TARGET-'].update(
            " " if power_target is None else "{:4.0f}".format(power_target))
        remain_s = workout.block_time_remaining(t.get_time().seconds)
        window['-REMAINING-'].update("{:2.0f}:{:02.0f}".format(
            int(remain_s / 60) % 60, remain_s % 60))

        # Update plot:
        norm_time = t.get_time().seconds / workout.duration_s
        if heartrate:
            if avg_hr is None:
                avg_hr = heartrate
            avg_hr = _avg_val(avg_hr, heartrate, avg_window=3)
            _plot_trace(window["-PROFILE-"],
                (norm_time, (avg_hr-HEART_RATE_LIMITS[0])/HEART_RATE_LIMITS[1]),
                (0,0.5), color="cyan")
        if power:
            if avg_power is None:
                avg_power = power
            avg_power = _avg_val(avg_power, power, avg_window=10)
            _plot_trace(window["-PROFILE-"],
                (norm_time, avg_power / ftp_watts),
                (min_power, max_power), color="red")

        # Update power bug
        if power:
            power_bug.update("CURRENT_POWER",
                             (power - float(power_target))/POWER_BUG_LIMITS_WATTS + 0.5)

        # Update log file
        iters += 1
        if t.get_time().seconds - last_log_time.seconds >= 1.0:  # Log at 1Hz.
            if pwr_status == AntSensors.SensorStatus.State.CONNECTED:
                logfile.add_point(Point(heartrate_bpm=heartrate,
                                        cadence_rpm=cadence,
                                        power_watts=power,
                                        distance_m=sim.total_distance_m,
                                        speed_mps=sim.speed_mps))
                logfile.set_lap_stats(total_time_s=t.get_time().seconds, distance_m=sim.total_distance_m)
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
