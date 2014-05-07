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
tcpclient will attempt to request content through a normal HTTP GET request,
which is going to be intercepted by the oracle in the controller. An HTTP
redirect (code 307) will be sent with the IP address of a P2P source.
"""
import httplib
import SimpleHTTPServer
import SocketServer
import threading
import sys
import datetime

class IndexOutOfRange(Exception): pass
class WrongHttpResponse(Exception): pass

class TcpClient:
    def __init__(self, listeningPort, targetPort, numRequests):
        self.listeningPort = listeningPort
        self.targetPort = targetPort
        self.numRequests = numRequests
        self.catalog = ['first','second']
        self.cached = []
        self.baseDomain = 'bogusdomain.com'
        self.thread = threading.Thread(target=self.webserver)
        self.thread.setDaemon(True)
        self.thread.start()
        self.monthname = [None,
                 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    def webserver(self):
        handler = SimpleHTTPServer.SimpleHTTPRequestHandler
        httpd = SocketServer.TCPServer(("", self.listeningPort), handler)
        httpd.serve_forever()
        
    def requestContent(self, fileName):
        downloaded = False
        location = self.baseDomain
        port = self.targetPort
        while not downloaded:
            conn = httplib.HTTPConnection(location, int(port))
            conn.request("GET", fileName)
            print self.getTimeStamp(), 'Sent connection request to ' + location+':'+str(port)
            response = conn.getresponse()
            if response.status == 307:
                newlocation = response.getheader('location')
            	sep = newlocation.rfind(':')
            	location = newlocation[:sep]
            	port = newlocation[sep+1:]
            	print self.getTimeStamp(), 'Received http redirect to', location + ':' + port
            elif response.status == 200:
                downloaded = True
                print self.getTimeStamp(), 'Received http 200 OK'
            else:
                raise WrongHttpResponse(str(response.status) + ' ' + response.reason)
        with open(fileName, 'wb') as out:
            out.write(response.read())                
            print self.getTimeStamp(), fileName, 'written succesfully'
            # self.cached.append(self.catalog[contentIndex])

    def interactiveShell(self):
    	running = True
        while running:
            print "Catalog: ", self.catalog
            index = input("Enter the index of the content you want to retrieve: ")
            try:
                j = int(index)
                for i in range(self.numRequests):
                    print 'Request', i+1, 'of', self.numRequests
                    self.requestContent(self.catalog[j])
            except TypeError:
                print("Please insert a number")
            except IndexOutOfRange as e: 
                print("IndexOutOfRange exception: {0}".format(e.strerror))
            except WrongHttpResponse as e: 
                print("WrongHttpResponse exception: {0}".format(e.strerror))
                running = False
            except:
            	print("Unexpected error:", sys.exc_info()[0])
            	raise
            	running = False

    def getTimeStamp(self):
        now = datetime.datetime.now()
        tt = now.timetuple()
        ms = now.microsecond / 1000
        s = "[%02d/%3s/%04d %02d:%02d:%02d:%04d] " % (
                tt[2], self.monthname[tt[1]], tt[0], tt[3], tt[4], tt[5], ms)
        return s

if __name__ == "__main__":
    # first argument is the listening port for the webserver
    # second argument is the port to contact for the HTTP request
    # third argument is the number of consecutive requests to send for each content
    # (for the delay measurements across multiple requests)
    if len(sys.argv) > 3:
        numRequests = int(sys.argv[3])
    else:
        numRequests = 1
    if len(sys.argv) > 2:
        targetPort = int(sys.argv[2])
    else:
        targetPort = 9003
    if len(sys.argv) > 1:
        listeningPort = int(sys.argv[1])
    else:
        listeningPort = 9001
    client = TcpClient(listeningPort, targetPort, numRequests)
    for i in range(numRequests):
        print 'Request', i+1, 'of', numRequests
        client.requestContent("first.txt")
    # client.interactiveShell()
