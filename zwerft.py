#!/usr/bin/python
# -*- coding: ascii -*-
"""

"""
import sys
import time
import PySimpleGUI as sg
from ant_sensors import AntSensors

def exit(status=0):
    # Exit cleanly
    try:
        window.close()
        sensors.close()
    finally:
        sys.exit(status)

sg.SetOptions(element_padding=(0,0))
sg.theme("DarkBlack")

def update_sensor_status_indicator(element, sensor_status):
    if sensor_status == AntSensors.SensorStatus.State.NOTCONNECTED:
        element.update(background_color="red")
    elif sensor_status == AntSensors.SensorStatus.State.CONNECTED:
        element.update(background_color="green")
    elif sensor_status == AntSensors.SensorStatus.State.STALE:
        element.update(background_color="yellow")

# Connect to sensors
connected = False
sensors = None
while not connected:
    try:
        sensors = AntSensors()
        sensors.connect()
        connected = True
        break
    except AntSensors.SensorError as e:
        if e.err_type == AntSensors.SensorError.ErrorType.USB:
            sg.Popup("USB Dongle Error", "Could not connect to ANT+ dongle - check USB connection and try again",
                keep_on_top=True, any_key_closes=True)
            # TODO: Keep the application open and try again - this should be recoverable
            exit(-1)
        else:
            print("Caught sensor error {}".format(e.err_type))
    except Exception as e:
        print(e)
        exit(-1)
    time.sleep(1)
    sensors.close()
    del sensors

layout = [[sg.T("  ",size=(2,1),key="-HRSTATUS-",background_color="red"),
           sg.T("HR:"), sg.T("000",(3,1),relief="raised",key="-HEARTRATE-",justification="L"),
           sg.T("  ",size=(2,1),key="-PMSTATUS-",background_color="red",pad=((10,0),(0,0))),
           sg.T("Watts:"),sg.T("0000",(4,1),relief="raised",key="-POWER-",justification="L"),
           sg.T("Cadence:"),sg.T("000",(3,1),relief="raised",key="-CADENCE-",justification="L")],
            [sg.ProgressBar(100,size=(80, 10),orientation="h",bar_color=("blue", "white"), k="-PROGRESS-",pad=((10,10),(10,0)))]]
window = sg.Window("Zwerft", layout, grab_anywhere=True, keep_on_top=True, use_ttk_buttons=True,
    alpha_channel=0.8)


# Main loop
progress=0
while True:
    try:
        # Handle window events
        event, values = window.read(timeout=250)
        window["-HEARTRATE-"].update(sensors.heartrate_bpm)
        window["-POWER-"].update(sensors.power_W)
        window["-CADENCE-"].update(sensors.cadence_rpm)

        window["-PROGRESS-"].update_bar(progress)
        progress += 1

        # Handle sensor status:
        update_sensor_status_indicator(window["-HRSTATUS-"], sensors.heart_rate_status)
        update_sensor_status_indicator(window["-PMSTATUS-"], sensors.power_meter_status)

        if event == sg.WIN_CLOSED:
            exit()
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
        exit(-1)
