# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring, invalid-name, unexpected-keyword-arg
##############################################################################
#
# Copyright (c) 2011, Martín Raúl Villalba
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

from __future__ import division, absolute_import, print_function, unicode_literals

import unittest

from ant.core.exceptions import MessageError
from ant.core.constants import MESSAGE_SYSTEM_RESET, MESSAGE_CHANNEL_ASSIGN
from ant.core.message import Message
from ant.core import message as MSG


class MessageTest(unittest.TestCase):
    def setUp(self):
        self.message = Message(type=0x00)

    def test_get_payload(self):
        msg = self.message
        with self.assertRaises(MessageError):
            msg.payload = b'\xFF' * 15
        msg.payload = b'\x11' * 5
        self.assertEquals(msg.payload, b'\x11' * 5)

    def test_get_setType(self):
        msg = self.message
        with self.assertRaises(MessageError):
            Message(type=-1)
        with self.assertRaises(MessageError):
            Message(type=300)
        msg.type = 0x23
        self.assertEquals(msg.type, 0x23)

    def test_getChecksum(self):
        msg = self.message = Message(type=MESSAGE_SYSTEM_RESET)
        self.assertEquals(msg.checksum, 0xEF)
        msg = self.message = Message(type=MESSAGE_CHANNEL_ASSIGN)
        self.assertEquals(msg.checksum, 0xE5)

    def test_size(self):
        msg = self.message
        msg.payload = b'\x11' * 7
        self.assertEquals(len(msg), 11)

    def test_encode(self):
        msg = self.message = Message(type=MESSAGE_CHANNEL_ASSIGN)
        self.assertEqual(msg.encode(), b'\xA4\x03\x42\x00\x00\x00\xE5')

    def test_decode(self):
        self.assertRaises(MessageError, Message.decode, b'\xA5\x03\x42\x00\x00\x00\xE5')
        self.assertRaises(MessageError, Message.decode,
                          b'\xA4\x14\x42' + (b'\x00' * 20) + b'\xE5')
        self.assertRaises(MessageError, Message.decode, b'\xA4\x03\x42\x01\x02\xF3\xE5')
        msg = Message.decode(b'\xA4\x03\x42\x00\x00\x00\xE5')
        self.assertEqual(len(msg), 7)
        self.assertEqual(msg.type, MESSAGE_CHANNEL_ASSIGN)
        self.assertEqual(msg.payload, b'\x00' * 3)
        self.assertEqual(msg.checksum, 0xE5)
        
        msg = Message.decode(b'\xA4\x03\x42\x00\x00\x00\xE5')
        self.assertTrue(isinstance(msg, MSG.ChannelAssignMessage))
        self.assertRaises(MessageError, Message.decode, b'\xA4\x03\xFF\x00\x00\x00\xE5')
        self.assertRaises(MessageError, Message.decode, b'\xA4\x03\x42')
        self.assertRaises(MessageError, Message.decode, b'\xA4\x05\x42\x00\x00\x00\x00')


class ChannelMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = MSG.ChannelMessage(type=MESSAGE_CHANNEL_ASSIGN)

    def test_get_ChannelNumber(self):
        msg = self.message
        self.assertEquals(msg.channelNumber, 0)
        msg.channelNumber = 3
        self.assertEquals(msg.channelNumber, 3)


class ChannelUnassignMessageTest(unittest.TestCase):
    # No currently defined methods need testing
    pass


class ChannelAssignMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = MSG.ChannelAssignMessage()

    def test_get_channelType(self):
        msg = self.message
        msg.channelType = 0x10
        self.assertEquals(msg.channelType, 0x10)

    def test_get_networkNumber(self):
        msg = self.message
        msg.networkNumber = 0x11
        self.assertEquals(msg.networkNumber, 0x11)

    def test_payload(self):
        msg = self.message
        msg.channelNumber = 0x01
        msg.channelType = 0x02
        msg.networkNumber = 0x03
        self.assertEquals(msg.payload, b'\x01\x02\x03')


class ChannelIDMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = MSG.ChannelIDMessage()

    def test_get_deviceNumber(self):
        msg = self.message
        msg.deviceNumber = 0x10FA
        self.assertEquals(msg.deviceNumber, 0x10FA)

    def test_get_deviceType(self):
        msg = self.message
        msg.deviceType = 0x10
        self.assertEquals(msg.deviceType, 0x10)

    def test_get_transmissionType(self):
        msg = self.message
        msg.transmissionType = 0x11
        self.assertEquals(msg.transmissionType, 0x11)

    def test_payload(self):
        msg = self.message
        msg.channelNumber = 0x01
        msg.deviceNumber = 0x0302
        msg.deviceType = 0x04
        msg.transmissionType = 0x05
        self.assertEquals(msg.payload, b'\x01\x02\x03\x04\x05')


class ChannelPeriodMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = MSG.ChannelPeriodMessage()

    def test_get_channelPeriod(self):
        msg = self.message
        msg.channelPeriod = 0x10FA
        self.assertEquals(msg.channelPeriod, 0x10FA)

    def test_payload(self):
        msg = self.message
        msg.channelNumber = 0x01
        msg.channelPeriod = 0x0302
        self.assertEquals(msg.payload, b'\x01\x02\x03')


class ChannelSearchTimeoutMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = MSG.ChannelSearchTimeoutMessage()

    def test_get_setTimeout(self):
        msg = self.message
        msg.timeout = 0x10
        self.assertEquals(msg.timeout, 0x10)

    def test_payload(self):
        msg = self.message
        msg.channelNumber = 0x01
        msg.timeout = 0x02
        self.assertEquals(msg.payload, b'\x01\x02')


class ChannelFrequencyMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = MSG.ChannelFrequencyMessage()

    def test_get_setFrequency(self):
        msg = self.message
        msg.frequency = 22
        self.assertEquals(msg.frequency, 22)

    def test_payload(self):
        msg = self.message
        msg.channelNumber = 0x01
        msg.frequency = 0x02
        self.assertEquals(msg.payload, b'\x01\x02')


class ChannelTXPowerMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = MSG.ChannelTXPowerMessage()

    def test_get_setPower(self):
        msg = self.message
        msg.power = 0xFA
        self.assertEquals(msg.power, 0xFA)

    def test_payload(self):
        msg = self.message
        msg.channelNumber = 0x01
        msg.power = 0x02
        self.assertEquals(msg.payload, b'\x01\x02')


class NetworkKeyMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = MSG.NetworkKeyMessage()

    def test_get_setNumber(self):
        msg = self.message
        msg.number = 0xFA
        self.assertEquals(msg.number, 0xFA)

    def test_get_setKey(self):
        msg = self.message
        msg.key = b'\xFD' * 8
        self.assertEquals(msg.key, b'\xFD' * 8)

    def test_payload(self):
        msg = self.message
        msg.number = 0x01
        msg.key = b'\x02\x03\x04\x05\x06\x07\x08\x09'
        self.assertEquals(msg.payload, b'\x01\x02\x03\x04\x05\x06\x07\x08\x09')


class TXPowerMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = MSG.TXPowerMessage()

    def test_get_setPower(self):
        msg = self.message
        msg.power = 0xFA
        self.assertEquals(msg.power, 0xFA)

    def test_payload(self):
        msg = self.message
        msg.power = 0x01
        self.assertEquals(msg.payload, b'\x00\x01')


class SystemResetMessageTest(unittest.TestCase):
    # No currently defined methods need testing
    pass


class ChannelOpenMessageTest(unittest.TestCase):
    # No currently defined methods need testing
    pass


class ChannelCloseMessageTest(unittest.TestCase):
    # No currently defined methods need testing
    pass


class ChannelRequestMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = MSG.ChannelRequestMessage()

    def test_get_messageID(self):
        msg = self.message
        with self.assertRaises(MessageError):
            msg.messageID = 0xFFFF
        msg.messageID = 0xFA
        self.assertEquals(msg.messageID, 0xFA)

    def test_payload(self):
        msg = self.message
        msg.channelNumber = 0x01
        msg.messageID = 0x02
        self.assertEquals(msg.payload, b'\x01\x02')


class ChannelBroadcastDataMessageTest(unittest.TestCase):
    # No currently defined methods need testing
    pass


class ChannelAcknowledgedDataMessageTest(unittest.TestCase):
    # No currently defined methods need testing
    pass


