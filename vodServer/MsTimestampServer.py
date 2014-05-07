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

""" Override of BaseHTTPRequestHandler
Prints milliseconds in log messages
"""

__all__ = ["MsHTTPRequestHandler"]

import datetime
import BaseHTTPServer

class MsHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def log_date_time_string(self):
        """Return the current time formatted for logging, with additional ms."""
        now = datetime.datetime.now()
        # year, month, day, hh, mm, ss, x, y, z = time.localtime(now)
        tt = now.timetuple()
        ms = now.microsecond / 1000
        s = "%02d/%3s/%04d %02d:%02d:%02d:%04d" % (
                tt[2], self.monthname[tt[1]], tt[0], tt[3], tt[4], tt[5], ms)
        return s
