# -*- coding: utf-8 -*-
"""Demonstrate the use of the ANT+ Power Profile

"""

import time

from ant.core import driver
from ant.core.node import Node, Network, ChannelID
from ant.core.constants import NETWORK_KEY_ANT_PLUS, NETWORK_NUMBER_PUBLIC
from ant.plus.power import *

from config import *

device = driver.USB2Driver(log=LOG, debug=False)
antnode = Node(device)
antnode.start()
network = Network(key=NETWORK_KEY_ANT_PLUS, name='N:ANT+')
antnode.setNetworkKey(NETWORK_NUMBER_PUBLIC, network)

def device_found(self, device_number, transmission_type):
    print("Detect monitor device number: %d, transmission type: %d" % (device_number, transmission_type))

def power_data(eventCount, pedalDiff, pedalPowerRatio, cadence, accumPower, instantPower):
    print ("Instant Power: %d, InstantCadence: %d" % (instantPower,cadence))

power  = BicyclePower(antnode, network, callbacks = {'onDevicePaired': device_found,
                                              'onPowerData': power_data})

# Unpaired, search:
power.open()


monitor = None
while True:
    try:
        time.sleep(1)
    except KeyboardInterrupt:
        break

power.close()
antnode.stop()
