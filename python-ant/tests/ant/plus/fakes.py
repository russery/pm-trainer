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

from ant.core.node import Node, Channel
from ant.core.constants import RESPONSE_NO_ERROR

class FakeEventMachine():
    def __init__(self):
        self.messages = []
        self.waited_message = None

    def writeMessage(self, msg):
        self.messages.append(msg)
        return self

    def waitForAck(self, msg):
        return RESPONSE_NO_ERROR

    def waitForMessage(self, class_):
        return self.waited_message

    def registerCallback(self, callback):
        pass

    def removeCallback(self, callback):
        pass

class FakeChannel(Channel):
    def __init__(self, node, number=0):
        super(FakeChannel, self).__init__(node, number)

    def assign(self, network, channelType):
        self.assigned_network = network
        self.assigned_channel_type = channelType
        self.assigned_channel_number = self.number
        super(FakeChannel, self).assign(network, channelType)

    def open(self):
        self.open_called = True
        super(FakeChannel, self).open()

    def close(self):
        self.close_called = True

class FakeNode(Node):
    def __init__(self, event_machine):
        super(FakeNode, self).__init__(None, None)

        # Properties of the real thing
        self.evm = event_machine
        self.networks = [None] * 3
        self.channels = [FakeChannel(self, i) for i in range(0, 8)]

        # Sensing
        self.network_number = None
        self.network_key = None
        self._running = True
        self.num_channels = 8

    def set_running(self, running):
        self._running = running

    running = property(lambda self: self._running,
                       set_running)

    def reset(self, wait=True):
        pass

    def start(self, wait=True):
        self.running = True

    def stop(self):
        self.running = False

    def setNetworkKey(self, number, network=None):
        self.network_number = number
        self.network_key = network.key

    def use_all_channels(self):
        for channel in self.channels:
            channel.network = 1

