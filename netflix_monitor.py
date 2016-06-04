from operator import attrgetter

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.lib import hub
import json

class SimpleMonitor(app_manager.RyuApp):

   def __init__(self, *args, **kwargs):
     super(SimpleMonitor, self).__init__(*args, **kwargs)
     self.datapaths = {}
     self.monitor_thread = hub.spawn(self._monitor)

   @set_ev_cls(ofp_event.EventOFPStateChange,
         [MAIN_DISPATCHER, DEAD_DISPATCHER])
   def _state_change_handler(self, ev):
     datapath = ev.datapath
     if ev.state == MAIN_DISPATCHER:
       if not datapath.id in self.datapaths:
         self.logger.debug('register datapath: %016x', datapath.id)
         self.datapaths[datapath.id] = datapath
     elif ev.state == DEAD_DISPATCHER:
       if datapath.id in self.datapaths:
         self.logger.debug('unregister datapath: %016x', datapath.id)
         del self.datapaths[datapath.id]

   def _monitor(self):
     while True:
       for dp in self.datapaths.values():
         self.send_flow_stats_request(dp)
       hub.sleep(5)

   @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
   def flow_stats_reply_handler(self, ev):
      body = ev.msg.body

      # self.logger.info('datapath      '
      #              'eth-dst       '
      #              'packets  bytes')
      # self.logger.info('------------- '
      #              '-------------- '
      #              '-------- --------')
      for stat in sorted([flow for flow in body if flow.priority == 100]):
         flowdata = json.dumps(ev.msg.to_jsondict(), ensure_ascii=True, indent=3, sort_keys=True)
         self.logger.info('%s', flowdata)
         print flowdata
         f = open("/Users/Addie/Dropbox/Uni work/TELE4642/4642project/jsonout.txt", "w")
         f.write(flowdata);
         f.close()

   def send_flow_stats_request(self, datapath):
     ofp = datapath.ofproto
     ofp_parser = datapath.ofproto_parser

     cookie = cookie_mask= 1
     match = ofp_parser.OFPMatch(in_port=1)
     req = ofp_parser.OFPFlowStatsRequest(datapath, 0,
                         ofp.OFPTT_ALL,
                         ofp.OFPP_ANY, ofp.OFPG_ANY,
                         cookie, cookie_mask,
                         match)
     # self.logger.info("Sending request for stats")
     datapath.send_msg(req)