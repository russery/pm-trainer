# -*- coding: utf-8 -*-
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
# pylint: disable=missing-docstring

from __future__ import division, absolute_import, print_function, unicode_literals

from struct import pack, unpack

from six import with_metaclass

from ant.core import constants
from ant.core.constants import MESSAGE_TX_SYNC, RESPONSE_NO_ERROR
from ant.core.exceptions import MessageError


class MessageType(type):

    def __init__(cls, name, bases, dict_):
        super(MessageType, cls).__init__(name, bases, dict_)
        type_ = cls.type
        if type_ is not None:
            cls.TYPES[type_] = cls

    def __call__(cls, *args, **kwargs):
        if cls.type is not None:
            return super(MessageType, cls).__call__(*args, **kwargs)

        type_ = kwargs.get('type')
        if type_ is None:
            raise RuntimeError("Message' cannot be untyped")
        del kwargs['type']

        msgType = cls.TYPES.get(type_)
        if msgType is not None:
            return msgType(*args, **kwargs)

        if 0x00 <= type_ <= 0xFF:
            msg = super(MessageType, cls).__call__(*args, **kwargs)
            msg.type = type_
            return msg
        else:
            raise MessageError('Could not set type (type out of range).',
                               internal=Message.CORRUPTED)


MSG_HEADER_SIZE = 3
MSG_FOOTER_SIZE = 1

class Message(with_metaclass(MessageType)):
    TYPES = {}
    type = None

    INCOMPLETE = 'incomplete'
    CORRUPTED = 'corrupted'
    MALFORMED = 'malformed'

    def __init__(self, payload=None):
        self._payload = None
        self.payload = payload if payload is not None else bytearray()

    @property
    def payload(self):
        return self._payload
    @payload.setter
    def payload(self, payload):
        if len(payload) > 9:
            raise MessageError('Could not set payload (payload too long).',
                               internal=Message.MALFORMED)
        self._payload = payload

    @property
    def checksum(self):
        checksum = MESSAGE_TX_SYNC ^ len(self._payload) ^ self.type
        for byte in self._payload:
            checksum ^= byte
        return checksum

    def encode(self):
        raw, payload = bytearray(len(self)), self._payload
        raw[0:MSG_HEADER_SIZE-1] = (MESSAGE_TX_SYNC, len(payload), self.type)
        raw[MSG_HEADER_SIZE:-MSG_FOOTER_SIZE] = payload
        raw[-1] = self.checksum
        return raw

    @classmethod
    def decode(cls, raw):
        raw = bytearray(raw)
        if len(raw) < 5:
            raise MessageError('Could not decode. Message length should be >=5 bytes but was %d.' % len(raw),
                               internal=Message.INCOMPLETE)

        sync, length, type_ = raw[:MSG_HEADER_SIZE]

        if sync != MESSAGE_TX_SYNC:
            raise MessageError('Could not decode. Expected TX sync but got 0x%.2x.' % sync,
                               internal=Message.CORRUPTED)
        if len(raw) < (length + MSG_HEADER_SIZE + MSG_FOOTER_SIZE):
            raise MessageError('Could not decode. Message length should be %d but was %d.' %
                               (length + MSG_HEADER_SIZE + MSG_FOOTER_SIZE, len(raw)),
                               internal=Message.INCOMPLETE)

        msg = Message(type=type_)  # pylint: disable=unexpected-keyword-arg
        msg.payload = raw[MSG_HEADER_SIZE:length + MSG_HEADER_SIZE]

        if msg.checksum != raw[length + MSG_HEADER_SIZE]:
            raise MessageError('Could not decode. Checksum should be 0x%.2x but was 0x%.2x.' %
                               (raw[length + MSG_HEADER_SIZE], msg.checksum),
                               internal=Message.CORRUPTED)

        return msg

    def __len__(self):
        return len(self._payload) + MSG_HEADER_SIZE + MSG_FOOTER_SIZE

    def __str__(self, data=None):
        rawstr = '<' + self.__class__.__name__
        if data is not None:
            rawstr += ': ' + data
        return rawstr + '>'


