#!/usr/bin/python
# -*- coding: ascii -*-
"""

"""
import time
import PySimpleGUI as sg
from ant_sensors import AntSensors


sg.SetOptions(element_padding=(0,0))
sg.theme("DarkBlack")

layout = [[sg.T("HR:"), sg.T("000",(3,1),relief="raised",key="-HEARTRATE-",justification="L"),
           sg.T("Watts:"),sg.T("0000",(4,1),relief="raised",key="-POWER-",justification="L"),
           sg.T("Cadence:"),sg.T("000",(3,1),relief="raised",key="-CADENCE-",justification="L")],
            [sg.ProgressBar(1000,size=(80, 10),orientation='h',bar_color=('blue', 'white'), k="-PROGRESS-",pad=((10,10),(10,0)))]]
window = sg.Window("Zwerft", layout, grab_anywhere=True, keep_on_top=True, use_ttk_buttons=True,
    alpha_channel=0.8)

# Begin searching for ANT+ sensors
sensors = AntSensors()

progress = 0
# Create an event loop
while True:
    try:
        time.sleep(0.25)
        # Handle window events
        event, values = window.read(timeout=10)
        window["-HEARTRATE-"].update(sensors.heartrate_bpm)
        window["-POWER-"].update(sensors.power_W)
        window["-CADENCE-"].update(sensors.cadence_rpm)

        window["-PROGRESS-"].update_bar(progress)
        progress += 1
        if event == sg.WIN_CLOSED:
            break
    except Exception as e:
        print(e)
        # Catch any exceptions and make sure we shut down cleanly
        break
    
sensors.close()
window.close()