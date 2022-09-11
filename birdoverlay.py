#!/bin/env python3

import os
from os import path
from time import sleep
import http.server
import socketserver

from jinja2 import Environment, FileSystemLoader

from api.Owlet import Owlet

DEBUG = True
root = path.dirname(path.realpath(__file__))
templates_dir = os.path.join(root, 'template')
env = Environment( loader = FileSystemLoader(templates_dir) )
template = env.get_template('index.html')

# Instantiate and login
api = Owlet()
authenticated = api.authenticate()

if not authenticated:
    print("Couldn't log in to owlet api")
    exit(1)

if len(api.devices) < 1:
    print("No devices found for owlet")
    exit(1)

#TODO: should make this configurable
sock_serial = api.devices[0]

def get_html():
    if DEBUG:
        print("Starting to update sensor info")

    # Refresh auth if needed
    if not api.token:
        api.authenticate()
    
    state, _ = api.vitals(sock_serial)
    
    if DEBUG:
        print(f"Got state: {state}")

    return template.render(
            hr = state['heart_rate'],
            movement_detected = int(state['movement']) != 0,
            spo2 = state['oxygen_saturation']
    )

class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # Sending an '200 OK' response
        self.send_response(200)

        # Setting the header
        self.send_header("Content-type", "text/html")

        # Whenever using 'send_header', you also have to call 'end_headers'
        self.end_headers()

        self.wfile.write(bytes(get_html(), "utf8"))

        return

handler_object = MyHttpRequestHandler

PORT = 8000
my_server = socketserver.TCPServer(("", PORT), handler_object)

# Start the server
my_server.serve_forever()
### Run until stopped
# if __name__ == "__main__":
#     while True:
#         run_updates()
#         if DEBUG:
#             print("Pausing for 10 seconds until next update")
#         sleep(10)
