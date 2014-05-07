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
import pox.lib.packet.udp as pkt_udp
import pox.lib.packet.ipv4 as pkt_ip
import pox.lib.packet.ethernet as pkt_eth
from pox.lib.addresses import IPAddr
from pox.lib.revent import *
from oracleDB import OracleDB

log = core.getLogger()


class DNSUpdate (Event):
    def __init__ (self, item):
        Event.__init__()
        self.item = item
        
class DNSLookup (Event):
    def __init__ (self, rr):
        Event.__init__()
        self.name = rr.name
        self.qtype = rr.qtype
        self.rr = rr
        for t in pkt_dns.rrtype_to_str.values():
            setattr(self, t, False)
        t = pkt_dns.rrtype_to_str.get(rr.qtype)
        if t is not None:
            setattr(self, t, True)
            setattr(self, "OTHER", False)
        else:
            setattr(self, "OTHER", True)
                
class DNSOracle (EventMixin):
    _eventMixin_events = set([ DNSUpdate, DNSLookup ])
    
    def __init__ (self, install_flow = True):
        self._install_flow = install_flow
        self.ip_to_name = {}
        self.name_to_ip = {}
        self.cname = {}
        self.oracle = OracleDB()
        self.tcpFlowsMap = {}
        self.domain = "bogusdomain.com"
        # hardcoded sources to test functionality
        if not self.oracle.addSource("first", "10.0.0.2"):
            raise Exception("Failed to initialize oracle in dns_oracle.py")
        core.openflow.addListeners(self)
        # Add handy function to console
        core.Interactive.variables['lookup'] = self.lookup
            
    def _handle_ConnectionUp (self, event):
        if self._install_flow:
            msg = of.ofp_flow_mod()
            msg.match = of.ofp_match()
            msg.match.dl_type = pkt.ethernet.IP_TYPE
            msg.match.nw_proto = pkt.ipv4.UDP_PROTOCOL
            msg.match.tp_src = 53
            msg.actions.append(of.ofp_action_output(port = of.OFPP_CONTROLLER))
            event.connection.send(msg)
            
    def lookup (self, something):
        if something in self.name_to_ip:
            return self.name_to_ip[something]
        if something in self.cname:
            return self.lookup(self.cname[something])
        try:
            return self.ip_to_name.get(IPAddr(something))
        except:
            return None
                    
    def _record (self, ip, name):
        # Handle reverse lookups correctly?
        modified = False
        val = self.ip_to_name.setdefault(ip, [])
        if name not in val:
            val.insert(0, name)
            modified = True
        val = self.name_to_ip.setdefault(name, [])
        if ip not in val:
            val.insert(0, ip)
            modified = True
        return modified
                
    def _record_cname (self, name, cname):
        modified = False
        val = self.cname.setdefault(name, [])
        if name not in val:
            val.insert(0, cname)
            modified = True
        return modified

    def _handle_FlowRemoved(self, event):
        if event.idleTimeout and event.ofp.match.nw_proto is pkt_ip.TCP_PROTOCOL:
            source = event.ofp.match.nw_src
            dest = event.ofp.match.nw_dst
            if source is None or dest is None:
            	return
            elif (source,dest) in self.tcpFlowsMap.keys():
                # completed P2P flow, add new source
                content = self.tcpFlowsMap[(source,dest)]
                if self.oracle.addSource(content,dest.toStr()):
                    log.info("Added source " + dest.toStr() + " for content " + content)
                    log.info("Sources: " + str(self.oracle.listSources(content)))
                del self.tcpFlowsMap[(source, dest)]
            	
            
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

        # Check if it's a DNS packet
        p = event.parsed.find('dns')
        if p is not None and p.parsed:
            log.debug(p)                    
            for q in p.questions:
                if q.qclass != 1: continue # Internet only
                if p.qr == 0 and q.qtype == 1 and q.name.endswith(self.domain): # vod request
                    index = q.name.rfind(self.domain)
                    content = q.name[:index-1]
                    source = self.oracle.getSource(content)
                    # make sure we're not telling the requester to contact itself (just for the demo)
                    n = len(self.oracle.listSources(content))
                    ip_query = event.parsed.find('ipv4')
                    while n>1 and source == ip_query.srcip.toStr():
                    	source = self.oracle.getSource(content)
                    if source is not None:
                        # return the IP address of the source as DNS response
                        if len(p.answers) > 0:
                            raise Exception("DNS request for bogusdomain has answers")
                            p.answers = []
                        dns_res = pkt_dns()
                        dns_res.qr = 1 # response
                        dns_res.id = p.id
                        dns_res.questions.append(q)                         
                        # 0 is the TTL (no caching), 4 is the number of octets of the 
                        # response (single IP address)                        
                        a = pkt_dns.rr(q.name, q.qtype, q.qclass, 0, 4, IPAddr(source))
                        dns_res.answers.append(a)
                        udp_query = event.parsed.find('udp')
                        udp_res = pkt_udp()
                        udp_res.srcport = udp_query.dstport
                        udp_res.dstport = udp_query.srcport
                        # FIXME: how do I calculate the dns_res real length?
                        udp_res.len = pkt_udp.MIN_LEN + pkt_dns.MIN_LEN
                        udp_res.set_payload(dns_res)
                        ip_res = pkt_ip()
                        ip_res.iplen = pkt_ip.MIN_LEN + udp_res.len
                        ip_res.protocol = pkt_ip.UDP_PROTOCOL
                        ip_res.dstip = ip_query.srcip
                        ip_res.srcip = ip_query.dstip
                        ip_res.set_payload(udp_res)
                        eth_res = pkt_eth()
                        eth_res.type = pkt_eth.IP_TYPE
                        eth_query = event.parsed.find('ethernet')
                        eth_res.src = eth_query.dst
                        eth_res.dst = eth_query.src
                        eth_res.set_payload(ip_res)                        
                        msg = of.ofp_packet_out(data = eth_res.pack())
                        msg.actions.append(of.ofp_action_output(port = event.port))
                        event.connection.send(msg)
                        log.info ("DNS response with source %s for content %s sent" % (source, content))
                        # record the flow - content association to monitor it
                        # FIXME: we should record the pair IP:PORT for source and dest, but there's no way of knowing it
                        self.tcpFlowsMap[(IPAddr(source), ip_res.dstip)] = content
                        # tell the OF switch to drop the dns request - NOT REQUIRED
                        # (Would return a buffer_empty error)
                        # drop()
                        # FIXME: I'm assuming there's no other question ( I know there's
                        # no answer as I checked above)
                        return
                    else:
                        # no source has been found - send request to nameserver    
                        self.raiseEvent(DNSLookup, q)
                else: # non VoD request
                    self.raiseEvent(DNSLookup, q)
                        
            def process_q (entry):
                if entry.qclass != 1:
                    # Not internet
                    return
                if entry.qtype == pkt.dns.rr.CNAME_TYPE:
                    if self._record_cname(entry.name, entry.rddata):
                        self.raiseEvent(DNSUpdate, entry.name)
                        log.info("add cname entry: %s %s" % (entry.rddata, entry.name))
                elif entry.qtype == pkt.dns.rr.A_TYPE:
                    if self._record(entry.rddata, entry.name):
                        self.raiseEvent(DNSUpdate, entry.name)
                        log.info("add dns entry: %s %s" % (entry.rddata, entry.name))
                            
            for answer in p.answers:
                process_q(answer)
            for addition in p.additional:
                process_q(addition)
                
def launch (no_flow = False):
    core.registerNew(DNSOracle, not no_flow)
