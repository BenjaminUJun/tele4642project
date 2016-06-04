# 4642 Mini-project
# Group 1
# Monitoring Netflix traffic with the Northbound Networks Zodiac FX switch
# Adeline Yeung

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

# list of Netflix IP ranges
iplist = []

# set of Netflix IPs that we've already seen
# to prevent duplicate flows
ips_seen = set()

# parse the list of Netflix IPs and put them into the list
def getIPs():
   with open("/Users/Addie/Dropbox/Uni work/TELE4642/4642project/iplist.txt", "r") as input:
      for line in input:
         iplist.append(line.strip())

# checks if IP is in the Netlix AS range
def checkIfNetflix(checkIP):
   for ip in iplist:
      if ipaddress.ip_address(checkIP.decode("utf-8")) in ipaddress.ip_network(ip.decode("utf-8")):
         return True
   return False

# Initialise simple switch with packet_in handler to check if incoming packet is from Netflix
class SimpleSwitch13(app_manager.RyuApp):
    # keep this from simple_switch_13, the Zodiac supports it
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    # initialise simple switch and populat ip list with Netflix ranges
    def __init__(self, *args, **kwargs):
        super(SimpleSwitch13, self).__init__(*args, **kwargs)
        getIPs()

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        match = parser.OFPMatch(in_port = 1)
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER), parser.OFPActionOutput(2)]
        self.add_flow(datapath, 1, match, actions)

        match = parser.OFPMatch(in_port = 2)
        actions = [parser.OFPActionOutput(1)]
        self.add_flow(datapath, 1, match, actions) 

    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
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
        dst = eth_pkt.dst
        src = eth_pkt.src

        if ip4_pkt:
            self.logger.info('  ------')
            self.logger.info('  _packet_in_handler: source -> %s' % ip4_pkt.src)
            self.logger.info('  _packet_in_handler: dest -> %s' % ip4_pkt.dst)
            self.logger.info('  _packet_in_handler: %s' % ip4_pkt)
            self.logger.info("Entering loop to check IP packet for Netflix")
            if checkIfNetflix(ip4_pkt.src) and ip4_pkt.src not in ips_seen:
               self.logger.info("Matched Netlix -> %s" % ip4_pkt.src)
               ips_seen.add(ip4_pkt.src)
               match = parser.OFPMatch(in_port=in_port, eth_dst=dst, ipv4_src=ip4_pkt.src)
               actions = [parser.OFPActionOutput(2)]
               self.add_flow(datapath, 100, match, actions)
               self.logger.info("Flow for Netflix added!")
               return