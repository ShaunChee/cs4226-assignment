'''
Please add your name: Jeremiah Ang
Please add your matric number: A0155950B
'''

import os
import sys
import atexit
import time
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
        self.linkInfo = {}

    def addLinkInfo(self, h1, h2, bw):
        if h1 not in self.linkInfo:
            self.linkInfo[h1] = {}
        self.linkInfo[h1][h2] = int(bw)

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
                self.addLinkInfo(h1,h2,bw)
                self.addLinkInfo(h2,h1,bw)
                self.addLink(h1, h2)

    
    # You can write other functions as you need.

    # Add hosts
    # > self.addHost('h%d' % [HOST NUMBER])

    # Add switches
    # > sconfig = {'dpid': "%016x" % [SWITCH NUMBER]}
    # > self.addSwitch('s%d' % [SWITCH NUMBER], **sconfig)

    # Add links
    # > self.addLink([HOST1], [HOST2])

def createQosQueue(net, switch_interface, bw):

    # Values in unit Mbps
    bw = bw * 1000000
    W = 0.8 * bw 
    X = 0.6 * bw
    Y = 0.3 * bw
    Z = 0.2 * bw
    os.system('sudo ovs-vsctl -- set Port %s qos=@newqos \
               -- --id=@newqos create QoS type=linux-htb other-config:max-rate=%d queues=0=@q0,1=@q1,2=@q2 \
               -- --id=@q0 create queue other-config:max-rate=%d other-config:min-rate=%d \
               -- --id=@q1 create queue other-config:min-rate=%d \
               -- --id=@q2 create queue other-config:max-rate=%d' 
               % (switch_interface, bw, X, Y, W, Z))

def createQosQueues(net, linkInfo):
    for switch in net.switches:
        for intf in switch.intfList():
            if intf.link:
                info('**** Adding Queue for %s interface\n' % intf.link)
                n1 = intf.link.intf1.node
                n2 = intf.link.intf2.node
                target = n2 if n1 == switch else n1
                switch_interface = intf.link.intf1 if n1 == switch else intf.link.intf2
                bw = linkInfo[switch.name][target.name]
                switch_intrface_name = switch_interface.name
                createQosQueue(net, switch_intrface_name, bw)


def startNetwork():
    info('** Creating the tree network\n')
    topo = TreeTopo()
    topo.readFromFile("topology.in")

    global net
    net = Mininet(topo=topo, link = TCLink,
                  controller=lambda name: RemoteController(name, ip='172.17.194.79'),
                  listenPort=6633, autoSetMacs=True)

    info('** Starting the network\n')
    net.start()
    net.waitConnected()

    info('** Creating QoS Queues\n')
    createQosQueues(net, topo.linkInfo)

    # Create QoS Queues
    
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
