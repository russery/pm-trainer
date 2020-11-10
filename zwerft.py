"""

"""

import time

from ant.core import driver
from ant.core.node import Node, Network
from ant.core.constants import NETWORK_KEY_ANT_PLUS, NETWORK_NUMBER_PUBLIC
from ant.plus.plus import DeviceProfile
from ant.plus.heartrate import HeartRate
from ant.plus.power import BicyclePower

device = driver.USB2Driver()
antnode = Node(device)
antnode.start()
network = Network(key=NETWORK_KEY_ANT_PLUS, name='N:ANT+')
antnode.setNetworkKey(NETWORK_NUMBER_PUBLIC, network)

def on_device_found(_, ch_id):
    print("device number: %d, device type %s, transmission type: %d" %
        (ch_id.deviceNumber, ch_id.deviceType, ch_id.transmissionType))
    if ch_id.deviceType == HeartRate.deviceType:
        print("Found heart rate monitor")
    elif ch_id.deviceType == BicyclePower.deviceType:
        print("Found power meter")
    else:
        print("Found unknown device type {:d}".format(ch_id.deviceType))

def on_heartrate_data(computed_heartrate, event_time_ms, rr_interval_ms):
    if rr_interval_ms is not None:
        print("Heart rate: %d, event time(ms): %d, rr interval (ms): %d" %
              (computed_heartrate, event_time_ms, rr_interval_ms))
    else:
        print("Heart rate: %d" % computed_heartrate)

def on_power_data(event_count, pedal_diff, pedal_power_ratio, cadence_rpm, accumulated_pwr_W, instantaneous_pwr_W):
    print("got some sweet sweet power")


device_power_meter = BicyclePower(antnode, network, callbacks = {'onDevicePaired': on_device_found,
                                              'onPowerData': on_power_data})
device_power_meter.open()

device_heart_rate = HeartRate(antnode, network, callbacks = {'onDevicePaired': on_device_found,
                                              'onHeartRateData': on_heartrate_data})
device_heart_rate.open()


while True:
    try:
        time.sleep(0.25)
    except KeyboardInterrupt:
        break

device_heart_rate.close()
device_power_meter.close()
antnode.stop()
