'''
Please add your name: Jeremiah Ang
Please add your matric number: A0155950B
'''

import os
import sys
import atexit
from mininet.net import Mininet
from mininet.log import setLogLevel, info
from mininet.cli import CLI
from mininet.topo import Topo
from mininet.link import TCLink
from mininet.node import RemoteController

net = None

class TreeTopo(Topo):
            
    def __init__(self):
        # Initialize topology
        Topo.__init__(self)

    def readFromFile(self, filename):

        with open(filename) as fd:
            header = fd.readline()
            N, M, L = header.split()
            for i in range(int(N)):
                host_number = i + 1
                self.addHost('h%d' % host_number)

            for i in range(int(M)):
                switch_number = i + 1
                sconfig = {'dpid': "%016x" % switch_number}
                self.addSwitch('s%d' % switch_number, **sconfig)

            for i in range(int(L)):
                line = fd.readline()
                h1, h2, bw = line.split(",")
                linkopts = {'bw': int(bw)}
                self.addLink(h1, h2, **linkopts)

    
    # You can write other functions as you need.

    # Add hosts
    # > self.addHost('h%d' % [HOST NUMBER])

    # Add switches
    # > sconfig = {'dpid': "%016x" % [SWITCH NUMBER]}
    # > self.addSwitch('s%d' % [SWITCH NUMBER], **sconfig)

    # Add links
    # > self.addLink([HOST1], [HOST2])

def startNetwork():
    info('** Creating the tree network\n')
    topo = TreeTopo()
    topo.readFromFile("topology.in")

    global net
    net = Mininet(topo=topo, link = TCLink,
                  controller=lambda name: RemoteController(name, ip='192.168.0.123'),
                  listenPort=6633, autoSetMacs=True)

    info('** Starting the network\n')
    net.start()

    # Create QoS Queues
    # > os.system('sudo ovs-vsctl -- set Port [INTERFACE] qos=@newqos \
    #            -- --id=@newqos create QoS type=linux-htb other-config:max-rate=[LINK SPEED] queues=0=@q0,1=@q1,2=@q2 \
    #            -- --id=@q0 create queue other-config:max-rate=[LINK SPEED] other-config:min-rate=[LINK SPEED] \
    #            -- --id=@q1 create queue other-config:min-rate=[X] \
    #            -- --id=@q2 create queue other-config:max-rate=[Y]')

    info('** Running CLI\n')
    CLI(net)

def stopNetwork():
    if net is not None:
        net.stop()
        # Remove QoS and Queues
        os.system('sudo ovs-vsctl --all destroy Qos')
        os.system('sudo ovs-vsctl --all destroy Queue')


if __name__ == '__main__':
    # Force cleanup on exit by registering a cleanup function
    atexit.register(stopNetwork)

    # Tell mininet to print useful information
    setLogLevel('info')
    startNetwork()
