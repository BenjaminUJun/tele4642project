#!/usr/bin/python

import plotly.plotly as py  
import plotly.tools as tls   
import plotly.graph_objs as go
import threading
import json
import datetime 
import time

data = None
clients = {}

def read_data():
   threading.Timer(10.0, read_data).start()
   with open('jsonout.json') as data_file:    
      global data
      data = json.load(data_file)

   get_stats()

def get_stats():
   global clients
   global stream_links
   for flows in data['OFPFlowStatsReply']['body'][2:]:
      # print flows['OFPFlowStats']['byte_count']
      byte_count = flows['OFPFlowStats']['byte_count']

      # print flows['OFPFlowStats']['packet_count']
      packet_count = flows['OFPFlowStats']['packet_count']

      for matchfields in flows['OFPFlowStats']['match']['OFPMatch']['oxm_fields'][1:2]:
         # print matchfields['OXMTlv']['value']
         mac_addr = matchfields['OXMTlv']['value']
         if mac_addr in clients:
            print "mac addr %s in clients" % mac_addr
            curr_packet_count = clients[mac_addr][0]
            curr_byte_count = clients[mac_addr][1]

            packet_count += curr_packet_count
            byte_count + curr_byte_count

            clients[mac_addr] = (packet_count, byte_count)
         else:
            print "mac addr %s not in clients" % mac_addr
            clients[mac_addr] = (packet_count, byte_count)
            est_stream(mac_addr)
            

def est_stream(client):
   global streams
   global stream_links
   i = len(streams) + 1

   # Get stream id from stream id list 
   stream_id = stream_ids[i]

   # Make instance of stream id object 
   stream = dict(token=stream_id, maxpoints=10)

   streams[client] = stream

   trace = go.Scatter(x=[], y=[], mode='lines+markers', stream=stream)
   data = go.Data([trace])

   # Add title to layout object
   layout = go.Layout(
      title='Netflix usage for client %s' % client,
      xaxis=dict(
        title='Time',
        titlefont=dict(
            family='Courier New, monospace',
            size=18,
            color='#000000'
         )
      ),
       yaxis=dict(
         title='Bytes',
         titlefont=dict(
            family='Courier New, monospace',
            size=18,
            color='#000000'
         )
      )
   )

   # Make a figure object
   fig = go.Figure(data=data, layout=layout)

   # Send fig to Plotly, initialize streaming plot, open new tab
   py.plot(fig, filename='plot %d' % i)

   # We will provide the stream link object the same token that's associated with the trace we wish to stream to
   s = py.Stream(stream_id)

   # We then open a connection
   s.open()

   stream_links[client] = s

stream_ids = tls.get_credentials_file()['stream_ids']
read_data()