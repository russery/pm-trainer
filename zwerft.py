'''
Logs trainer rides or something.
'''
import argparse
import os
import sys
import time
import datetime as dt
import PySimpleGUI as sg
import profile_plotter
import settings
from ant_sensors import AntSensors
import assets.icons
from workout_profile import Workout
from tcx_file import Tcx, Point
from bug_indicator import BugIndicator
from bike_sim import BikeSim

DEFAULT_SETTINGS = {
   # User / session settings:
   "FTPWatts": 230,
   "RiderWeightKg": 70,
   "BikeWeightKg": 10,
   "Workout": "workouts/short_stack.yaml",

   # Window / system settings
   "LogDirectory": "./logs",
   "SettingsFile": "zwerft_settings.ini",
   "UpdateRateHz": 10
}

PLOT_MARGINS_PERCENT = 10 # Percent of plot to show beyond limits
HEART_RATE_LIMITS = (100, 200)
POWER_BUG_LIMITS_WATTS = 100 # Vertical size of power bug in watts

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
    A timer, that returns time as a datetime timedelta. The timer only updates
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
    '''
    Exit cleanly, closing window, writing logfile, and freeing ANT+ resources.
    '''
    if logfile:
        logfile.flush()
    if window:
        window.close()
    if sensors:
        sensors.close()
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

def _settings_dialog(config):
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
FONT = "Any 22"
LABEL_FONT = "Any 14"
layout = [[sg.T("Time:", pad=((10,0),(0,0)), font=LABEL_FONT),
                sg.T("HH:MM:SS", (8,1), relief="raised",
                     key="-TIME-",justification="L", font=FONT),
           sg.T("HR:", key="-HR-LABEL-", pad=((10,0),(0,0)), font=LABEL_FONT),
                sg.T("000",(3,1),relief="raised",
                     key="-HEARTRATE-",justification="L", font=FONT),
           sg.T("Watts:", key="-PWR-LABEL-", pad=((10,0),(0,0)), font=LABEL_FONT),
                sg.T("0000",(4,1),relief="raised",
                     key="-POWER-",justification="L", font=FONT),
           sg.T("Speed:", pad=((10,0),(0,0)), font=LABEL_FONT),
                sg.T("0.0",(4,1),relief="raised",
                     key="-SPEED-",justification="L", font=FONT),
           sg.T("Distance:", pad=((10,0),(0,0)), font=LABEL_FONT),
                sg.T("000",(4,1),relief="raised",
                     key="-DISTANCE-",justification="L", font=FONT),
           sg.T("Target Power:", pad=((10,0),(0,0)), font=LABEL_FONT),
                sg.T("0000",(4,1),relief="raised",
                     key="-TARGET-",justification="L", font=FONT),
           sg.T("Remaining:", pad=((10,0),(0,0)), font=LABEL_FONT),
                sg.T("MM:SS",(5,1),relief="raised",
                     key="-REMAINING-",justification="L", font=FONT),
           sg.Button('', image_data=assets.icons.settings,
                button_color=(sg.theme_background_color(),sg.theme_background_color()),
                border_width=0, key="-SETTINGS-")],
           [sg.Graph(canvas_size=(30,60), graph_bottom_left=(0,0), graph_top_right=(20,60),
                     background_color="black", key="-BUG-"),
           sg.Graph(canvas_size=(1000,60), graph_bottom_left=(0,0),
                     graph_top_right=(1000,60), background_color="black",
                     key="-PROFILE-")]]
window = sg.Window("Zwerft", layout, keep_on_top=True, use_ttk_buttons=True,
    alpha_channel=0.9, finalize=True, element_padding=(0,0))
power_bug = BugIndicator(window["-BUG-"])
power_bug.add_bug("TARGET_POWER", level_percent=0.5, color="blue")
power_bug.add_bug("CURRENT_POWER", level_percent=0.5,
                  height_px=30, width_px=30, left=False, color="red")

workout, min_power, max_power = _get_workout_from_config(cfg)
_plot_workout(window["-PROFILE-"], workout, (min_power, max_power))

log_dir = cfg.get("LogDirectory")
logfile = _start_log(log_dir)

update_ms = 1000 / float(cfg.get("UpdateRateHz"))
if REPLAY_MODE:
    update_ms = 50
ftp_watts = float(cfg.get("FTPWatts"))

# Main loop
t = Timer(replay=REPLAY_MODE, tick_ms=args.speed * update_ms)
if REPLAY_MODE:
    replay_data = Tcx()
    replay_data.open_log(args.replay)
    replay_data.get_activity()
    p = replay_data.get_next_point()
    t.start(current_time=p.time)
else:
    t.start()

sim = BikeSim(weight_kg=(float(cfg.get("RiderWeightKg"))+float(cfg.get("BikeWeightKg"))))

iters = 0

while True:
    try:
        # Handle window events
        event, _ = window.read(timeout=update_ms)
        if event == sg.WIN_CLOSED:
            _exit_zwerft()
        if event == "-SETTINGS-":
            #window.Disappear()
            _settings_dialog(cfg)
            #window.Reappear()
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
            if REPLAY_MODE:
                update_ms = 50
            ftp_watts = float(cfg.get("FTPWatts"))

        # Update current time:
        t.update()

        # Update sensor variables:
        heartrate = sensors.heartrate_bpm
        power = sensors.power_watts
        cadence = sensors.cadence_rpm
        hr_status = sensors.heart_rate_status
        pwr_status = sensors.power_meter_status
        if REPLAY_MODE:
            while (p is not None) and ((p.time - t.start_time) <= t.get_time()):
                heartrate = p.heartrate_bpm
                if heartrate:
                   hr_status = AntSensors.SensorStatus.State.CONNECTED
                power = p.power_watts
                if power:
                   pwr_status = AntSensors.SensorStatus.State.CONNECTED
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
        if power_target:
            power_target = "{:4.0f}".format(power_target*ftp_watts)
        else:
            power_target = ""
        window['-TARGET-'].update(power_target)
        remain_s = workout.block_time_remaining(t.get_time().seconds)
        window['-REMAINING-'].update("{:2.0f}:{:02.0f}".format(
            int(remain_s / 60) % 60, remain_s % 60))

        # Update plot:
        norm_time = t.get_time().seconds / workout.duration_s
        if power:
            _plot_trace(window["-PROFILE-"],
                (norm_time, power / ftp_watts),
                (min_power, max_power), color="red")
        if heartrate:
            _plot_trace(window["-PROFILE-"],
                (norm_time, (heartrate-HEART_RATE_LIMITS[0])/HEART_RATE_LIMITS[1]),
                (0,0.5), color="cyan")

        # Update power bug
        if power:
            power_bug.update("CURRENT_POWER",
                             (power - float(power_target))/POWER_BUG_LIMITS_WATTS + 0.5)

        # Update log file
        iters += 1
        if iters % int(cfg.get("UpdateRateHz")) == 0: #HACKY HACK HACK
            #TODO: Limit logging to 1Hz more intelligently
            if pwr_status == AntSensors.SensorStatus.State.CONNECTED:
                logfile.add_point(Point(heartrate_bpm=heartrate,
                                        cadence_rpm=cadence,
                                        power_watts=power,
                                        distance_m=sim.total_distance_m,
                                        speed_mps=sim.speed_mps))
                logfile.lap_stats(total_time_s=t.get_time().seconds)
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
