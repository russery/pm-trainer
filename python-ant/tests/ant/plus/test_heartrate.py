# -*- coding: utf-8 -*-

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

import struct
import unittest

from ant.core.message import *
from ant.core.node import Network
from ant.plus.heartrate import *
from ant.plus.plus import *
from .fakes import *


def send_fake_heartrate_msg(hr):
    test_data = bytearray(b'\x00' * 8)
    test_data[6] = 23
    test_data[7] = 0x64
    hr.channel.process(ChannelBroadcastDataMessage(data=test_data))


def create_msg(page_number = 0, page_toggle = 0, page_bytes = bytearray(b'\xff' * 3),
               beat_time = 2013, beat_count = 131, computed_hr = 0xb4):
    channel_number = 0
    msg = bytearray(b'\x00' * 9)
    struct.pack_into("<BBBBBHBB", msg, 0, channel_number,
                     page_number | (page_toggle << 7),
                     page_bytes[0], page_bytes[1], page_bytes[2],
                     beat_time, beat_count, computed_hr)

    return msg


class HeartRateTest(unittest.TestCase):
    def setUp(self):
        self.event_machine = FakeEventMachine()
        self.node = FakeNode(self.event_machine)
        self.network = Network(key=NETWORK_KEY_ANT_PLUS, name='N:ANT+')

    def test_default_channel_setup(self):
        hr = HeartRate(self.node, self.network)
        hr.open()

        self.assertEqual(0x39, hr.channel.frequency)
        self.assertEqual(8070, hr.channel.period)
        self.assertEqual(12, hr.channel.searchTimeout)  # Each count is equivalent to 2.5 seconds, so 12 = 30 seconds.

        pairing_channel = ChannelID(0, 0x78, 0)
        self.assertEqual(pairing_channel.deviceNumber, hr.channel.id.deviceNumber)
        self.assertEqual(pairing_channel.deviceType, hr.channel.id.deviceType)
        self.assertEqual(pairing_channel.transmissionType, hr.channel.id.transmissionType)

        self.assertEqual(self.network.key, hr.channel.assigned_network.key)
        self.assertEqual(self.network.name, hr.channel.assigned_network.name)
        self.assertEqual(self.network.number, hr.channel.assigned_network.number)

        self.assertEqual(CHANNEL_TYPE_TWOWAY_RECEIVE, hr.channel.assigned_channel_type)
        self.assertEqual(0, hr.channel.assigned_channel_number)

        self.assertEqual(True, hr.channel.open_called)

    def test_paired_channel_setup(self):
        hr = HeartRate(self.node, self.network)
        hr.open(ChannelID(1234, 0x78, 2))

        pairing_channel = ChannelID(1234, 0x78, 2)
        self.assertEqual(pairing_channel.deviceNumber, hr.channel.id.deviceNumber)
        self.assertEqual(pairing_channel.deviceType, hr.channel.id.deviceType)
        self.assertEqual(pairing_channel.transmissionType, hr.channel.id.transmissionType)

    def test_receives_channel_broadcast_message(self):
        hr = HeartRate(self.node, self.network)
        hr.open()

        self.assertEqual(None, hr.computed_heart_rate)

        test_data = bytearray(b'\x00' * 8)
        test_data[7] = 0x64
        hr.channel.process(ChannelBroadcastDataMessage(data=test_data))

        self.assertEqual(100, hr.computed_heart_rate)

    def test_channel_order_of_operations(self):
        # This test really belongs to the Channel class, but it doesn't
        # handle this... yet.
        hr = HeartRate(self.node, self.network)
        hr.open()

        messages = self.event_machine.messages
        self.assertEqual(6, len(messages))

        # Assignment must come first (9.5.2.2)
        self.assertIsInstance(messages[0], ChannelAssignMessage)

        # The rest can come in any order, though setting Channel ID is
        # typically second in the documentation
        self.assertIsInstance(messages[1], ChannelIDMessage)
        self.assertIsInstance(messages[2], ChannelFrequencyMessage)
        self.assertIsInstance(messages[3], ChannelPeriodMessage)
        self.assertIsInstance(messages[4], ChannelSearchTimeoutMessage)

        # Open must be last (9.5.4.2)
        self.assertIsInstance(messages[5], ChannelOpenMessage)

    def test_unpaired_channel_queries_id(self):
        hr = HeartRate(self.node, self.network)
        hr.open()

        # This should be higher level, but Node nor Channel provide it
        send_fake_heartrate_msg(hr)

        messages = self.event_machine.messages
        self.assertIsInstance(messages[6], ChannelRequestMessage)
        self.assertEqual(messages[6].messageID, MESSAGE_CHANNEL_ID)

    def test_receives_channel_id_message(self):
        hr = HeartRate(self.node, self.network)
        hr.open()

        hr.channel.process(ChannelIDMessage(0, 23358, 120, 1))

        self.assertEqual(ChannelState.OPEN, hr.state)

    def test_paired_but_unknown_device_queries_id(self):
        hr = HeartRate(self.node, self.network)
        hr.open(ChannelID(23358, 0x78, 1))

        send_fake_heartrate_msg(hr)

        messages = self.event_machine.messages
        self.assertIsInstance(messages[6], ChannelRequestMessage)
        self.assertEqual(messages[6].messageID, MESSAGE_CHANNEL_ID)

        hr.channel.process(ChannelIDMessage(0, 23358, 120, 1))
        self.assertEqual(ChannelState.OPEN, hr.state)

    def test_channel_search_timeout_and_close(self):
        hr = HeartRate(self.node, self.network)
        hr.open()

        self.assertEqual(ChannelState.SEARCHING, hr.state)

        msg = ChannelEventResponseMessage(0x00, MESSAGE_CHANNEL_EVENT, EVENT_RX_SEARCH_TIMEOUT)
        hr.channel.process(msg)

        self.assertEqual(ChannelState.SEARCH_TIMEOUT, hr.state)

        msg = ChannelEventResponseMessage(0x00, MESSAGE_CHANNEL_EVENT, EVENT_CHANNEL_CLOSED)
        hr.channel.process(msg)
        self.assertEqual(ChannelState.CLOSED, hr.state)

    def test_channel_rx_fail_over_to_search(self):
        hr = HeartRate(self.node, self.network)
        hr.open()

        self.assertEqual(ChannelState.SEARCHING, hr.state)

        send_fake_heartrate_msg(hr)
        hr.channel.process(ChannelIDMessage(0, 23358, 120, 1))

        self.assertEqual(ChannelState.OPEN, hr.state)

        msg = ChannelEventResponseMessage(0x00, MESSAGE_CHANNEL_EVENT, EVENT_RX_FAIL_GO_TO_SEARCH)
        hr.channel.process(msg)

        self.assertEqual(ChannelState.SEARCHING, hr.state)

    def test_device_detected_callback(self):
        channelId = None
        def callback(device, id):
            nonlocal channelId
            channelId = id

        hr = HeartRate(self.node, self.network, callbacks = {'onDevicePaired': callback})
        hr.open()

        hr.channel.process(ChannelIDMessage(0, 23358, 120, 1))

        self.assertIsNotNone(channelId)
        self.assertEqual(23358, channelId.deviceNumber)
        self.assertEqual(120, channelId.deviceType)
        self.assertEqual(1, channelId.transmissionType)

    def test_data_callback(self):
        heartRate = None
        def callback(computedHeartRate, accumulatedEventTime, rrInterval):
            nonlocal heartRate
            heartRate = computedHeartRate

        hr = HeartRate(self.node, self.network, callbacks = {'onHeartRateData': callback})
        hr.open()

        send_fake_heartrate_msg(hr)
        self.assertEqual(100, heartRate)

    def test_consecutive_beat_page_0_r_r_interval(self):
        time = None
        interval = None
        def callback(computedHeartRate, accumulatedEventTime, rrInterval):
            nonlocal time
            nonlocal interval
            time = accumulatedEventTime
            interval = rrInterval

        hr = HeartRate(self.node, self.network, callbacks = {'onHeartRateData': callback})
        hr.open()

        hr.processData(create_msg(beat_time = 1672, beat_count = 130, computed_hr = 0xb4)[1:])
        hr.processData(create_msg(beat_time = 2013, beat_count = 131, computed_hr = 0xb4)[1:])

        self.assertAlmostEqual(333.0078125, interval)
        self.assertAlmostEqual(1.9658203125, time)

    def test_non_consecutive_beat_page_0_r_r_interval(self):
        time = None
        interval = None
        def callback(computedHeartRate, accumulatedEventTime, rrInterval):
            nonlocal time
            nonlocal interval
            time = accumulatedEventTime
            interval = rrInterval

        hr = HeartRate(self.node, self.network, callbacks = {'onHeartRateData': callback})
        hr.open()

        hr.processData(create_msg(beat_time = 1672, beat_count = 130, computed_hr = 0xb4)[1:])
        hr.processData(create_msg(beat_time = 2013, beat_count = 132, computed_hr = 0xb4)[1:])

        self.assertEqual(None, interval)
        self.assertAlmostEqual(1.9658203125, time)

    def test_consecutive_page_0_r_r_interval_wraparound(self):
        time = None
        interval = None
        def callback(computedHeartRate, accumulatedEventTime, rrInterval):
            nonlocal time
            nonlocal interval
            time = accumulatedEventTime
            interval = rrInterval

        hr = HeartRate(self.node, self.network, callbacks = {'onHeartRateData': callback})
        hr.open()

        hr.processData(create_msg(beat_time = 65535, beat_count = 255, computed_hr = 0xb4)[1:])
        hr.processData(create_msg(beat_time = 341, beat_count = 0, computed_hr = 0xb4)[1:])

        self.assertAlmostEqual(333.0078125, interval)
        self.assertAlmostEqual(64.33203125, time)

    def test_page_gt_0_ignored_until_toggle_bit_changes(self):
        time = None
        interval = None
        def callback(computedHeartRate, accumulatedEventTime, rrInterval):
            nonlocal time
            nonlocal interval
            time = accumulatedEventTime
            interval = rrInterval

        hr = HeartRate(self.node, self.network, callbacks = {'onHeartRateData': callback})
        hr.open()

        page_bytes = bytearray(b'\xff' * 3)
        struct.pack_into("<BH", page_bytes, 0, 0xff, 1672)

        hr.processData(create_msg(page_number = 4, page_toggle = 0,
                                page_bytes = page_bytes, beat_time = 2013,
                                beat_count = 131, computed_hr = 0xb4)[1:])
        self.assertEqual(None, interval)

        hr.processData(create_msg(page_number = 4, page_toggle = 1,
                                page_bytes = page_bytes, beat_time = 2013,
                                beat_count = 131, computed_hr = 0xb4)[1:])
        self.assertAlmostEqual(333.0078125, interval)
        self.assertAlmostEqual(1.9658203125, time)

    def test_page_2_and_3_return_consecutive_beat_rr_interval(self):
        interval = None
        def callback(computedHeartRate, accumulatedEventTime, rrInterval):
            nonlocal interval
            interval = rrInterval

        hr = HeartRate(self.node, self.network, callbacks = {'onHeartRateData': callback})
        hr.open()

        page_bytes = bytearray(b'\xff' * 3)

        hr.processData(create_msg(page_number = 2, page_toggle = 0,
                                page_bytes = page_bytes, beat_time = 2000,
                                beat_count = 131, computed_hr = 0xb4)[1:])
        self.assertEqual(None, interval)

        hr.processData(create_msg(page_number = 2, page_toggle = 1,
                                page_bytes = page_bytes, beat_time = 2500,
                                beat_count = 132, computed_hr = 0xb4)[1:])
        self.assertAlmostEqual(488.28125, interval)

        hr.processData(create_msg(page_number = 3, page_toggle = 0,
                                page_bytes = page_bytes, beat_time = 3000,
                                beat_count = 133, computed_hr = 0xb4)[1:])
        self.assertAlmostEqual(488.28125, interval)

        hr.processData(create_msg(page_number = 3, page_toggle = 1,
                                page_bytes = page_bytes, beat_time = 3500,
                                beat_count = 134, computed_hr = 0xb4)[1:])
        self.assertAlmostEqual(488.28125, interval)

    def test_close_calls_close_on_channel(self):
        closeCalled = False
        def callback(device):
            nonlocal closeCalled
            closeCalled = True

        hr = HeartRate(self.node, self.network, callbacks = {'onChannelClosed': callback})
        hr.open()

        hr.process(ChannelEventResponseMessage(0, MESSAGE_CHANNEL_EVENT, EVENT_CHANNEL_CLOSED), hr.channel)

        self.assertEqual(True, closeCalled)
        self.assertEqual(ChannelState.CLOSED, hr.state)

