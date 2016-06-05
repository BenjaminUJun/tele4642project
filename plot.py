#!/usr/bin/python

# 4642 Mini-project
# Group 1
# Monitoring Netflix traffic with the Northbound Networks Zodiac FX switch
# Adeline Yeung

import os
import threading
import json
import datetime 
import time

data = None
clients = {}

def read_data():
   threading.Timer(5.0, read_data).start()
   with open('jsonout.json') as data_file:    
      global data
      data = json.load(data_file)

   get_stats()
   write_values()

def get_stats():
   global clients
   for flows in data['OFPFlowStatsReply']['body'][2:]:
      # print flows['OFPFlowStats']['byte_count']
      byte_count = flows['OFPFlowStats']['byte_count']

      # print flows['OFPFlowStats']['packet_count']
      packet_count = flows['OFPFlowStats']['packet_count']

      # print flows['OFPFlowStats']['duration_sec']
      duration = flows['OFPFlowStats']['duration_sec']

      for matchfields in flows['OFPFlowStats']['match']['OFPMatch']['oxm_fields'][1:2]:
         # print matchfields['OXMTlv']['value']
         mac_addr = matchfields['OXMTlv']['value']
         if mac_addr in clients:
            curr_packet_count = clients[mac_addr][0]
            curr_byte_count = clients[mac_addr][1]
            curr_duration = clients[mac_addr][2]

            if curr_packet_count != packet_count and curr_byte_count != byte_count:
               packet_count += curr_packet_count
               byte_count += curr_byte_count
            else:
               packet_count = curr_packet_count
               byte_count = curr_byte_count
               
            if duration > curr_duration:
               curr_duration = duration

            clients[mac_addr] = (packet_count, byte_count, curr_duration)
         else:
            clients[mac_addr] = (packet_count, byte_count, duration)

def write_values():
   global clients
   if not clients:
      print "There don't seem to be any clients accessing Netflix yet."
   else:
      os.system('clear')

      print "{:<20} | {:<15} | {:<15} | {:<15}".format('Client','Packets', 'Bytes', 'Duration (s)')
      print ("-" * 71)
      for client, data in clients.iteritems():
         totalpackets, totalbytes, duration = data
         print "{:<20} | {:<15} | {:<15} | {:<15}".format(client, totalpackets, totalbytes, duration)

read_data()