"""
Extending on demo-03, implements an event callback we can use to process the
incoming data.

"""

from __future__ import print_function

import sys
import time

from ant.core import driver
from ant.core import node
from ant.core import event
from ant.core import message
from ant.core.constants import *

from config import *

NETKEY = '\xB9\xA5\x21\xFB\xBD\x72\xC3\x45'

command_id = 0x46
send_times = 2
pg_num = 1
DP_PAYLOAD = bytearray([command_id, 0xFF, 0xFF, 0, 0, send_times, pg_num, 1])
#DP_PAYLOAD = bytearray([255, 255, 0, 0, send_times, pg_num, 1])
CHANNEL = 1 #TODO: not really, channel is set much later
pay = DP_PAYLOAD
p1 = message.ChannelAcknowledgedDataMessage(number=CHANNEL,data=pay)
pay[6] = 2
p2 = message.ChannelAcknowledgedDataMessage(number=CHANNEL,data=pay)
pay[6] = 3
p3 = message.ChannelAcknowledgedDataMessage(number=CHANNEL,data=pay)
pay[6] = 4
p4 = message.ChannelAcknowledgedDataMessage(number=CHANNEL,data=pay)

RSP = bytearray([0xFF, 0x3A])

class RsMessage(message.ChannelMessage):
    type = 0x63
    def __init__(self, number=0x00):
        super(RsMessage, self).__init__(number=number, payload=RSP)


rs = RsMessage(0)
RECV = 0

class WeightListener(event.EventCallback):
    def process(self, msg, _channel):
        global RECV
        if isinstance(msg, message.ChannelBroadcastDataMessage):
#            print('R%04X: ' % RECV, *('%02X' % ord(byte) for byte in msg.payload))
            data = str(msg.payload)
            print('%04X' % RECV, *('%02X' % ord(byte) for byte in data))
#            print [map(ord, msg.payload)]
            page_number = msg.payload[1]
            RECV += 1
            if   page_number == 1:
                pass
            elif page_number == 2:
                pass
            elif page_number == 3:
                pass
            elif page_number == 4:
                pass

def delete_channel(channel):
    channel.close()
    channel.unassign()

def reset_channel(antnode, channel=None):
    if channel:
        delete_channel(channel)
    channel = antnode.getFreeChannel()
    channel.name = 'C:WGT'
    channel.assign(net, CHANNEL_TYPE_TWOWAY_RECEIVE)
    channel.setID(119, 0, 0)
    channel.period = 0x2000  # nebo 0x0020 ???
    channel.frequency = 0x39

    rs.channelNumber = channel.deviceNumber
    channel.node.evm.writeMessage(rs)

    channel.searchTimeout = TIMEOUT_NEVER
    channel.open()

    channel.registerCallback(WeightListener())

    return channel


# Initialize
#LOG=None
#DEBUG=False

stick = driver.USB1Driver(SERIAL, log=LOG, debug=DEBUG)
antnode = node.Node(stick)
antnode.start()

# Setup channel
net = node.Network(name='N:ANT+', key=NETKEY)
antnode.setNetworkKey(0, net)

channel = reset_channel(antnode)
restart = int(time.time())
# Wait
print("Listening for weight scale events ...")
while True:
    time.sleep(0.1)
    # Restart channel every 3 seconds
    now = int(time.time())
    if (now % 3 == 0) and (now != restart):
        channel = reset_channel(antnode, channel)
        RECV = 0
        restart = now


# Shutdown
delete_channel(channel)
antnode.stop()
