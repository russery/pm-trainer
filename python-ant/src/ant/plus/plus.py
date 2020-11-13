# -*- coding: utf-8 -*-
"""ANT+ Device Profile connection and event handling

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
from threading import Lock
from enum import Enum

from ant.core.constants import *
from ant.core.message import *
from ant.core.node import ChannelID


class ChannelState(Enum):
    SEARCHING = 1
    SEARCH_TIMEOUT = 2
    OPEN = 3
    CLOSED = 4


class DeviceProfile(object):

    channelFrequency = 0x39  # Subclasses can override if this needs to be different
    channelPeriod = 0   # Subclasses should override
    deviceType = 0      # Subclasses should override
    name = 'Ant Device'

    def __init__(self, node, network, callbacks=None):
        """
        :param node: The ANT node to use
        :param network: The ANT network to connect on
        :param callbacks: Dictionary of string-function pairs specifying the callbacks to
                use for each event. Events supported by `DeviceProfile` are:
                'onDevicePaired'
                'onSearchTimeout'
                'onChannelClosed'
        """
        self.node = node
        self.network = network
        self.callbacks = callbacks if callbacks is not None else {}
        self.channel = None
        self.lock = Lock()
        self.state = ChannelState.CLOSED
        self._detected = False

    def open(self, channelId=None, searchTimeout=30):
        """Pairs with a device and opens a channel for communicating.
        Once pairing has completed and the first data message has been recieved, the onDevicePaired
        callback will be called with the full channel ID.
        If a device is not found within `searchTimeout`, the onSearchTimeout callback will be called.

        :param channelId: The unique ID for each device link in a network.
                Set to None to find any device of this type. Set to an instance of
                `ant.node.ChannelID` to pair with a specific device.
        :param searchTimeout: Time to allow for searching, in seconds.
        """
        deviceNumber = 0 if channelId is None else channelId.deviceNumber
        deviceType = self.deviceType if channelId is None else channelId.deviceType
        transmissionType = 0 if channelId is None else channelId.transmissionType

        self.channel = self.node.getFreeChannel()
        self.channel.registerCallback(self)
        self.channel.assign(self.network, CHANNEL_TYPE_TWOWAY_RECEIVE)
        self.channel.setID(deviceType, deviceNumber, transmissionType)
        self.channel.frequency = self.channelFrequency
        self.channel.period = self.channelPeriod
        self.channel.searchTimeout = int(searchTimeout / 2.5)  # ANT spec says each count is equivalent to 2.5 seconds.

        self.channel.open()
        self.state = ChannelState.SEARCHING

    def close(self):
        self.channel.close()

    def wrapDifference(self, current, previous, max):
        if previous > current:
            correction = current + max
            difference = correction - previous
        else:
            difference = current - previous
        return difference

    def process(self, msg, channel):
        """Handles incoming channel messages
        Converts messages to ANT+ device specific data.
        """
        if isinstance(msg, ChannelBroadcastDataMessage):
            self.processData(msg.data)

            if not self._detected:
                req_msg = ChannelRequestMessage(messageID=MESSAGE_CHANNEL_ID)
                self.channel.send(req_msg)
                self._detected = True

        elif isinstance(msg, ChannelIDMessage):
            self.state = ChannelState.OPEN
            onDevicePaired = self.callbacks.get('onDevicePaired')
            if onDevicePaired:
                onDevicePaired(self, ChannelID(msg.deviceNumber, msg.deviceType, msg.transmissionType))

        elif isinstance(msg, ChannelEventResponseMessage):
            if msg.messageCode == EVENT_CHANNEL_CLOSED:
                self.state = ChannelState.CLOSED
                onChannelClosed = self.callbacks.get('onChannelClosed')
                if onChannelClosed:
                    onChannelClosed(self)
            elif msg.messageCode == EVENT_RX_SEARCH_TIMEOUT:
                self.state = ChannelState.SEARCH_TIMEOUT
                onSearchTimeout = self.callbacks.get('onSearchTimeout')
                if onSearchTimeout:
                    onSearchTimeout(self)
            elif msg.messageCode == EVENT_RX_FAIL_GO_TO_SEARCH:
                self.state = ChannelState.SEARCHING

    def processData(self, data):
        """Handles broadcast data messages.
        Subclasses should override to process data specific to the device profile.
        """
        pass