#!/usr/bin/python
#
# weewx driver that reads data from MQTT subscription
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.
#
# See http://www.gnu.org/licenses/

#
# The units must be weewx.US:
#   degree_F, inHg, inch, inch_per_hour, mile_per_hour
#
# To use this driver, put this file in the weewx user directory, then make
# the following changes to weewx.conf:
#
# [Station]
#     station_type = wxMesh
# [wxMesh]
#     host = localhost           # MQTT broker hostname
#     topic = weather            # topic
#     driver = user.wxMesh
#
# If the variables in the file have names different from those in weewx, then
# create a mapping such as this:
#
# [wxMesh]
#     ...
#     [[label_map]]
#         temp = outTemp
#         humi = outHumidity
#         in_temp = inTemp
#         in_humid = inHumidity

from __future__ import with_statement
import syslog
import time
import paho.mqtt.client as mqtt
import weewx.drivers

DRIVER_VERSION = "0.1"

def logmsg(dst, msg):
    syslog.syslog(dst, 'wxMesh: %s' % msg)

def logdbg(msg):
    logmsg(syslog.LOG_DEBUG, msg)

def loginf(msg):
    logmsg(syslog.LOG_INFO, msg)

def logerr(msg):
    logmsg(syslog.LOG_ERR, msg)

def _get_as_float(d, s):
    v = None
    if s in d:
        try:
            v = float(d[s])
        except ValueError, e:
            logerr("cannot read value for '%s': %s" % (s, e))
    return v

def loader(config_dict, engine):
    return wxMesh(**config_dict['wxMesh'])

class wxMesh(weewx.drivers.AbstractDevice):
    """weewx driver that reads data from a file"""

    def __init__(self, **stn_dict):
        # where to find the data file
        self.host = stn_dict.get('host', 'localhost')
        self.topic = stn_dict.get('topic', 'weather')
        # how often to poll the weather data file, seconds
        self.poll_interval = float(stn_dict.get('poll_interval', 5.0))
        # mapping from variable names to weewx names
        self.label_map = stn_dict.get('label_map', {})

        loginf("host is %s" % self.host)
        loginf("topic is %s" % self.topic)
        loginf("polling interval is %s" % self.poll_interval)
        loginf('label map is %s' % self.label_map)
        
        self.payload = "Empty"
        #self.payloadList = [payload]
        self.client = mqtt.Client(client_id="XXX", protocol=mqtt.MQTTv31)

	#self.client.on_connect = self.on_connect
	self.client.on_message = self.on_message

        self.client.username_pw_set("XXX", "XXX")
	self.client.connect(self.host, 1883, 60)
	self.client.subscribe(self.topic, qos=1)

    # The callback for when a PUBLISH message is received from the server.
    def on_message(self, client, userdata, msg):
	self.payload = str(msg.payload)
	logdbg("Got message %s" % str(msg.payload))

    def genLoopPackets(self):	
        while True:
	    self.client.loop()
            # read whatever values we can get from the MQTT broker
            logdbg("Working on payload : %s" % self.payload)
	    if self.payload != "Empty" :
		data = {}
		row = self.payload.split(",");
		for datum in row:
		    (key,value)  = datum.split(":")
		    data[key] = value
                    if( key=="TIME" and data[key] == "0"):
                        data[key] = str(int(time.time()))
		    logdbg("key: "+key+" value: "+data[key])
	    
		# map the data into a weewx loop packet
		_packet = {'usUnits': weewx.METRIC}
		for vname in data:
		    _packet[self.label_map.get(vname, vname)] = _get_as_float(data, vname)

		yield _packet
	        self.payload = "Empty"
	    
	    logdbg("Sleeping for %d" % self.poll_interval)
            time.sleep(self.poll_interval)
        self.client.disconnect()
    @property
    def hardware_name(self):
        return "wxMesh"
