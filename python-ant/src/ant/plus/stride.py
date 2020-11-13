# -*- coding: utf-8 -*-
"""ANT+ Stride Based Speed and Distance Monitor Device Profile

"""
# pylint: disable=not-context-manager,protected-access
##############################################################################
#
# Copyright (c) 2017, Matt Hughes
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
#
##############################################################################

from __future__ import print_function

import struct

from .plus import DeviceProfile


class Stride(DeviceProfile):
    """ANT+ Stride Based Speed and Distance Monitor"""

    channelPeriod = 8134
    deviceType = 0x7c
    name = 'Stride Based Speed and Distance'

    def __init__(self, node, network, callbacks=None):
        """
        :param node: The ANT node to use
        :param network: The ANT network to connect on
        :param callbacks: Dictionary of string-function pairs specifying the callbacks to
                use for each event. In addition to the events supported by `DeviceProfile`,
                `Stride` also has the following:
                'onStrideCount'
                'onCalories'
        """
        super(Stride, self).__init__(node, network, callbacks)

        self._detected_device = None

        self._stride_count = None
        self._calories = None
        self._hw_revision = None
        self._manufacturer_id = None
        self._model_number = None
        self._sw_revision = None
        self._serial_number = None

    def processData(self, data):
        payload_offset = 0
        device_page = None

        with self.lock:
            data_page_index = 0 + payload_offset
            device_page = data[data_page_index]

            if device_page == 0x01:
                stride_count_index = 6 + payload_offset
                self._stride_count = data[stride_count_index]
                callback = self.callbacks.get('onStrideCount')
                if callback:
                    callback(self._stride_count)

            elif device_page == 0x02:
                print("page 2, template")

            elif device_page == 0x03:
                calories_index = 6 + payload_offset
                self._calories = data[calories_index]
                callback = self.callbacks.get('onCalories')
                if callback:
                    callback(self._calories)

            elif device_page == 0x10:
                print("page 16, Distance & Strides Since Battery Reset")

            elif device_page == 0x16:
                print("page 22, capabilities")

            elif device_page == 0x50:
                self._hw_revision = data[3 + payload_offset]

                lsb = data[4 + payload_offset]
                msb = data[5 + payload_offset]
                self._manufacturer_id = 256 * msb + lsb

                lsb = data[6 + payload_offset]
                msb = data[7 + payload_offset]
                self._model_number = 256 * msb + lsb

            elif device_page == 0x51:
                self._sw_revision = data[3 + payload_offset]
                self._serial_number = struct.unpack('>L', data[4 + payload_offset:8 + payload_offset])[0]

    @property
    def stride_count(self):
        """Accumulated Strides.
        """
        strides = None
        with self.lock:
            strides = self._stride_count

        return strides

    @property
    def hardware_revision(self):
        """The hardware revision of the connected device.

        If the data page 80 has not been received yet, this will be None.
        """
        hw_rev = None
        with self.lock:
            hw_rev = self._hw_revision
        return hw_rev

    @property
    def manufacturer_id(self):
        """The manufacturer id of the connected device.

        If the data page 80 has not been received yet, this will be None.
        """
        manufacturer_id = None
        with self.lock:
            manufacturer_id = self._manufacturer_id

        return manufacturer_id

    @property
    def model_number(self):
        """The model number of the connected device.

        If the data page 80 has not been received yet, this will be None.
        """
        model_number = None
        with self.lock:
            model_number = self._model_number

        return model_number

    @property
    def software_revision(self):
        """The software revision of the connected device.

        If the data page 81 has not been received yet, this will be None.
        """
        sw_rev = None
        with self.lock:
            sw_rev = self._sw_revision

        return sw_rev

    @property
    def serial_number(self):
        """The serial number of the connected device.

        If the data page 81 has not been received yet, this will be None.
        """
        serial = None
        with self.lock:
            serial = self._serial_number

        return serial
