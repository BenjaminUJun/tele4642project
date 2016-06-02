from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import arp, ipv4
import array
import ipaddress
import ast

iplist = []

# parse the list of Netflix IPs and put them into the list
def getIPs():
   with open("/Users/Addie/Dropbox/Uni work/TELE4642/4642project/iplist.txt", "r") as input:
      for line in input:
         # line = line.strip()
         # iplist.append(tuple(line.split(',')))
         iplist.append(line.strip())

# checks if IP is in the Netlix AS range
def checkIfNetflix(checkIP):
   for ip in iplist:
      if ipaddress.ip_address(checkIP.decode("utf-8")) in ipaddress.ip_network(ip.decode("utf-8")):
         return True
   return False

class SimpleSwitch13(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        getIPs()
        self.mac_to_port = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install table-miss flow entry
        #
        # We specify NO BUFFER to max_len of the output action due to
        # OVS bug. At this moment, if we specify a lesser number, e.g.,
        # 128, OVS will send Packet-In with invalid buffer_id and
        # truncated packet data. In that case, we cannot output packets
        # correctly.  The bug has been fixed in OVS v2.1.0.

        # match = parser.OFPMatch()
        # actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
        #                                   ofproto.OFPCML_NO_BUFFER)]

        match = parser.OFPMatch(in_port = 1)
        actions = [parser.OFPActionOutput(2), ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER]
        self.add_flow(datapath, 1, match, actions)

        match = parser.OFPMatch(in_port = 2)
        actions = [parser.OFPActionOutput(1), ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER]
        self.add_flow(datapath, 1, match, actions)

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id,
                                    priority=priority, match=match,
                                    instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        datapath.send_msg(mod)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        actions = []
        match = []

        # If you hit this you might want to increase
        # the "miss_send_length" of your switch
        if ev.msg.msg_len < ev.msg.total_len:
            self.logger.debug("packet truncated: only %s of %s bytes",
                              ev.msg.msg_len, ev.msg.total_len)
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(array.array('B', ev.msg.data))
        eth_pkt = pkt.get_protocol(ethernet.ethernet)

        if eth_pkt.ethertype == ether_types.ETH_TYPE_LLDP:
            # ignore lldp packet
            return

        ip4_pkt = pkt.get_protocol(ipv4.ipv4)
        if ip4_pkt:
            pak = ip4_pkt
            self.logger.info('  _packet_in_handler: src_mac -> %s' % pak.src)
            self.logger.info('  _packet_in_handler: dst_mac -> %s' % pak.dst)
            self.logger.info('  _packet_in_handler: %s' % pak)
            self.logger.info('  ------')
        else:
            pak = eth_pkt

        dst = eth_pkt.dst
        src = eth_pkt.src

        dpid = datapath.id
        self.mac_to_port.setdefault(dpid, {})

        # self.logger.info("packet in %s %s %s %s", dpid, src, dst, in_port)

        # learn a mac address to avoid FLOOD next time.
        self.mac_to_port[dpid][src] = in_port

        if dst in self.mac_to_port[dpid]:
            out_port = self.mac_to_port[dpid][dst]
        else:
            out_port = ofproto.OFPP_FLOOD

        if ip4_pkt and in_port == 1:
            self.logger.info("Entering loop to check IP packet for Netflix -> %s" % ip4_pkt.src)
            if checkIfNetflix(ip4_pkt.src):
               self.logger.info("Matched Netlix -> %s" % ip4_pkt.src)
               match = parser.OFPMatch(in_port=in_port, eth_dst=dst, ipv4_src=ip4_pkt.src)
               actions = [parser.OFPActionOutput(out_port)]
               self.add_flow(datapath, 100, match, actions)
               self.logger.info("Flow for Netflix added!")
               return
        else: 
            actions = [parser.OFPActionOutput(out_port)]

            # loop through netflix IP list
                # if ip4.src is in ipaddress subnet range
                    # actions = [parser.OFPActionOutput(out_port)] - this needs some kind of check to ensure that out port is never OFPP_FLOOD
                # else 
                    # actions = [parser.OFPActionOutput(out_port), parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]

        # install a flow to avoid packet_in next time
        if out_port != ofproto.OFPP_FLOOD:
            match = parser.OFPMatch(in_port=in_port, eth_dst=dst)
            # verify if we have a valid buffer_id, if yes avoid to send both
            # flow_mod & packet_out
            if msg.buffer_id != ofproto.OFP_NO_BUFFER:
                self.add_flow(datapath, 1, match, actions, msg.buffer_id)
                return
            else:
                self.add_flow(datapath, 1, match, actions)
        data = None
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = parser.OFPPacketOut(datapath=datapath, buffer_id=msg.buffer_id,
                                  in_port=in_port, actions=actions, data=data)
        datapath.send_msg(out)
