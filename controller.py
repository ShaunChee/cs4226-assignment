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

import datetime

log = core.getLogger()

TTL = 5
IDLE_TTL = TTL
HARD_TTL = TTL

REGULAR = 0
PREMIUM = 1
FREE = 2

FIREWALL_PRIORITY = 200
QOS_PRIORITY = 100

class Controller(EventMixin):
    def __init__(self):
        self.listenTo(core.openflow)
        core.openflow_discovery.addListeners(self)

        # 2D mac address to port mapping 
        self.macport = {}
        self.macport_ttl = {}

        # Maps hosts to their service class
        self.service_class = {}
        
    def _handle_PacketIn (self, event):  

        packet = event.parsed
        src_mac = packet.src # packet's src mac
        dst_mac = packet.dst # packet's dst mac
        inport = event.port # the port where the packet enters
        dpid = event.dpid # switch id  

        srcIP = None
        dstIP = None
        if packet.type == packet.IP_TYPE:
            srcIP = packet.payload.srcip
            dstIP = packet.payload.dstip
        elif packet.type == packet.ARP_TYPE:
            srcIP = packet.payload.protosrc
            dstIP = packet.payload.protodst

        # log.debug("** Switch %s: Recv %s from port %s" % (dpid, packet, inport))

        # Update Mac to Port table mapping
        def update_table():
            if dpid not in self.macport: 
                self.macport[dpid] = {}
                self.macport_ttl[dpid] = {}

            self.macport[dpid][src_mac] = inport
            self.macport_ttl[dpid][src_mac] = datetime.datetime.now()

            if dst_mac in self.macport_ttl[dpid] and self.macport_ttl[dpid][dst_mac] + datetime.timedelta(seconds=TTL) <= datetime.datetime.now():
                log.debug("** Switch %i: Timeout!" % dpid)
                self.macport[dpid].pop(dst_mac)
                self.macport_ttl[dpid].pop(dst_mac)

    	# install entries to the route table
        def install_enqueue(event, packet, outport, q_id):
            log.debug("** Switch %i: Installing flow %s.%i -> %s.%i", dpid, src_mac, inport, dst_mac, outport)
            msg = of.ofp_flow_mod()
            msg.match = of.ofp_match.from_packet(packet, inport)
            msg.priority = QOS_PRIORITY
            msg.actions.append(of.ofp_action_enqueue(port = outport, queue_id = q_id))
            msg.data = event.ofp
            msg.idle_timeout = IDLE_TTL 
            msg.hard_timeout = HARD_TTL
            event.connection.send(msg)
            log.debug("** Switch %i: Rule sent: Outport %i, Queue %i\n", dpid, outport, q_id)
            return

    	# Check the packet and decide how to route the packet
        def forward(message = None):

            # Step 1
            update_table();

            # Step 2
            if dst_mac.is_multicast:
                flood("** Switch %s: Multicast -- %s" % (dpid, packet))
                return

            # Step 2a1 and 2b  
            if dst_mac not in self.macport[dpid]:
                flood("** Switch %s: Port for %s unknown -- flooding" % (dpid, dst_mac,))
                return

            q_id = get_q_id(str(srcIP), str(dstIP))
            outport = self.macport[dpid][dst_mac]

            # Step 2a2
            install_enqueue(event, packet, outport, q_id)

            return

        # get the queue it should go into
        def get_q_id(srcIP, dstIP):
            src_q_id = get_ip_q_id(srcIP)
            dst_q_id = get_ip_q_id(dstIP)
            if src_q_id == PREMIUM or dst_q_id == PREMIUM:
                return PREMIUM
            elif src_q_id == REGULAR or dst_q_id == REGULAR:
                return REGULAR
            else:
                return FREE

            
        def get_ip_q_id(ip):
            if ip is None:
                return REGULAR
            elif ip not in self.service_class: return FREE
            else: return self.service_class[ip]

        # When it knows nothing about the destination, flood but don't install the rule
        def flood (message = None):
            log.debug(message)

            # Create packet out message
            msg = of.ofp_packet_out() 

            # Set the packet data same as the incoming one
            msg.data = event.ofp

            # Set the in_port so that the switch knows
            msg.in_port = inport

            # Add an action to send to the all port
            msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))

            # Sends the packet out
            event.connection.send(msg)

            log.debug("Switch %s: Flood packet, DstIP: %s" % (dpid, dstIP))
            return
        
        # begin
        forward()


    def _handle_ConnectionUp(self, event):
        dpid = dpid_to_str(event.dpid)
        log.debug("Switch %s has come up.", dpid)

        def readPoliciesFromFile(file):
            fw_policies = []

            with open(file) as fd:
                N, M = fd.readline().split()
                for i in range(int(N)):
                    params = [x.strip() for x in fd.readline().split(",")]
                    if len(params) == 1:
                        fw_policies.append((params[0], None, None))
                    elif len(params) == 2:
                        fw_policies.append((None, params[0], params[1]))
                    else:
                        fw_policies.append(params)

                for i in range(int(M)):
                    ip, service_class_value = [x.strip() for x in fd.readline().split(",")]
                    log.debug("** Switch %s: Saving Service Class Rule Src %s, Class: %s" % (dpid, ip, service_class_value))
                    self.service_class[ip] = int(service_class_value)
                    print(self.service_class)
                    log.debug("** Switch %s: Saved Service Class Rule Src %s, Class: %s" % (dpid, ip, service_class_value))

            return fw_policies
        
        # Send the firewall policies to the switch
        def sendFirewallPolicy(connection, policy):
            from_IP, to_IP, to_port = policy
            log.debug("** Switch %s: Adding Firewall Rule Src: %s, Dst: %s:%s" % (dpid, from_IP, to_IP, to_port))
            
            msg = of.ofp_flow_mod()

            msg.priority = FIREWALL_PRIORITY

            # Set flow to send to no where
            msg.actions.append(of.ofp_action_output(port = of.OFPP_NONE))

            # ethernet type should be ipv4 (0x800)
            msg.match.dl_type = 0x800

            # IP header protocol number should be TCP (6)
            #   ICMP - 1, UDP - 17
            msg.match.nw_proto = 6

            # Source IP Address
            if from_IP: msg.match.nw_src = IPAddr(from_IP)
            if to_IP: 
                # Destination IP Address:Port Number
                msg.match.nw_dst = IPAddr(to_IP)
                msg.match.tp_dst = int(to_port)

            connection.send(msg)
            log.debug("** Switch %s: Firewall Rule added!" % (dpid, ))


        fw_policies = readPoliciesFromFile("./pox/misc/policy.in")
        for fw_policy in fw_policies:
            sendFirewallPolicy(event.connection, fw_policy)
            

def launch():
    # Run discovery and spanning tree modules
    pox.openflow.discovery.launch()
    pox.openflow.spanning_tree.launch()

    # Starting the controller module
    core.registerNew(Controller)
