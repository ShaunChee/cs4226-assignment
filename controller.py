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

TTL = 30
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

        def host_ip_to_mac(hostip):
            '''
            Its a hacky part which skips the learning of a host's MAC address
            '''
            hostid = int(str(hostip).split('.')[-1])
            hostmac = EthAddr("%012x" % (hostid & 0xffFFffFFffFF,))
            return hostmac

        # Update Mac to Port table mapping
        def learn_table():
            '''
            If the switch don't have a MAC to PORT table, create one
            If the source MAC does not have a mapping in MAC to PORT table, create one.
            '''
            if dpid not in self.macport: 
                self.macport[dpid] = {}
                self.macport_ttl[dpid] = {}

            if src_mac not in self.macport[dpid]:
                log.debug("** Switch %i: Learning... MAC: %s, Port: %s" % (dpid, src_mac, inport))
                self.macport[dpid][src_mac] = inport
                self.macport_ttl[dpid][src_mac] = datetime.datetime.now()

        def unlear_table():
            '''
            If the destination MAC to PORT entry has expired 
            then remove it.
            '''
            if dst_mac in self.macport_ttl[dpid] and self.macport_ttl[dpid][dst_mac] + datetime.timedelta(seconds=TTL) <= datetime.datetime.now():
                log.debug("** Switch %i: Timeout!... Unlearn MAC: %s, Port: %s" % (dpid, dst_mac, self.macport[dpid][dst_mac]))
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
            log.debug("** Switch %i: Rule sent: Outport %i, Queue %i", dpid, outport, q_id)
            return

    	# Check the packet and decide how to route the packet
        def forward(message = None):
            '''
            If it is meant to be broadcasted
                then broadcast it
            else if we don't know which specific port to send to
                then broadcast it also
            else 
                install enqueue flow entry 
            '''

            if dst_mac.is_multicast: return flood("** Switch %s: Multicast -- %s" % (dpid, packet))
            if dst_mac not in self.macport[dpid]: return flood("** Switch %s: Port for %s unknown -- flooding" % (dpid, dst_mac,))

            q_id = get_q_id(str(src_ip), str(dst_ip))
            outport = self.macport[dpid][dst_mac]
            install_enqueue(event, packet, outport, q_id)

            return

        # get the queue it should go into
        def get_q_id(src_ip, dst_ip):
            '''
            Get the Queue ID of the 2 IP and 
            returns the Queue ID of the higher class
            '''
            src_q_id = get_ip_q_id(src_ip)
            dst_q_id = get_ip_q_id(dst_ip)
            if src_q_id == PREMIUM or dst_q_id == PREMIUM: return PREMIUM
            elif src_q_id == REGULAR or dst_q_id == REGULAR: return REGULAR
            else: return FREE

            
        def get_ip_q_id(ip):
            '''
            Get Queue ID of desired IP address
            If there's no record, its in the FREE class 
            Otherwise return recorded value
            '''
            if ip is None: return REGULAR
            elif ip not in self.service_class: return FREE
            else: return self.service_class[ip]

        # When it knows nothing about the destination, flood but don't install the rule
        def flood (message = None):
            '''
            Extracted from l2 learning switch sample code
            Basically send the packet to all the ports except the incoming one.
            '''
            log.debug(message)

            # Create packet out message
            msg = of.ofp_packet_out() 

            # Set the packet data same as the incoming one
            msg.data = event.ofp

            # Set the in_port so that the switch knows
            msg.in_port = inport

            # Add an action to send to the all port
            msg.actions.append(of.ofp_action_output(port = of.OFPP_ALL))

            # Sends the packet out
            event.connection.send(msg)

            log.debug("Switch %s: Flood packet, DstIP: %s" % (dpid, dst_ip))
            return
        

        '''
        1) Extract information from the packet... namely:
            packet: the actual packet
            src_mac: source's MAC address
            dst_mac: destination's MAC address
            inport: the port which the packet came in from
            dpid: switch
            src_ip: source's IP address
            dst_ip: destination's IP address

        2) If this is an ARP request packet(i.e. we have to flood it), but we know the 
        MAC address of the destination, send to the port targeting the MAC address 
        instead of flooding to prevent infinite loops
        '''
        packet = event.parsed
        src_mac = packet.src
        dst_mac = packet.dst
        inport = event.port
        dpid = event.dpid 

        src_ip = None
        dst_ip = None
        if packet.type == packet.IP_TYPE:
            src_ip = packet.payload.srcip
            dst_ip = packet.payload.dstip
        elif packet.type == packet.ARP_TYPE:
            src_ip = packet.payload.protosrc
            dst_ip = packet.payload.protodst
            if dst_mac.is_multicast:
                dst_mac = host_ip_to_mac(dst_ip)

        # Step 1
        learn_table();
        forward()
        unlear_table()


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
