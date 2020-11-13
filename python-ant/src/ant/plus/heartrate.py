# -*- coding: utf-8 -*-
"""ANT+ Heart Rate Device Profile

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

from .plus import DeviceProfile


class HeartRate(DeviceProfile):
    """ANT+ Heart Rate Monitor"""

    channelPeriod = 8070
    deviceType = 0x78
    name = 'Heart Rate'

    def __init__(self, node, network, callbacks=None):
        """
        :param node: The ANT node to use
        :param network: The ANT network to connect on
        :param callbacks: Dictionary of string-function pairs specifying the callbacks to
                use for each event. In addition to the events supported by `DeviceProfile`,
                `HeartRate` also has the following:
                'onHeartRateData'
        """
        super(HeartRate, self).__init__(node, network, callbacks)

        self._computed_heart_rate = None
        self._previous_beat_count = 0
        self._previous_event_time = 0
        self._accumulated_event_time = 0.0

        self._page_toggle_observed = False
        self._page_toggle = None

        self._detected_device = None

    def event_time_correction(self, time_difference):
        return time_difference * 1000 / 1024

    def processData(self, data):
        page_index = 0
        prev_event_time_lsb_index = 2
        prev_event_time_msb_index = 3
        event_time_lsb_index = 4
        event_time_msb_index = 5
        heart_beat_count_index = 6
        computed_heart_rate_index = 7

        rr_interval = None
        event_time = None
        with self.lock:
            self._computed_heart_rate = data[computed_heart_rate_index]

            page = data[page_index] & 0x7f
            page_toggle = data[page_index] >> 7

            if not self._page_toggle_observed:
                if self._page_toggle is None:
                    self._page_toggle = page_toggle
                else:
                    if self._page_toggle != page_toggle:
                        self._page_toggle_observed = True

            beat_count = data[heart_beat_count_index]
            beat_count_difference = self.wrapDifference(beat_count, self._previous_beat_count, 256)
            self._previous_beat_count = beat_count

            time_difference = None
            if self._page_toggle_observed and page == 4:
                prev_event_time = (data[prev_event_time_msb_index] << 8) + (data[prev_event_time_lsb_index])
                event_time = (data[event_time_msb_index] << 8) + (data[event_time_lsb_index])
                time_difference = self.wrapDifference(event_time, prev_event_time, 65535)
            else:
                event_time = (data[event_time_msb_index] << 8) + (data[event_time_lsb_index])
                if beat_count_difference == 1:
                    time_difference = self.wrapDifference(event_time, self._previous_event_time, 65535)
                else:
                    time_difference = None

            if time_difference is not None:
                rr_interval = self.event_time_correction(time_difference)
            # Update accumulated time
            event_time = (data[event_time_msb_index] << 8) + (data[event_time_lsb_index])
            time_difference = self.wrapDifference(event_time, self._previous_event_time, 65535)
            self._previous_event_time = event_time
            self._accumulated_event_time += float(self.event_time_correction(time_difference)) / 1000

            callback = self.callbacks.get('onHeartRateData')
            if callback:
                callback(self._computed_heart_rate, self._accumulated_event_time, rr_interval)

    @property
    def computed_heart_rate(self):
        """The computed heart rate calculated by the connected monitor.
        """
        rate = None
        with self.lock:
            rate = self._computed_heart_rate
        return rate
