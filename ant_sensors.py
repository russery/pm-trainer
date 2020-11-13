"""
Handles interactions with ANT+ heartrate and power meter sensors.

Connects to the sensors, and provides callbacks to the python-ant library
for each type of device. Outputs heartrate, power, and cadence data.

Depends on python_ant from: https://github.com/bissont/python-ant
Note that there are other forks available, but this one is the only
one that seems to work.

Also requires libopenusb or libusb to be installed:
https://sourceforge.net/projects/openusb/files/libopenusb/libopenusb-1.1.16/

Class: 
    AntSensors()
"""

from ant.core import driver
from ant.core.node import Node, Network
from ant.core.constants import NETWORK_KEY_ANT_PLUS, NETWORK_NUMBER_PUBLIC
from ant.plus.plus import DeviceProfile
from ant.plus.heartrate import HeartRate
from ant.plus.power import BicyclePower

class AntSensors():
    """
    ANT+ Heartrate and Power Meter sensor handler
    """
    def __init__(self, search_timeout_sec=120):
        """
        Attaches to the ANT+ interface dongle, registers callbacks,
        begins search for heartrate and power meter sensors.
        """
        self.device = driver.USB2Driver()
        self.antnode = Node(self.device)
        self.antnode.start()
        self.network = Network(key=NETWORK_KEY_ANT_PLUS, name='N:ANT+')
        self.antnode.setNetworkKey(NETWORK_NUMBER_PUBLIC, self.network)

        # Start search for sensors and register callbacks:
        self.device_power_meter = BicyclePower(self.antnode, self.network,
            callbacks = {'onDevicePaired': self._on_device_found,
                         'onPowerData': self._on_power_data,
                         'onChannelClosed': self._on_channel_closed,
                         'onSearchTimeout': self._on_search_timeout})
        self.device_heart_rate = HeartRate(self.antnode, self.network,
            callbacks = {'onDevicePaired': self._on_device_found,
                         'onHeartRateData': self._on_heartrate_data,
                         'onChannelClosed': self._on_channel_closed,
                         'onSearchTimeout': self._on_search_timeout})
        self.device_heart_rate.open(searchTimeout=search_timeout_sec)
        self.device_power_meter.open(searchTimeout=search_timeout_sec)

        # Heartrate fields
        self._heartrate_bpm = None
        self._rr_interval_ms = None
        # Power meter fields
        self._instantaneous_power_W = None
        self._cadence_rpm = None
        self._accumulated_power_W = None
        self._power_event_count = None
    
    def close(self):
        """
        Safely closes down the dongle interface and releases resources
        prior to exit.
        """
        self.device_heart_rate.close()
        self.device_power_meter.close()
        self.antnode.stop()

    def _on_device_found(self, device, ch_id):
        #TODO: make the device number available
        print("Found a {:s} device".format(device.name))
        print("device number: {:d} device type {:d}, transmission type: {:d}\r\n".format(
            ch_id.deviceNumber, ch_id.deviceType, ch_id.transmissionType))

    def _on_channel_closed(self, device):
        #TODO: Handle this - make sure that data reflects channel no longer being open
        print("Channel closed for {:s}".format(device.name))

    def _on_search_timeout(self, device):
        #TODO: Handle this in some way - might want to retry search or at least signal somehow that search timed out
        print("Search timed out for {:s}".format(device.name))
        
    def _on_heartrate_data(self, computed_heartrate, event_time_ms, rr_interval_ms):
        self._heartrate_bpm = computed_heartrate
        self._rr_interval_ms = rr_interval_ms

    def _on_power_data(self, event_count, pedal_diff, pedal_power_ratio, cadence_rpm, accumulated_power_W, instantaneous_power_W):
        self._instantaneous_power_W = instantaneous_power_W
        self._cadence_rpm = cadence_rpm
        self._accumulated_power_W = accumulated_power_W
        self._power_event_count = event_count

    @property
    def heartrate_bpm(self):
        """
        Returns heartrate in beats per minute (BPM) or None if heartrate data are not
        available or fresh.
        """
        #TODO: check for stale data (if no update in xx sec, return None)
        return self._heartrate_bpm

    @property
    def power_W(self):
        """
        Returns power in Watts if available, or None if not available or fresh.
        """
        #TODO: return calculated power from accumulated power if there are event_count gaps
        #TODO: check for stale data (if no update in xx sec, return None)
        return self._instantaneous_power_W

    @property
    def cadence_rpm(self):
        """
        Returns cadence in RPM if available or None if not available or fresh.
        """
        #TODO: check for stale data (if no update in xx sec, return None)
        return self._cadence_rpm


if __name__ == "__main__":
    import time

    print("Attaching to ANT+ sensors...")

    sensors = AntSensors()
    while True:
        try:
            time.sleep(0.25)
            print("heartrate: {} power: {} cadence: {}".format(
                sensors.heartrate_bpm, sensors.power_W, sensors.cadence_rpm))
        except KeyboardInterrupt:
            break
    sensors.close()