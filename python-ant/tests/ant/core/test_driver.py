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

from ant.core.driver import *
from ant.core.log import *
from ant.core.message import ChannelAssignMessage

from serial import Serial, SerialException, SerialTimeoutException

dumps = []
class FakeDriver(Driver):
    def __init__(self, log = None, debug = False):
        super(FakeDriver, self).__init__(log = log, debug = debug)
        self.open_called = False
        self.close_called = False
        self.is_open = False
        self.data = bytearray(range(10))
        self.written_data = []

    @property
    def _opened(self):
        return self.is_open

    def _open(self):
        self.open_called = True
        self.is_open = True

    def _close(self):
        self.close_called = True
        self.is_open = False

    def _read(self, count):
        data_to_return = self.data[0:count]
        self.data = self.data[count:]
        return data_to_return

    def _write(self, data):
        self.written_data.append(data)

    @staticmethod
    def _dump(data, title):
        global dumps
        dumps.append((data, title))

LOG_OPEN = 0
LOG_CLOSE = 1
LOG_READ = 2
LOG_WRITE = 3
class FakeLog(LogWriter):
    def __init__(self):
        super(FakeLog, self).__init__()
        self.logs = []

    def open(self, filename):
        pass

    def close(self):
        pass

    def logOpen(self):
        self.logs.append((LOG_OPEN,None))

    def logClose(self):
        self.logs.append((LOG_CLOSE,None))

    def logRead(self, data):
        self.logs.append((LOG_READ,data))

    def logWrite(self, data):
        self.logs.append((LOG_WRITE,data))


class DriverTest(unittest.TestCase):
    def setUp(self):
        self.log = FakeLog()
        self.driver = FakeDriver(log = self.log, debug = True)

        global dumps
        dumps = []

    def test_open_close(self):
        self.driver.open()
        self.assertTrue(self.driver.open_called)
        self.assertTrue(self.log.logs[-1][0] == LOG_OPEN)

        self.driver.close()
        self.assertTrue(self.driver.close_called)
        self.assertTrue(self.log.logs[-1][0] == LOG_CLOSE)

    def test_opening_open_driver_raises_error(self):
        self.driver.open()
        with self.assertRaises(DriverError):
            self.driver.open()

    def test_closing_closed_driver_raises_error(self):
        with self.assertRaises(DriverError):
            self.driver.close()

    def test_read(self):
        self.driver.open()
        data = self.driver.read(1)

        self.assertEqual(0, data[0])
        self.assertEqual(self.driver.log.logs[-1][0], LOG_READ)
        self.assertEqual(self.driver.log.logs[-1][1], data)

        global dumps
        self.assertEqual(dumps[0], (bytearray([0]), 'READ'))

    def test_read_zero_or_less_raises_error(self):
        self.driver.open()

        with self.assertRaises(DriverError):
            self.driver.read(-1)

        with self.assertRaises(DriverError):
            self.driver.read(0)

    def test_reading_closed_driver_rasises_error(self):
        with self.assertRaises(DriverError):
            self.driver.read(1)

    def test_write(self):
        self.driver.open()

        # Write calls .encode() on it's argument...
        # It would be better if read and write both worked in terms of
        # bytearrays.
        msg = ChannelAssignMessage()
        self.driver.write(msg)

        self.assertEqual(self.driver.written_data[-1], msg.encode())
        self.assertEqual(self.driver.log.logs[-1], (LOG_WRITE, msg.encode()))

        global dumps
        self.assertEqual(dumps[0], (msg.encode(), 'WRITE'))

    def test_writing_to_closed_driver_raises_error(self):
        with self.assertRaises(DriverError):
            msg = ChannelAssignMessage()
            self.driver.write(msg)

class USB1DriverTest(unittest.TestCase):
    def setUp(self):
        this = self
        self.data = bytearray(range(10))
        self.written_data = []

        def serial_init(self, device, baud):
            pass

        def serial_is_open(self):
            return True

        def serial_get_timeout(self):
            return self._fake_timeout

        def serial_set_timeout(self, timeout):
            self._fake_timeout = timeout

        def serial_close(self):
            this.serial_close_called = True

        def serial_read(self, count):
            data_to_return = this.data[0:count]
            self.data = this.data[count:]
            return data_to_return

        def serial_write(self, data):
            this.written_data.append(data)
            return len(data)

        def serial_flush(self):
            this.serial_flush_called = True

        Serial.__init__ = serial_init
        Serial.isOpen = serial_is_open
        Serial.timeout = property(serial_get_timeout, serial_set_timeout)
        Serial.close = serial_close
        Serial.read = serial_read
        Serial.write = serial_write
        Serial.flush = serial_flush

    def test_open(self):
        driver = USB1Driver('/dev/ttyS0')
        self.assertEqual(driver._opened, False)

        driver.open()

        self.assertIsNotNone(driver._serial)
        self.assertEqual(driver._serial.timeout, 0.01)
        self.assertEqual(driver._opened, True)

    def test_open_raises_driver_error_on_SerialException(self):
        def serial_init(self, device, baud):
            raise SerialException
        Serial.__init__ = serial_init

        driver = USB1Driver('/dev/ttyS0')
        with self.assertRaises(DriverError):
            driver.open()

    def test_open_raises_driver_error_when_device_isnt_open(self):
        def serial_is_open(self):
            return False
        Serial.isOpen = serial_is_open

        driver = USB1Driver('/dev/ttyS0')
        with self.assertRaises(DriverError):
            driver.open()

    def test_close(self):
        driver = USB1Driver('/dev/ttyS0')
        driver.open()
        driver.close()

        self.assertTrue(self.serial_close_called)

    def test_read(self):
        driver = USB1Driver('/dev/ttyS0')
        driver.open()
        data = driver.read(1)

        self.assertEqual(data[0], 0)

    def test_write(self):
        driver = USB1Driver('/dev/ttyS0')
        driver.open()

        msg = ChannelAssignMessage()
        count = driver.write(msg)
        self.assertEqual(self.written_data[-1], msg.encode())
        self.assertTrue(self.serial_flush_called)

    def test_write_raises_DriverError_on_SerialTimeoutException(self):
        def serial_write(self, data):
            raise SerialTimeoutException

        Serial.write = serial_write

        driver = USB1Driver('/dev/ttyS0')
        driver.open()

        msg = ChannelAssignMessage()
        with self.assertRaises(DriverError):
            count = driver.write(msg)


class USB2DriverTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_something(self):
        pass