class ChannelBurstDataMessageTest(unittest.TestCase):
    # No currently defined methods need testing
    pass


class ChannelEventMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = MSG.ChannelEventResponseMessage()

    def test_get_messageID(self):
        msg = self.message
        with self.assertRaises(MessageError):
            msg.messageID = 0xFFFF
        msg.messageID = 0xFA
        self.assertEquals(msg.messageID, 0xFA)

    def test_get_messageCode(self):
        msg = self.message
        with self.assertRaises(MessageError):
            msg.messageCode = 0xFFFF
        msg.messageCode = 0xFA
        self.assertEquals(msg.messageCode, 0xFA)

    def test_payload(self):
        msg = self.message
        msg.channelNumber = 0x01
        msg.messageID = 0x02
        msg.messageCode = 0x03
        self.assertEquals(msg.payload, b'\x01\x02\x03')


class ChannelStatusMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = MSG.ChannelStatusMessage()

    def test_get_status(self):
        msg = self.message
        with self.assertRaises(MessageError):
            msg.status = 0xFFFF
        msg.status = 0xFA
        self.assertEquals(msg.status, 0xFA)

    def test_payload(self):
        msg = self.message
        msg.channelNumber = 0x01
        msg.status = 0x02
        self.assertEquals(msg.payload, b'\x01\x02')


class VersionMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = MSG.VersionMessage()

    def test_get_version(self):
        msg = self.message
        with self.assertRaises(MessageError):
            msg.version =  '1234'
        msg.version = b'\xAB' * 9
        self.assertEquals(msg.version, b'\xAB' * 9)

    def test_payload(self):
        msg = self.message
        msg.version = b'\x01' * 9
        self.assertEquals(msg.payload, b'\x01' * 9)


class CapabilitiesMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = MSG.CapabilitiesMessage()

    def test_get_maxChannels(self):
        msg = self.message
        with self.assertRaises(MessageError):
            msg.maxChannels = 0xFFFF
        msg.maxChannels = 0xFA
        self.assertEquals(msg.maxChannels, 0xFA)

    def test_get_maxNetworks(self):
        msg = self.message
        with self.assertRaises(MessageError):
            msg.maxNetworks = 0xFFFF
        msg.maxNetworks = 0xFA
        self.assertEquals(msg.maxNetworks, 0xFA)

    def test_get_stdOptions(self):
        msg = self.message
        with self.assertRaises(MessageError):
            msg.stdOptions = 0xFFFF
        msg.stdOptions = 0xFA
        self.assertEquals(msg.stdOptions, 0xFA)

    def test_get_advOptions(self):
        msg = self.message
        with self.assertRaises(MessageError):
            msg.advOptions = 0xFFFF
        msg.advOptions = 0xFA
        self.assertEquals(msg.advOptions, 0xFA)

    def test_get_advOptions2(self):
        msg = self.message
        with self.assertRaises(MessageError):
            msg.advOptions2 = 0xFFFF
        msg.advOptions2 = 0xFA
        self.assertEquals(msg.advOptions2, 0xFA)
        msg = MSG.CapabilitiesMessage(adv_opts2=None)
        self.assertEquals(len(msg.payload), 4)

    def test_payload(self):
        msg = self.message
        msg.maxChannels = 0x01
        msg.maxNetworks = 0x02
        msg.stdOptions = 0x03
        msg.advOptions = 0x04
        msg.advOptions2 = 0x05
        self.assertEquals(msg.payload, b'\x01\x02\x03\x04\x05')


class SerialNumberMessageTest(unittest.TestCase):
    def setUp(self):
        self.message = MSG.SerialNumberMessage()

    def test_get_serialNumber(self):
        msg = self.message
        with self.assertRaises(MessageError):
            msg.serialNumber = b'\xFF' * 8
        msg.serialNumber = b'\xFA\xFB\xFC\xFD'
        self.assertEquals(msg.serialNumber, b'\xFA\xFB\xFC\xFD')

    def test_payload(self):
        msg = self.message
        msg.serialNumber = b'\x01\x02\x03\x04'
        self.assertEquals(msg.payload, b'\x01\x02\x03\x04')
