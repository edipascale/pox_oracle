# Copyright 2011-2014 James McCauley, Emanuele Di Pascale
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at:
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
This is a modified version of the dns_spy component that ships with Floodlight.
The purpose is to intercept dns request, and if they match a certain pattern
(used to identify content rather than a host) return an answer based on 
locality informations. The oracle itself is kept as a separate module.
"""

from pox.core import core
import pox.openflow.libopenflow_01 as of
import pox.lib.packet as pkt
import pox.lib.packet.dns as pkt_dns
import pox.lib.packet.tcp as pkt_tcp
import pox.lib.packet.ipv4 as pkt_ip
import pox.lib.packet.ethernet as pkt_eth
from pox.lib.addresses import IPAddr
from pox.lib.revent import *
from oracleDB import OracleDB
import struct
import datetime

log = core.getLogger()


                
class TCPOracle (EventMixin):
    _eventMixin_events = set([])
    
    def __init__ (self, install_flow = True):
        self._install_flow = install_flow
        self.oracle = OracleDB()
        self.tcpFlowsMap = {}
        self.domain = "bogusdomain.com"
        self.vodIP = "10.0.0.3"
        # hardcoded sources to test functionality
        if not self.oracle.addSource("first.txt", "10.0.0.2:9002"):
            raise Exception("Failed to initialize oracle in tcp_oracle.py")
        core.openflow.addListeners(self)
        self.monthname = [None,
                 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
           
    def _handle_ConnectionUp (self, event):
        if self._install_flow:
            msg = of.ofp_flow_mod()
            msg.match = of.ofp_match()
            msg.match.dl_type = pkt.ethernet.IP_TYPE
            msg.match.nw_proto = pkt.ipv4.TCP_PROTOCOL
            msg.match.nw_dstip = IPAddr(self.vodIP)
            msg.actions.append(of.ofp_action_output(port = of.OFPP_CONTROLLER))
            event.connection.send(msg)
            
    def _handle_FlowRemoved(self, event):
        log.debug("FlowRemoved event")
        if event.idleTimeout and event.ofp.match.nw_proto is pkt_ip.TCP_PROTOCOL:
            sourceIP = event.ofp.match.nw_src
            if sourceIP is None:
            	return
            sourcePort = str(event.ofp.match.tp_src)
            source = sourceIP.toStr() + ':' + sourcePort
            destIP = event.ofp.match.nw_dst
            if destIP is None:
            	return
            #destPort = str(event.ofp.match.tp_dst)
            dest = destIP.toStr() # + ':' + destPort 
            log.debug("TCP flow expired for %s, %s", source, dest)
            if (source,dest) in self.tcpFlowsMap.keys():
                # completed P2P flow, add new source
                content = self.tcpFlowsMap[(source,dest)]
                if self.oracle.addSource(content,dest):
                    log.info("Added source " + dest + " for content " + content)
                    log.info("Sources: " + str(self.oracle.listSources(content)))
                del self.tcpFlowsMap[(source, dest)]

    def getTimeStamp(self):
        now = datetime.datetime.now()
        tt = now.timetuple()
        ms = now.microsecond / 1000
        s = "[%02d/%3s/%04d %02d:%02d:%02d:%04d]" % (
                tt[2], self.monthname[tt[1]], tt[0], tt[3], tt[4], tt[5], ms)
        return s            	
            
    def _handle_PacketIn (self, event):
        def drop (duration = None):
            """
            Drops this packet and optionally installs a flow to continue
            dropping similar ones for a while
            """
            if duration is not None:
                if not isinstance(duration, tuple):
                    duration = (duration,duration)
                msg = of.ofp_flow_mod()
                msg.match = of.ofp_match.from_packet(p)
                msg.idle_timeout = duration[0]
                msg.hard_timeout = duration[1]
                msg.buffer_id = event.ofp.buffer_id
                event.connection.send(msg)
            elif event.ofp.buffer_id is not None:
                msg = of.ofp_packet_out()
                msg.buffer_id = event.ofp.buffer_id
                msg.in_port = event.port
                event.connection.send(msg)
            log.info("Dropped packet.")

        # Check if it's a TCP VoD request
        tcp = event.parsed.find('tcp')
        if tcp is not None and tcp.parsed:
            ip = event.parsed.find('ipv4')
            if ip.dstip == self.vodIP: # http vod request
                http = tcp.payload
                index = http.find('GET') 
                if index is not -1:
                    delim = http.find('HTTP/1')
                    content = http[index+4:delim-1].strip()
                    log.info(self.getTimeStamp() + "Request for content " + content)
                    source = self.oracle.getSource(content)
                    # make sure we're not telling the requester to contact itself (just for the demo)
                    n = len(self.oracle.listSources(content))
                    while n>1 and source.split(':')[0] == ip.srcip.toStr():
                    	source = self.oracle.getSource(content)
                    if source is not None:
                        # return the IP address of the source as an HTTP Redirect
                        response = "HTTP/1.1 307 Temporary Redirect\nLocation: " + source +'\n\n'
                        tcp_res = pkt_tcp()
                        tcp_res.srcport = tcp.dstport
                        tcp_res.dstport = tcp.srcport
                        tcp_res.ACK = True
                        # tcp_res.FIN = True
                        tcp_res.win = 14000
                        tcp_res.seq = tcp.ack
                        tcp_res.ack = tcp.seq + tcp.payload_len
                        tcp_res.off = 5 # is that right?
                        tcp_res.set_payload(response)
                        tcp_res.len = pkt_tcp.MIN_LEN + len(response)
                        ip_res = pkt_ip()
                        ip_res.iplen = pkt_ip.MIN_LEN + tcp_res.len
                        ip_res.protocol = pkt_ip.TCP_PROTOCOL
                        ip_res.dstip = ip.srcip
                        ip_res.srcip = ip.dstip
                        ip_res.set_payload(tcp_res)
                        eth_res = pkt_eth()
                        eth_res.type = pkt_eth.IP_TYPE
                        eth = event.parsed.find('ethernet')
                        eth_res.src = eth.dst
                        eth_res.dst = eth.src
                        eth_res.set_payload(ip_res)                        
                        msg = of.ofp_packet_out(data = eth_res.pack())
                        msg.actions.append(of.ofp_action_output(port = event.port))
                        event.connection.send(msg)
                        log.info (self.getTimeStamp() + "HTTP 307 response with source %s for content %s sent" % (source, content))
                        # record the flow - content association to monitor it
                        # note: destination port will change after the redirect, cannot save it
                        dest = ip_res.dstip.toStr() # +':'+str(tcp_res.dstport)
                        self.tcpFlowsMap[source, dest] = content
                        log.info('%s - %s pair saved for content %s', source, dest, content)
                        # attempt to stop other modules from forwarding the packet
                        event.halt = True
                        return
                    else:
                        log.info(self.getTimeStamp() + "No source found, we won't redirect")
                        return
                else: # not an HTTP GET
                    log.info(self.getTimeStamp() + "VoD TCP flow match but not a GET request")
                    return                        
                
def launch (no_flow = False):
    core.registerNew(TCPOracle, not no_flow)
