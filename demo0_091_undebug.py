# -*- coding: utf-8 -*-
"""
Created on Mon May 14 11:47:06 2018

@author: salted_fish

Note:
    Open mongod server and tagsee first!
    
(This version has not been debugged and may well have bugs!
"print" is aimed at debugging ,and can be deleted.)
"""

from ws4py.client.threadedclient import WebSocketClient
import json
import urllib2
import math
from pymongo import MongoClient
count=0

client = MongoClient()
dbb = client['basic_info']
dbo = client['rfid_output']
stu_info = dbb['stu_info']
fixed_info=dbb['fixed_info']
stu_list=[]
fixed_list=[]

for post in stu_info.find():
    td={'epc':post['epc'],'1':0,'2':0,'3':0,'c1':0,'c2':0,'c3':0,'a1':0,'a2':0,'a3':0}
    stu_list.append(td)
for post in fixed_info.find():
    td={'epc':post['epc'],'1':0,'2':0,'3':0,'c1':0,'c2':0,'c3':0,'a1':0,'a2':0,'a3':0}
    fixed_list.append(td)


#check epc in stu_list
def stulistcheck(jsonepc):
    j=0
    for i in stu_list:
        if i['epc']==jsonepc:
            return j
        j+=1
    return -1

#check epc in fixed_list
def fixedlistcheck(jsonepc):
    j=0
    for i in fixed_list:
        if i['epc']==jsonepc:
            return j
        j+=1
    return -1

class DummyClient(WebSocketClient):
    def opened(self):
        url='http://localhost:9092/service/agent/192.168.1.27/start'
        res=urllib2.urlopen(url)
        page=res.read()
        print page
        

    def closed(self, code, reason=None):
        
        url='http://localhost:9092/service/agent/192.168.1.27/stop'
        res=urllib2.urlopen(url)
        page=res.read()
        print page
        print "Closed down", code, reason
        
        #gain rssi average
        for i in range(len(stu_list)):
            if stu_list[i]['c1']!=0:
                stu_list[i]['a1']=stu_list[i]['1']/stu_list[i]['c1']
            if stu_list[i]['c2']!=0:
                stu_list[i]['a2']=stu_list[i]['2']/stu_list[i]['c2']
            if stu_list[i]['c3']!=0:
                stu_list[i]['a3']=stu_list[i]['3']/stu_list[i]['c3']
        for i in range(len(fixed_list)):
            if fixed_list[i]['c1']!=0:
                fixed_list[i]['a1']=fixed_list[i]['1']/fixed_list[i]['c1']
            if fixed_list[i]['c2']!=0:
                fixed_list[i]['a2']=fixed_list[i]['2']/fixed_list[i]['c2']
            if fixed_list[i]['c3']!=0:
                fixed_list[i]['a3']=fixed_list[i]['3']/fixed_list[i]['c3']
        #print "average success!"
        
        #gain location by rssi:generate students' location
        loc=[]#will be inserted in stu_loc
        for key2 in range(len(fixed_list)):
            minn=999
            mink=0
            for key1 in range(len(stu_list)):
                te=(stu_list[key1]['a1']-fixed_list[key2]['a1'])*(stu_list[key1]['a1']-fixed_list[key2]['a1'])+(stu_list[key1]['a2']-fixed_list[key2]['a2'])*(stu_list[key1]['a2']-fixed_list[key2]['a2'])+(stu_list[key1]['a3']-fixed_list[key2]['a3'])*(stu_list[key1]['a3']-fixed_list[key2]['a3'])
                t=math.sqrt(te)

                if t<minn:
                    minn=t
                    mink=key1
            #print key2
            #print minn
            #print mink
            #print ' '
            ted={'fixed_epc':key2,'stu_epc':mink}
            loc.append(ted)
            
        #call names(can be run 1 time):generate an unattendence record
        unatdt=[]
        for i in range(len(stu_list)):
            if stu_list[i]['c1']==0 and stu_list[i]['c2']==0 and stu_list[i]['c3']==0:
                te={'epc':stu_list[i]['epc']}
                unatdt.append(te)
        
        #update rfid_output database
        unatd_rec=dbo['unatd_rec']
        stu_loc=dbo['stu_loc']
        unatd_rec.delete_many({})
        stu_loc.delete_many({})
        unatd_rec.insert_many(unatdt)
        stu_loc.insert_many(loc)
    

    def received_message(self, m):
        global count,stu_list,fixed_list
        strrr=str(m)
        jsonn=json.loads(strrr)
        #print jsonn
        #print jsonn["type"]
        if jsonn["type"]=="readings":
            #print "epc:"+str(jsonn["tags"][0]["epc"])+" rssi:"+str(jsonn["tags"][0]['rssi'])+' antenna:'+str(jsonn["tags"][0]['antenna'])
            i=stulistcheck(jsonn["tags"][0]['epc'])
            if i!=-1:
                t='c'+str(jsonn["tags"][0]['antenna'])
                stu_list[i][str(jsonn["tags"][0]['antenna'])]+=jsonn["tags"][0]['rssi']
                stu_list[i][t]+=1
                count+=1
            i=fixedlistcheck(jsonn["tags"][0]['epc'])
            if i!=-1:
                t='c'+str(jsonn["tags"][0]['antenna'])
                fixed_list[i][str(jsonn["tags"][0]['antenna'])]+=jsonn["tags"][0]['rssi']
                fixed_list[i][t]+=1
                count+=1
            print count
            if count==100:
                self.close(reason='Bye bye')


if __name__ == '__main__':
    try:
        ws = DummyClient('ws://localhost:9092/socket', protocols=['chat'])
        ws.connect()
        ws.run_forever()
    except KeyboardInterrupt:
        ws.close()