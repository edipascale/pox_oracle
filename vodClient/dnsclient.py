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
dnsclient will attempt to request content by mapping their name to a 
domain name; the dns request will be intercepted by the oracle in the controller
and the IP address of a P2P source will be returned if available. 
"""
import httplib
import SimpleHTTPServer
import SocketServer
import threading

class IndexOutOfRange(Exception): pass
class WrongHttpResponse(Exception): pass

class DnsClient:
    def __init__(self):
        self.catalog = ['first','second']
        self.cached = []
        self.baseDomain = '.bogusvod.com'
        self.thread = threading.Thread(target=self.webserver)
        self.thread.daemon = True
        self.thread.start()

    def webserver(self):
        handler = SimpleHTTPServer.SimpleHTTPRequestHandler
        httpd = SocketServer.TCPServer(("", 1234), handler)
        httpd.serve_forever()
        
    def requestContent(self, contentIndex):
        if contentIndex < 0 or contentIndex >= len(self.catalog):
            raise IndexOutOfRange("Index " + contentIndex + ", catalog size " + self.catalog.len)
        else:
            conn = httplib.HTTPConnection(self.catalog[contentIndex] + self.baseDomain)
            fileName = self.catalog[contentIndex]+'.txt'
            conn.request("GET", fileName)
            response = conn.getresponse()
            if response.status == 200:
                with open(fileName, 'wb') as out:
                    out.write(response.read())
                    self.cached.append(self.catalog[contentIndex])
                    print "Succesfully retrieved", fileName
            else:
                raise WrongHttpResponse(response.status + response.reason)

    def interactiveShell(self):
        while True:
            print "Catalog: ", self.catalog
            index = input("Enter the index of the content you want to retrieve: ")
            try: 
                self.requestContent(index)
            except TypeError:
                print("Please insert a number")
            except IndexOutOfRange as e: 
                print("IndexOutOfRange exception: {0}".format(e.strerror))
            except WrongHttpResponse as e: 
                print("WrongHttpResponse exception: {0}".format(e.strerror))
          #  except KeyboardInterrupt:
          #      print("KeyboardInterrupt catched, quitting.")
          #      self.thread.join()

if __name__ == "__main__":
    client = DnsClient()
    client.interactiveShell()
        