class ChannelMessage(Message):
    def __init__(self, payload=b'', number=0x00):
        super(ChannelMessage, self).__init__(bytearray(1) + payload)
        self.channelNumber = number

    @property
    def channelNumber(self):
        return self._payload[0]
    @channelNumber.setter
    def channelNumber(self, number):
        if (number > 0xFF) or (number < 0x00):
            raise MessageError('Could not set channel number. Should be 0 to 255 but was %s.' % number)

        self._payload[0] = number

    def __str__(self, data=None):
        rawstr = "C(%d)" % self.channelNumber
        if data is not None:
            rawstr += ': ' + data
        return super(ChannelMessage, self).__str__(data=rawstr)


# Config messages
class ChannelUnassignMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_UNASSIGN

    def __init__(self, number=0x00):
        super(ChannelUnassignMessage, self).__init__(number=number)


class ChannelAssignMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_ASSIGN

    def __init__(self, number=0x00, channelType=0x00, network=0x00):
        super(ChannelAssignMessage, self).__init__(payload=bytearray(2), number=number)
        self.channelType = channelType
        self.networkNumber = network

    @property
    def channelType(self):
        return self._payload[1]
    @channelType.setter
    def channelType(self, type_):
        self._payload[1] = type_

    @property
    def networkNumber(self):
        return self._payload[2]
    @networkNumber.setter
    def networkNumber(self, number):
        self._payload[2] = number


class ChannelIDMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_ID

    def __init__(self, number=0x00, device_number=0x0000, device_type=0x00,
                 trans_type=0x00):
        super(ChannelIDMessage, self).__init__(payload=bytearray(4), number=number)
        self.deviceNumber = device_number
        self.deviceType = device_type
        self.transmissionType = trans_type

    @property
    def deviceNumber(self):
        return unpack(b'<H', bytes(self._payload[1:3]))[0]
    @deviceNumber.setter
    def deviceNumber(self, device_number):
        self._payload[1:3] = pack(b'<H', device_number)

    @property
    def deviceType(self):
        return self._payload[3]
    @deviceType.setter
    def deviceType(self, device_type):
        self._payload[3] = device_type

    @property
    def transmissionType(self):
        return self._payload[4]
    @transmissionType.setter
    def transmissionType(self, trans_type):
        self._payload[4] = trans_type


class ChannelPeriodMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_PERIOD

    def __init__(self, number=0x00, period=8192):
        super(ChannelPeriodMessage, self).__init__(payload=bytearray(2), number=number)
        self.channelPeriod = period

    @property
    def channelPeriod(self):
        return unpack('<H', bytes(self._payload[1:3]))[0]
    @channelPeriod.setter
    def channelPeriod(self, period):
        self._payload[1:3] = pack('<H', period)


class ChannelSearchTimeoutMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_SEARCH_TIMEOUT

    def __init__(self, number=0x00, timeout=0xFF):
        super(ChannelSearchTimeoutMessage, self).__init__(payload=bytearray(1),
                                                          number=number)
        self.timeout = timeout

    @property
    def timeout(self):
        return self._payload[1]
    @timeout.setter
    def timeout(self, timeout):
        self._payload[1] = timeout


class ChannelFrequencyMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_FREQUENCY

    def __init__(self, number=0x00, frequency=66):
        super(ChannelFrequencyMessage, self).__init__(payload=bytearray(1), number=number)
        self.frequency = frequency

    @property
    def frequency(self):
        return self._payload[1]
    @frequency.setter
    def frequency(self, frequency):
        self._payload[1] = frequency


class ChannelTXPowerMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_TX_POWER

    def __init__(self, number=0x00, power=0x00):
        super(ChannelTXPowerMessage, self).__init__(payload=bytearray(1), number=number)
        self.power = power

    @property
    def power(self):
        return self._payload[1]
    @power.setter
    def power(self, power):
        self._payload[1] = power


