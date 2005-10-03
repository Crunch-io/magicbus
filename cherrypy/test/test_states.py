"""
Copyright (c) 2004, CherryPy Team (team@cherrypy.org)
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, 
are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, 
      this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, 
      this list of conditions and the following disclaimer in the documentation 
      and/or other materials provided with the distribution.
    * Neither the name of the CherryPy Team nor the names of its contributors 
      may be used to endorse or promote products derived from this software 
      without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND 
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE 
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE 
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL 
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER 
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, 
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE 
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import time
import threading

import cherrypy


class Root:
    def index(self):
        return "Hello World"
    index.exposed = True
    
    def ctrlc(self):
        raise KeyboardInterrupt()
    ctrlc.exposed = True
    
    def restart(self):
        cherrypy.server.restart()
        return "app was restarted succesfully"
    restart.exposed = True

cherrypy.root = Root()
cherrypy.config.update({
    'global': {
        'server.logToScreen': False,
        'server.environment': 'production',
    },
})


import helper


class ServerStateTests(helper.CPWebCase):
    
    def test_0_NormalStateFlow(self):
        # Without having called "cherrypy.server.start()", we should
        # get a NotReady error
        self.assertRaises(cherrypy.NotReady, self.getPage, "/")
        
        # Test server start
        cherrypy.server.start(True, self.serverClass)
        self.assertEqual(cherrypy.server.state, 1)
        
        if self.serverClass:
            host = cherrypy.config.get('server.socketHost')
            port = cherrypy.config.get('server.socketPort')
            self.assertRaises(IOError, cherrypy._cpserver.check_port, host, port)
        
        self.getPage("/")
        self.assertBody("Hello World")
        
        # Test server stop
        cherrypy.server.stop()
        self.assertEqual(cherrypy.server.state, 0)
        
        # Once the server has stopped, we should get a NotReady error again.
        self.assertRaises(cherrypy.NotReady, self.getPage, "/")
    
    def test_1_Restart(self):
        # Test server start
        cherrypy.server.start(True, self.serverClass)
        self.getPage("/")
        self.assertBody("Hello World")
        
        # Test server restart from this thread
        cherrypy.server.restart()
        self.assertEqual(cherrypy.server.state, 1)
        self.getPage("/")
        self.assertBody("Hello World")
        
        # Test server restart from inside a page handler
        self.getPage("/restart")
        self.assertEqual(cherrypy.server.state, 1)
        self.assertBody("app was restarted succesfully")
        
        cherrypy.server.stop()
        self.assertEqual(cherrypy.server.state, 0)
    
    def test_2_KeyboardInterrupt(self):
        if self.serverClass:
            
            # Raise a keyboard interrupt in the HTTP server's main thread.
            def interrupt():
                cherrypy.server.wait()
                cherrypy.server.httpserver.interrupt = KeyboardInterrupt
            threading.Thread(target=interrupt).start()
            
            # We must start the server in this, the main thread
            cherrypy.server.start(False, self.serverClass)
            # Time passes...
            self.assertEqual(cherrypy.server.httpserver, None)
            self.assertEqual(cherrypy.server.state, 0)
            self.assertRaises(cherrypy.NotReady, self.getPage, "/")
            
            # Raise a keyboard interrupt in a page handler; on multithreaded
            # servers, this should occur in one of the worker threads.
            # This should raise a BadStatusLine error, since the worker
            # thread will just die without writing a response.
            def interrupt():
                cherrypy.server.wait()
                from httplib import BadStatusLine
                self.assertRaises(BadStatusLine, self.getPage, "/ctrlc")
            threading.Thread(target=interrupt).start()
            
            cherrypy.server.start(False, self.serverClass)
            # Time passes...
            self.assertEqual(cherrypy.server.httpserver, None)
            self.assertEqual(cherrypy.server.state, 0)
            self.assertRaises(cherrypy.NotReady, self.getPage, "/")


def run(server, conf):
    helper.setConfig(conf)
    ServerStateTests.serverClass = server
    suite = helper.CPTestLoader.loadTestsFromTestCase(ServerStateTests)
    try:
        helper.CPTestRunner.run(suite)
    finally:
        cherrypy.server.stop()


if __name__ == "__main__":
    conf = {'server.socketHost': '127.0.0.1',
            'server.socketPort': 8000,
            'server.threadPool': 10,
            'server.logToScreen': False,
            'server.logConfigOptions': False,
            'server.environment': "production",
            'server.showTracebacks': True,
            }
    def _run(server):
        print
        print "Testing %s..." % (server or "serverless")
        run(server, conf)
    _run(None)
    _run("cherrypy._cpwsgi.WSGIServer")
    _run("cherrypy._cphttpserver.PooledThreadServer")
    conf['server.threadPool'] = 1
    _run("cherrypy._cphttpserver.CherryHTTPServer")