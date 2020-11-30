"""
Logs trainer rides or something.
"""

import sys
import time
from datetime import datetime as dt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, FigureCanvasAgg
from matplotlib.figure import Figure
import matplotlib.backends.tkagg as tkagg
import numpy as np
import PySimpleGUI as sg
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
           [sg.Canvas(size=(200,20), key="-PLOT-")]]
window = sg.Window("Zwerft", layout, grab_anywhere=True, keep_on_top=True,
    use_ttk_buttons=True, alpha_channel=0.8)
window.Finalize()

workout = Workout("workouts/short_stack.yaml")


# Initialize workout plot with workout profile
canvas_elem = window["-PLOT-"]
graph = FigureCanvasTkAgg(fig, master=canvas_elem.TKCanvas)
canvas = canvas_elem.TKCanvas

all_blocks = workout.get_all_blocks()

fig = Figure()
ax = fig.add_subplot(111)

dur = 0
for block in all_blocks:
    width = block[0]
    start = block[1]
    end = block[2]
    zone = get_zone(np.average([start,end]))
    color = ZONE_COLORS[zone]
    if start == end:
        # Start == end, so this is a rectangle
        shape = plt.Rectangle((dur, 0), width, start, fc=color)
    else:
        # This is a ramp (triangle)
        shape = plt.Polygon([[dur,0],[dur,start],[dur+width,end],[dur+width,0]],fc=color)
    ax.gca().add_patch(shape)
    dur += width

graph.draw()
figure_x, figure_y, figure_w, figure_h = fig.bbox.bounds
figure_w, figure_h = int(figure_w), int(figure_h)
photo = Tk.PhotoImage(master=canvas, width=figure_w, height=figure_h)
canvas.create_image(640 / 2, 480 / 2, image=photo)

figure_canvas_agg = FigureCanvasAgg(fig)
figure_canvas_agg.draw()

tkagg.blit(photo, figure_canvas_agg.get_renderer()._renderer, colormode=2) 





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

        # Update log file
        if ((sensors.heart_rate_status == AntSensors.SensorStatus.State.CONNECTED) and
            (sensors.power_meter_status == AntSensors.SensorStatus.State.CONNECTED)):
            logfile.add_point(heartrate_bpm=heartrate, cadence_rpm=cadence, power_watts=power)
            logfile.lap_stats(total_time_s=elapsed_time.seconds)

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
        # TODO

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
