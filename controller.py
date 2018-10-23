'''
Please add your name:
Please add your matric number: 
'''

import sys
import os
from sets import Set

from pox.core import core

import pox.openflow.libopenflow_01 as of
import pox.openflow.discovery
import pox.openflow.spanning_tree

from pox.lib.revent import *
from pox.lib.util import dpid_to_str
from pox.lib.addresses import IPAddr, EthAddr

log = core.getLogger()

class Controller(EventMixin):
    def __init__(self):
        self.listenTo(core.openflow)
        core.openflow_discovery.addListeners(self)

        # 2D mac address to port mapping 
        self.macport = {}
        
    # You can write other functions as you need.

    '''
    For each incoming packet p
        1. update mac to port table 
        2. Is detination mac in mac to port table?
            2a. Yes -- blindly forward accordingly 
            2b. No -- flood
    '''
        
    def _handle_PacketIn (self, event):  

        packet = event.parsed
        src_mac = packet.src # packet's src mac
        dst_mac = packet.dst # packet's dst mac
        port = event.port # the port where the packet enters
        dpid = event.dpid # switch id  

        log.debug("Switch %s: Recv %s from port %s" % (dpid, packet, port))

        # Step 1
        if dpid not in self.macport: self.macport[dpid] = {}
        self.macport[dpid][src_mac] = port

    	# install entries to the route table
        def install_enqueue(event, packet, outport, q_id):
            pass

    	# Check the packet and decide how to route the packet
        def forward(message = None):

            # Step 2
            if dst_mac.is_multicast:
                flood("Switch %s: Multicast" % (dpid,))
                return

            if dst_mac not in self.macport[dpid]:

                # Step 2b
                flood("Switch %s: Port for %s unknown -- flooding" % (dpid, dst_mac,))
                return

            q_id = get_q_id()
            outport = self.macport[dpid][dst_mac]

            # Step 2a
            blind_forward(event, packet, outport)

            return

        def blind_forward(event, packet, outport):
            log.debug("Switch %s: Blindly forwarding %s:%i - > %s:%i", dpid, src_mac, port, dst_mac, outport)
            msg = of.ofp_flow_mod();
            msg.match = of.ofp_match.from_packet(packet, port)
            msg.actions.append(of.ofp_action_output(port = outport))
            msg.data = event.ofp
            event.connection.send(msg)
            log.debug("Switch %i: Blindly forwarded: Outport %i", dpid, outport)

        # get the queue it should go into
        def get_q_id():
            return 1
            

        # When it knows nothing about the destination, flood but don't install the rule
        def flood (message = None):
            log.debug(message)

            # Create packet out message
            msg = of.ofp_packet_out() 

            # Add an action to send to the all port
            msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))

            # Set the packet data same as the incoming one
            msg.data = event.ofp

            # Set the in_port so that the switch knows
            msg.in_port = event.port

            # Sends the packet out
            event.connection.send(msg)
            return
        
        # begin
        forward()


    def _handle_ConnectionUp(self, event):
        dpid = dpid_to_str(event.dpid)
        log.debug("Switch %s has come up.", dpid)
        
        # Send the firewall policies to the switch
        def sendFirewallPolicy(connection, policy):
            pass

        # for i in [FIREWALL POLICIES]:
        #     sendFirewallPolicy(event.connection, i)
            

def launch():
    # Run discovery and spanning tree modules
    pox.openflow.discovery.launch()
    pox.openflow.spanning_tree.launch()

    # Starting the controller module
    core.registerNew(Controller)