class NetworkKeyMessage(Message):
    type = constants.MESSAGE_NETWORK_KEY

    def __init__(self, number=0x00, key=b'\x00' * 8):
        super(NetworkKeyMessage, self).__init__(payload=bytearray(9))
        self.number = number
        self.key = key

    @property
    def number(self):
        return self._payload[0]
    @number.setter
    def number(self, number):
        self._payload[0] = number

    @property
    def key(self):
        return self._payload[1:]
    @key.setter
    def key(self, key):
        self._payload[1:] = key


class TXPowerMessage(Message):
    type = constants.MESSAGE_TX_POWER

    def __init__(self, power=0x00):
        super(TXPowerMessage, self).__init__(payload=bytearray(2))
        self.power = power

    @property
    def power(self):
        return self._payload[1]
    @power.setter
    def power(self, power):
        self._payload[1] = power


# Control messages
class SystemResetMessage(Message):
    type = constants.MESSAGE_SYSTEM_RESET

    def __init__(self):
        super(SystemResetMessage, self).__init__(payload=bytearray(1))


class ChannelOpenMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_OPEN

    def __init__(self, number=0x00):
        super(ChannelOpenMessage, self).__init__(number=number)


class ChannelCloseMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_CLOSE

    def __init__(self, number=0x00):
        super(ChannelCloseMessage, self).__init__(number=number)


class ChannelRequestMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_REQUEST

    def __init__(self, number=0x00, messageID=constants.MESSAGE_CHANNEL_STATUS):
        super(ChannelRequestMessage, self).__init__(payload=bytearray(1), number=number)
        self.messageID = messageID

    @property
    def messageID(self):
        return self._payload[1]
    @messageID.setter
    def messageID(self, messageID):
        if (messageID > 0xFF) or (messageID < 0x00):
            raise MessageError('Could not set message ID. Should be 0 to 255 but was %s.' % messageID)

        self._payload[1] = messageID


# Data messages
class ChannelBroadcastDataMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_BROADCAST_DATA

    def __init__(self, number=0x00, data=b'\x00' * 7):
        super(ChannelBroadcastDataMessage, self).__init__(payload=data, number=number)

    @property
    def data(self):
        return self._payload[1:9]


class ChannelAcknowledgedDataMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_ACKNOWLEDGED_DATA

    def __init__(self, number=0x00, data=b'\x00' * 7):
        super(ChannelAcknowledgedDataMessage, self).__init__(payload=data, number=number)

    @property
    def data(self):
        return self._payload[1:9]


class ChannelBurstDataMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_BURST_DATA

    def __init__(self, number=0x00, data=b'\x00' * 7):
        super(ChannelBurstDataMessage, self).__init__(payload=data, number=number)

    @property
    def data(self):
        return self._payload[1:9]


# Channel event messages
class ChannelEventResponseMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_EVENT

    def __init__(self, number=0x00, message_id=0x00, message_code=0x00):
        super(ChannelEventResponseMessage, self).__init__(payload=bytearray(2),
                                                          number=number)
        self.messageID = message_id
        self.messageCode = message_code

    @property
    def messageID(self):
        return self._payload[1]
    @messageID.setter
    def messageID(self, message_id):
        if (message_id > 0xFF) or (message_id < 0x00):
            raise MessageError('Could not set message ID. Should be 0 to 255 but was %s.' % message_id)

        self._payload[1] = message_id

    @property
    def messageCode(self):
        return self._payload[2]
    @messageCode.setter
    def messageCode(self, message_code):
        if (message_code > 0xFF) or (message_code < 0x00):
            raise MessageError('Could not set message code. Should be 0 to 255 but was %s.' % message_code)

        self._payload[2] = message_code

    def __str__(self):  # pylint: disable=W0221
        msgCode = self.messageCode
        if self.messageID != 1:
            return "<ChannelResponse: '%s' on C(%d): %s>" % (
                self.TYPES[self.messageID].__name__, self.channelNumber,
                'OK' if msgCode == RESPONSE_NO_ERROR else '0x%.2x' % msgCode)

        return "<ChannelEvent: C(%d): 0x%.2x>" % (self.channelNumber, msgCode)


