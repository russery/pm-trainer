"""
Logs trainer rides or something.
"""

import sys
import time
from datetime import datetime as dt
import PySimpleGUI as sg
import profile_plotter
from ant_sensors import AntSensors
from workout_profile import Workout
from tcx_file import Tcx

def exit_zwerft(status=0):
    """
    Exit cleanly, closing window, writing logfile, and freeing ANT+ resources.
    """
    try:
        logfile.flush()
        window.close()
        sensors.close()
    finally:
        sys.exit(status)

def update_sensor_status_indicator(element, sensor_status):
    """
    Change color of the selected element based on the status of an ANT+ sensor.
    """
    if sensor_status == AntSensors.SensorStatus.State.NOTCONNECTED:
        element.update(background_color="red")
    elif sensor_status == AntSensors.SensorStatus.State.CONNECTED:
        element.update(background_color="green")
    elif sensor_status == AntSensors.SensorStatus.State.STALE:
        element.update(background_color="yellow")

FTP_WATTS = 220

sg.SetOptions(element_padding=(0,0))
sg.theme("DarkBlack")
# Connect to sensors
while True:
    try:
        sensors = AntSensors()
        sensors.connect()
        break
    except AntSensors.SensorError as e:
        if e.err_type == AntSensors.SensorError.ErrorType.USB:
            sg.Popup("USB Dongle Error", "Could not connect to ANT+ dongle \
             - check USB connection and try again",
                keep_on_top=True, any_key_closes=True)
            # TODO: Keep the application open and try again - this should be recoverable
            exit_zwerft(-1)
        else:
            print("Caught sensor error {}".format(e.err_type))
    time.sleep(1)
    sensors.close()
    del sensors

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
                                 key="-REMAINING-",justification="L")],
           [sg.Graph(canvas_size=(800, 100), graph_bottom_left=(0, 0),
                     graph_top_right=(800, 100), background_color='black',
                     key='-PROFILE-')]]
window = sg.Window("Zwerft", layout, grab_anywhere=True, keep_on_top=True,
    use_ttk_buttons=True, alpha_channel=0.8)
window.Finalize()

workout = Workout("workouts/short_stack.yaml")


# Initialize workout plot with workout profile
blocks = workout.get_all_blocks()
max_power = profile_plotter.get_max_power(blocks) * 1.2
profile_plotter.plot_blocks(window["-PROFILE-"], blocks, max_power)


logfile = Tcx()
logfile.start_activity(activity_type=Tcx.ActivityType.OTHER)
start_time = dt.now()

# Main loop
while True:
    try:
        # Handle window events
        event, values = window.read(timeout=250)

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
        update_sensor_status_indicator(window["-HEARTRATE-"], sensors.heart_rate_status)
        update_sensor_status_indicator(window["-POWER-"], sensors.power_meter_status)
        update_sensor_status_indicator(window["-CADENCE-"], sensors.power_meter_status)

        # Update workout params:
        window['-TARGET-'].update("{:4.0f}".format(
            workout.power_target(elapsed_time.seconds)*FTP_WATTS))
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

        if event == sg.WIN_CLOSED:
            exit_zwerft()
    except AntSensors.SensorError as e:
        if e.err_type == AntSensors.SensorError.ErrorType.USB:
            print("Could not connect to ANT+ dongle - check USB connection")
        elif e.err_type == AntSensors.SensorError.ErrorType.TIMEOUT:
            print("Starting search for sensors again...")
            sensors.connect()
            continue
        else:
            print("Caught sensor error {}".format(e.err_type))
    except Exception as e:
        print(e)
        exit_zwerft(-1)
