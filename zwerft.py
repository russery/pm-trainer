"""

"""
import time
from ant_sensors import AntSensors

sensors = AntSensors()
while True:
    try:
        time.sleep(0.25)
        print("heartrate: {} power: {} cadence: {}".format(
            sensors.heartrate_bpm, sensors.power_W, sensors.cadence_rpm))
    except KeyboardInterrupt:
        break
sensors.close()