# Requested response messages
class ChannelStatusMessage(ChannelMessage):
    type = constants.MESSAGE_CHANNEL_STATUS

    def __init__(self, number=0x00, status=0x00):
        super(ChannelStatusMessage, self).__init__(payload=bytearray(1), number=number)
        self.status = status

    @property
    def status(self):
        return self._payload[1]
    @status.setter
    def status(self, status):
        if (status > 0xFF) or (status < 0x00):
            raise MessageError('Could not set channel status. Should be 0 to 255 but was %s.' % status)

        self._payload[1] = status


class VersionMessage(Message):
    type = constants.MESSAGE_VERSION

    def __init__(self, version=b'\x00' * 9):
        super(VersionMessage, self).__init__(payload=bytearray(9))
        self.version = version

    @property
    def version(self):
        return self._payload
    @version.setter
    def version(self, version):
        if len(version) != 9:
            raise MessageError('Could not set ANT version (expected 9 bytes).')

        self.payload = bytearray(version)


class StartupMessage(Message):
    type = constants.MESSAGE_STARTUP

    def __init__(self, startupMessage=0x00):
        super(StartupMessage, self).__init__(payload=bytearray(1))
        self.startupMessage = startupMessage

    @property
    def startupMessage(self):
        return self._payload[0]
    @startupMessage.setter
    def startupMessage(self, startupMessage):
        if (startupMessage > 0xFF) or (startupMessage < 0x00):
            raise MessageError('Could not set start-up message. Should be 0 to 255 but was %s.' % startupMessage)
        self._payload[0] = startupMessage


class CapabilitiesMessage(Message):
    type = constants.MESSAGE_CAPABILITIES
    def __init__(self, max_channels=0x00, max_nets=0x00, std_opts=0x00,
                 adv_opts=0x00, adv_opts2=0x00):
        super(CapabilitiesMessage, self).__init__(payload=bytearray(4))
        self.maxChannels = max_channels
        self.maxNetworks = max_nets
        self.stdOptions = std_opts
        self.advOptions = adv_opts
        if adv_opts2 is not None:
            self.advOptions2 = adv_opts2

    @property
    def maxChannels(self):
        return self._payload[0]
    @maxChannels.setter
    def maxChannels(self, num):
        if (num > 0xFF) or (num < 0x00):
            raise MessageError('Could not set max channels. Should be 0 to 255 but was %s.' % num)
        self._payload[0] = num

    @property
    def maxNetworks(self):
        return self._payload[1]
    @maxNetworks.setter
    def maxNetworks(self, num):
        if (num > 0xFF) or (num < 0x00):
            raise MessageError('Could not set max networks. Should be 0 to 255 but was %s.' % num)
        self._payload[1] = num

    @property
    def stdOptions(self):
        return self._payload[2]
    @stdOptions.setter
    def stdOptions(self, num):
        if (num > 0xFF) or (num < 0x00):
            raise MessageError('Could not set std options. Should be 0 to 255 but was %s.' % num)
        self._payload[2] = num

    @property
    def advOptions(self):
        return self._payload[3]
    @advOptions.setter
    def advOptions(self, num):
        if (num > 0xFF) or (num < 0x00):
            raise MessageError('Could not set adv options. Should be 0 to 255 but was %s.' % num)
        self._payload[3] = num

    @property
    def advOptions2(self):
        return self._payload[4] if len(self._payload) == 5 else 0x00
    @advOptions2.setter
    def advOptions2(self, num):
        if (num > 0xFF) or (num < 0x00):
            raise MessageError('Could not set adv options 2. Should be 0 to 255 but was %s.' % num)
        if len(self._payload) == 4:
            self._payload.append(0)
        self._payload[4] = num


class SerialNumberMessage(Message):
    type = constants.MESSAGE_SERIAL_NUMBER

    def __init__(self, serial=b'\x00' * 4):
        super(SerialNumberMessage, self).__init__()
        self.serialNumber = serial

    @property
    def serialNumber(self):
        return self._payload
    @serialNumber.setter
    def serialNumber(self, serial):
        if len(serial) != 4:
            raise MessageError('Could not set serial number (expected 4 bytes).')

        self.payload = bytearray(serial)
