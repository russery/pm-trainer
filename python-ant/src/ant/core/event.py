# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring
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
#
# Beware s/he who enters: uncommented, non unit-tested,
# don't-fix-it-if-it-ain't-broken kind of threaded code ahead.
#

from __future__ import division, absolute_import, print_function, unicode_literals

from time import sleep, time
from threading import Lock, Thread

from ant.core.constants import MESSAGE_TX_SYNC
from ant.core.message import Message, ChannelEventResponseMessage
from ant.core.exceptions import MessageError, MessageTimeoutError
from usb.core import USBError


def EventPump(evm):
    buffer_ = bytearray()
    while True:
        with evm.runningLock:
            if not evm.running:
                break

        try:
            buffer_ += evm.driver.read(20)
        except USBError as e:
            if e.errno in (60, 110):  # timeout
                continue
            else:
                raise

        messages = []
        while buffer_:
            try:
                msg = Message.decode(buffer_)
                messages.append(msg)
                buffer_ = buffer_[len(msg):]
            except MessageError as err:
                if err.internal is not Message.INCOMPLETE:
                    i, length = 1, len(buffer_)
                    # move to the next SYNC byte
                    while i < length and buffer_[i] != MESSAGE_TX_SYNC:
                        i += 1
                    buffer_ = buffer_[i:]
                else:
                    break

        with evm.evmCallbackLock:
            for message in messages:
                for callback in evm.callbacks:
                    try:
                        callback.process(message)
                    except Exception as err:  # pylint: disable=broad-except
                        print(err)


class EventCallback(object):

    def process(self, msg):
        raise NotImplementedError()


class EventMachineCallback(EventCallback):
    MAX_QUEUE = 25
    WAIT_UNTIL = staticmethod(lambda _, __: None)

    def __init__(self):
        self.messages = []
        self.lock = Lock()

    def process(self, msg):
        with self.lock:
            messages = self.messages
            messages.append(msg)
            MAX_QUEUE = self.MAX_QUEUE
            if len(messages) > MAX_QUEUE:
                self.messages = messages[-MAX_QUEUE:]

    def waitFor(self, foo, timeout=10):  # pylint: disable=blacklisted-name
        messages = self.messages
        basetime = time()
        while time() - basetime < timeout:
            with self.lock:
                for emsg in messages:
                    if self.WAIT_UNTIL(foo, emsg):
                        messages.remove(emsg)
                        return emsg
            sleep(0.001)
        raise MessageTimeoutError("%s: timeout" % str(foo), internal=foo)

class AckCallback(EventMachineCallback):
    WAIT_UNTIL = staticmethod(lambda msg, emsg: msg.type == emsg.messageID)

    def process(self, msg):
        if isinstance(msg, ChannelEventResponseMessage) and \
           msg.messageID != 1:  # response message, not event
            super(AckCallback, self).process(msg)


class MsgCallback(EventMachineCallback):
    WAIT_UNTIL = staticmethod(lambda class_, emsg: isinstance(emsg, class_))


class EventMachine(object):
    def __init__(self, driver):
        self.driver = driver
        self.callbacks = set()
        self.eventPump = None
        self.running = False

        self.evmCallbackLock = Lock()
        self.runningLock = Lock()

        self.ack = ack = AckCallback()
        self.msg = msg = MsgCallback()
        self.registerCallback(ack)
        self.registerCallback(msg)

    def registerCallback(self, callback):
        with self.evmCallbackLock:
            self.callbacks.add(callback)

    def removeCallback(self, callback):
        with self.evmCallbackLock:
            try:
                self.callbacks.remove(callback)
            except KeyError:
                pass

    def writeMessage(self, msg):
        self.driver.write(msg)
        return self

    def waitForAck(self, msg):
        return self.ack.waitFor(msg).messageCode

    def waitForMessage(self, class_, timeout=10):
        return self.msg.waitFor(class_, timeout)

    def start(self, name=None, driver=None):
        with self.runningLock:
            if self.running:
                return
            self.running = True

            if driver is not None:
                self.driver = driver
            self.driver.open()

            evPump = self.eventPump = Thread(name=name, target=EventPump, args=(self,))
            evPump.start()

    def stop(self):
        with self.runningLock:
            if not self.running:
                return
            self.running = False
        self.eventPump.join()
        self.driver.close()
