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

import unittest
from .fakes import *

from ant.plus.stride import *

from ant.core.node import Network, ChannelID
from ant.core.constants import NETWORK_KEY_ANT_PLUS, CHANNEL_TYPE_TWOWAY_RECEIVE
from ant.core.message import ChannelBroadcastDataMessage


class StrideTest(unittest.TestCase):
    def setUp(self):
        self.event_machine = FakeEventMachine()
        self.node = FakeNode(self.event_machine)
        self.network = Network(key=NETWORK_KEY_ANT_PLUS, name='N:ANT+')

    def test_default_channel_setup(self):
        stride = Stride(self.node, self.network)
        stride.open()

        channel = stride.channel

        self.assertEqual(0x39, channel.frequency)
        self.assertEqual(8134, channel.period)
        self.assertEqual(12, channel.searchTimeout)  # Each count is equivalent to 2.5 seconds, so 12 = 30 seconds.

        pairing_channel = ChannelID(0, 0x7c, 0)
        self.assertEqual(pairing_channel.deviceNumber, channel.id.deviceNumber)
        self.assertEqual(pairing_channel.deviceType, channel.id.deviceType)
        self.assertEqual(pairing_channel.transmissionType, channel.id.transmissionType)

        self.assertEqual(self.network.key, channel.assigned_network.key)
        self.assertEqual(self.network.name, channel.assigned_network.name)
        self.assertEqual(self.network.number, channel.assigned_network.number)

        self.assertEqual(CHANNEL_TYPE_TWOWAY_RECEIVE, channel.assigned_channel_type)
        self.assertEqual(0, channel.assigned_channel_number)

        self.assertEqual(True, channel.open_called)

    def test_paired_channel_setup(self):
        stride = Stride(self.node, self.network)
        stride.open(ChannelID(1234, 0x7c, 2))

        channel = stride.channel

        pairing_channel = ChannelID(1234, 0x7c, 2)
        self.assertEqual(pairing_channel.deviceNumber, channel.id.deviceNumber)
        self.assertEqual(pairing_channel.deviceType, channel.id.deviceType)
        self.assertEqual(pairing_channel.transmissionType, channel.id.transmissionType)

    def test_receives_page_1_channel_broadcast_message(self):
        stride = Stride(self.node, self.network)
        stride.open()

        self.assertEqual(None, stride.stride_count)

        test_data = bytearray(b'\x00' * 8)
        test_data[0] = 0x01
        test_data[6] = 0x14

        stride.channel.process(ChannelBroadcastDataMessage(data=test_data))

        self.assertEqual(20, stride.stride_count)

    def test_receives_page_80_channel_broadcast_message(self):
        stride = Stride(self.node, self.network)
        stride.open()

        self.assertEqual(None, stride.hardware_revision)
        self.assertEqual(None, stride.manufacturer_id)
        self.assertEqual(None, stride.model_number)

        test_data = bytearray(b'\x00' * 8)
        test_data[0] = 0x50
        test_data[3] = 0x05

        test_data[4] = 0x03
        test_data[5] = 0x14

        test_data[6] = 0x06
        test_data[7] = 0x12

        stride.channel.process(ChannelBroadcastDataMessage(data=test_data))

        self.assertEqual(5, stride.hardware_revision)
        self.assertEqual(5123, stride.manufacturer_id)
        self.assertEqual(4614, stride.model_number)

    def test_receives_page_81_channel_broadcast_message(self):
        stride = Stride(self.node, self.network)
        stride.open()

        self.assertEqual(None, stride.software_revision)
        self.assertEqual(None, stride.serial_number)

        test_data = bytearray(b'\x00' * 8)
        test_data[0] = 0x51
        test_data[3] = 0x02

        test_data[4] = 0x04
        test_data[5] = 0x12
        test_data[6] = 0x15
        test_data[7] = 0x07

        stride.channel.process(ChannelBroadcastDataMessage(data=test_data))

        self.assertEqual(2, stride.software_revision)
        self.assertEqual(68293895, stride.serial_number)
