import requests
import re
import json

devices = requests.get('http://localhost:8080/stats/switches')
deviceList = re.findall("([\d]+)", devices.text)

iplist = []


# parse the list of Netflix IPs and put them into the list
def getIPs():
   with open("iplist.txt", "r") as input:
    for line in input:
        iplist.append(line.strip())

getIPs()

for device in deviceList:
   print device

   initFlow1 = "{ \"dpid\": %s, \"table_id\": 0, \"idle_timeout\": 0, \"hard_timeout\": 0, \"priority\": 1, \"flags\": 1, \"match\":{ \"in_port\":2 }, \"actions\":[ { \"type\":\"OUTPUT\", \"port\": 1 } ] }" % device
   initFlow2 = "{ \"dpid\": %s, \"table_id\": 0, \"idle_timeout\": 0, \"hard_timeout\": 0, \"priority\": 1, \"flags\": 1, \"match\":{ \"in_port\":1 }, \"actions\":[ { \"type\":\"OUTPUT\", \"port\": 2 } ] }" % device

   response = requests.post('http://localhost:8080/stats/flowentry/add', data=initFlow1)
   response = requests.post('http://localhost:8080/stats/flowentry/add', data=initFlow2) 

   for ip in iplist:
      netflixFlow = "{\"dpid\": %s, \"table_id\": 0, \"idle_timeout\": 0, \"hard_timeout\": 0, \"priority\": 2, \"flags\": 1, \"match\":{ \"in_port\":1, \"nw_src\": \"%s\",  \"dl_type\": 2048 }, \"actions\":[ \"type\":\"OUTPUT\", \"port\": 2 ]}" % (device, ip)
      response = requests.post('http://localhost:8080/stats/flowentry/add', data=netflixFlow)