"""
Handles interactions with ANT+ heartrate and power meter sensors.

Connects to the sensors, and provides callbacks to the python-ant library
for each type of device. Outputs heartrate, power, and cadence data.

Depends on python_ant from: https://github.com/bissont/python-ant
Note that there are other forks available, but this one is the only
one that seems to work.

Also requires libopenusb or libusb to be installed:
https://sourceforge.net/projects/openusb/files/libopenusb/libopenusb-1.1.16/

----
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
"""

import sys
from datetime import datetime as dt
from enum import Enum

from ant.core import driver, exceptions
from ant.core.node import Node, Network
from ant.core.constants import NETWORK_KEY_ANT_PLUS, NETWORK_NUMBER_PUBLIC
from ant.plus.plus import ChannelState
from ant.plus.heartrate import HeartRate
from ant.plus.power import BicyclePower

class AntSensors():
    """
    ANT+ Heartrate and Power Meter sensor handler
    """
    class SensorStatus():
        """
        Tracks the status of a sensor device, whether it's connected
        and if its data is fresh.
        """
        class State(Enum):
            """
            State of an ANT+ sensor
            """
            NOTCONNECTED = 1
            CONNECTED = 2
            STALE = 3

        def __init__(self, fresh_time_s=15):
            self._connected = False
            self._last_seen_time = None
            self._fresh_time_s = fresh_time_s

        def make_fresh(self):
            """ Marks the sensor as connected and makes last seen time now"""
            self._connected = True
            self._last_seen_time = dt.now()

        def make_disconnected(self):
            """ Marks the sensor as disconnceted"""
            self._connected = False

        @property
        def state(self):
            """ Returns the state of the sensor
            Returns:
                SensorStatus.State representing current state
            """
            if not self._connected:
                _s = self.State.NOTCONNECTED
            elif (self._last_seen_time and
                  (dt.now() - self._last_seen_time).total_seconds() > self._fresh_time_s):
                _s = self.State.STALE
            else:
                _s = self.State.CONNECTED
            return _s

    class SensorError(Exception):
        """
        Exceptions for ANT+ sensors.
        """
        class ErrorType(Enum):
            """
            Type of ANT+ sensor error
            """
            UNKNOWN = 1
            USB = 2
            NODE = 3
            TIMEOUT = 4
        def __init__(self, expression=None, message="", err_type=ErrorType.UNKNOWN):
            super().__init__(message)
            self.expression = expression
            self.message = message
            self.err_type = err_type

    def __init__(self, search_timeout_sec=120):
        """
        Create Ant+ node, network, and initialize all attributes
        """
        self.search_timeout_sec = search_timeout_sec
        self.device = driver.USB2Driver()
        self.antnode = Node(self.device)
        self.network = Network(key=NETWORK_KEY_ANT_PLUS, name='N:ANT+')

        # Start search for sensors and register callbacks:
        self.device_power_meter = BicyclePower(self.antnode, self.network,
            callbacks = {'onDevicePaired': self._on_device_found,
                         'onPowerData': self._on_power_data,
                         'onChannelClosed': self._on_channel_closed,
                         'onSearchTimeout': self._on_search_timeout})
        self._power_meter_status = AntSensors.SensorStatus(fresh_time_s=2)
        self.device_heart_rate = HeartRate(self.antnode, self.network,
            callbacks = {'onDevicePaired': self._on_device_found,
                         'onHeartRateData': self._on_heartrate_data,
                         'onChannelClosed': self._on_channel_closed,
                         'onSearchTimeout': self._on_search_timeout})
        self._heart_rate_status = AntSensors.SensorStatus(fresh_time_s=2)
        self._reconnect = True
        # Heartrate fields
        self._heartrate_bpm = None
        self._rr_interval_ms = None
        self._hr_event_time_ms = None
        # Power meter fields
        self._instantaneous_power_watts = None
        self._cadence_rpm = None
        self._accumulated_power_watts = None
        self._power_event_count = None

    def connect(self):
        """
        Attaches to the ANT+ dongle and begins search for heartrate
        and power meter sensors.
        """
        try:
            self.antnode.start()
            self.antnode.setNetworkKey(NETWORK_NUMBER_PUBLIC, self.network)
        except exceptions.DriverError as e:
            raise AntSensors.SensorError(
                message = e.args[0],
                err_type=AntSensors.SensorError.ErrorType.USB)
        except exceptions.NodeError as e:
            raise AntSensors.SensorError(
                message = e.args[0],
                err_type = AntSensors.SensorError.ErrorType.NODE)

        # Reinitialize all data fields
        self._heartrate_bpm = None
        self._rr_interval_ms = None
        self._hr_event_time_ms = None
        self._instantaneous_power_watts = None
        self._cadence_rpm = None
        self._accumulated_power_watts = None
        self._power_event_count = None
        # Open device and start searching
        self.device_heart_rate.open(searchTimeout=self.search_timeout_sec)
        self.device_power_meter.open(searchTimeout=self.search_timeout_sec)

    def close(self):
        """
        Safely closes down the dongle interface and releases resources
        prior to exit.
        """
        self._reconnect = False
        if (self.device_heart_rate.state and
            self.device_heart_rate.state != ChannelState.CLOSED):
            self.device_heart_rate.close()
        if (self.device_power_meter.state and
            self.device_power_meter.state != ChannelState.CLOSED):
            self.device_power_meter.close()
        try:
            self.antnode.stop()
        except (exceptions.NodeError, exceptions.DriverError):
            pass

    def _on_device_found(self, device, ch_id):
        #TODO: make the device number available
        print("Found a {:s} device".format(device.name))
        print("device number: {:d} device type {:d}, transmission type: {:d}\r\n".format(
            ch_id.deviceNumber, ch_id.deviceType, ch_id.transmissionType))

    def _on_channel_closed(self, device):
        if device == self.device_heart_rate:
            self._heart_rate_status.make_disconnected()
        elif device == self.device_power_meter:
            self._power_meter_status.make_disconnected()
        else:
            print("Unknown device channel closed!")
        print("Channel closed for {:s}".format(device.name))
        # TODO - figure out why re-open doesn't work - returns USB Driver error,
        #        perhaps something wasn't properly freed on close?
        #if self._reconnect == True:
        #    print("Attempting re-connect...")
        #    device.open()

    def _on_search_timeout(self, device):
        raise AntSensors.SensorError(
            message = "Timed out searching for device: {}".format(device.name),
            err_type=AntSensors.SensorError.ErrorType.TIMEOUT)

    def _on_heartrate_data(self, computed_heartrate, event_time_ms, rr_interval_ms):
        self._heartrate_bpm = computed_heartrate
        self._rr_interval_ms = rr_interval_ms
        if (not self._hr_event_time_ms) or event_time_ms > self._hr_event_time_ms:
            self._hr_event_time_ms = event_time_ms
            self._heart_rate_status.make_fresh()

    def _on_power_data(self, event_count, _, __, cadence_rpm,
                       accumulated_power_watts, instantaneous_power_watts):
        self._instantaneous_power_watts = instantaneous_power_watts
        self._cadence_rpm = cadence_rpm
        self._accumulated_power_watts = accumulated_power_watts
        if (not self._power_event_count) or event_count != self._power_event_count:
            self._power_event_count = event_count
            self._power_meter_status.make_fresh()

    @property
    def heartrate_bpm(self):
        """
        Returns heartrate in beats per minute (BPM) or None if heartrate data are not
        available or fresh.
        """
        #TODO: check for stale data (if no update in xx sec, return None)
        return self._heartrate_bpm

    @property
    def power_watts(self):
        """
        Returns power in Watts if available, or None if not available or fresh.
        """
        #TODO: return calculated power from accumulated power if there are event_count gaps
        #TODO: check for stale data (if no update in xx sec, return None)
        return self._instantaneous_power_watts

    @property
    def cadence_rpm(self):
        """
        Returns cadence in RPM if available or None if not available or fresh.
        """
        #TODO: check for stale data (if no update in xx sec, return None)
        return self._cadence_rpm

    @property
    def heart_rate_status(self):
        """
        Returns status of heart rate sensor.
        """
        return self._heart_rate_status.state

    @property
    def power_meter_status(self):
        """
        Returns status of power meter sensor.
        """
        return self._power_meter_status.state


if __name__ == "__main__":
    import time

    print("Attaching to ANT+ sensors...")
    sensors = AntSensors()
    try:
        sensors.connect()
    except AntSensors.SensorError as e:
        if e.err_type == AntSensors.SensorError.ErrorType.USB:
            print("Could not connect to ANT+ dongle - check USB connection")
        else:
            print("Caught sensor error {}".format(e.err_type))
        sys.exit("Sensor Error")

    while True:
        try:
            time.sleep(1)
            print("[{}] heartrate: {} power: {} cadence: {}      HRM: {} PM: {}".format(
                dt.now().strftime("%H:%M:%S.%f"),
                sensors.heartrate_bpm, sensors.power_watts, sensors.cadence_rpm,
                sensors.heart_rate_status, sensors.power_meter_status))
        except AntSensors.SensorError as e:
            print("Caught sensor error {}".format(e.err_type))
            if e.err_type == AntSensors.SensorError.ErrorType.TIMEOUT:
                print("Starting search for sensors again...")
                sensors.connect()
                continue
            break
        except KeyboardInterrupt:
            break
    sensors.close()
    sys.exit(0)
