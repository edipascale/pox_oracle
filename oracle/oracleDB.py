# Copyright 2014 Emanuele Di Pascale
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
oracleDB maps contents to IP of peer-to-peer sources. It can be interrogated
by other modules (e.g. the dns_oracle) to retrieve potential sources. 
"""



# Imports for the OracleDB itself


# Import some POX stuff
#from pox.core import core                     # Main POX object
#import pox.openflow.libopenflow_01 as of      # OpenFlow 1.0 library
#import pox.lib.packet as pkt                  # Packet parsing/construction
#from pox.lib.addresses import EthAddr, IPAddr # Address types
#import pox.lib.util as poxutil                # Various util functions
#import pox.lib.revent as revent               # Event library
#import pox.lib.recoco as recoco               # Multitasking library

# Create a logger for this component
#log = core.getLogger()


#def _go_up (event):
  # Event handler called when POX goes into up state
  # (we actually listen to the event in launch() below)
#  log.info("oracleDB up")


#@poxutil.eval_args
#def launch ():
#  """
#  Just initializing internal parameters
#  """
  # hardcoding some elements to test it out

#  core.addListenerByName("UpEvent", _go_up)

class OracleDB:

    # Define exceptions
    class OracleDBError(Exception): pass
    class UnknownContentError(OracleDBError): pass
    class UnknownSourceError(OracleDBError): pass

    def __init__(self):
        self.contentMap = {}

    def getSource (self, content):
        """returns the IP address of a P2P source for content, if one exists, or None
        otherwise."""
        import random
        if content in self.contentMap.keys():
            return random.choice(self.contentMap[content])
        else:
            return None
    
    def addSource (self, content, source):
        """adds a P2P source for the specified content. each source can be listed
        only once for each content. returns True if the insertion succeeds, False
        otherwise"""
        if content in self.contentMap.keys():
            if source in self.contentMap[content]:
                # source was already listed
                return False
            else:
                self.contentMap[content].append(source)
                return True
        else:
            # create empty list for this new content
            self.contentMap[content] = [source]
            # self.contentMap[content].append(source)
            return True
    
    def removeSource (self, content, source):
        """removes a P2P source for the specified content. Raises an
        UnknownContentError exception if content is not present in the map, and an
        UnknownSourceError excepion if the source is not listed for that content"""
        if content not in self.contentMap.keys():
            raise OracleDB.UnknownContentError("content " + content +" not present in contentMap")
        elif source not in self.contentMap[content]:
            raise OracleDB.UnknownSourceError("source " +source +" not present in the set for" + content)
        else:
            self.contentMap[content].remove(source)
    
    def listSources (self, content):
        """list all known sources for the specified content"""
        if content in self.contentMap.keys():
            return self.contentMap[content]
        else:
            return []
            
    def clear (self, content = None):
        if content is None:
            self.contentMap = {}
        elif content in self.contentMap.keys():
            del self.contentMap[content]

