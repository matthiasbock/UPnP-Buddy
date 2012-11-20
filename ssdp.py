#!/usr/bin/python

import socket
import struct
import sys
from httplib import HTTPResponse
from BaseHTTPServer import BaseHTTPRequestHandler
from StringIO import StringIO

import gtk
import gobject


class Request(BaseHTTPRequestHandler):
	def __init__(self, request_text):
		self.rfile = StringIO(request_text)
		self.raw_requestline = self.rfile.readline()
		self.error_code = self.error_message = None
		self.parse_request()

	def send_error(self, code, message):
		self.error_code = code
		self.error_message = message


class Response(HTTPResponse):
	def __init__(self, response_text):
		self.fp = StringIO(response_text)
		self.debuglevel = 0
		self.strict = 0
		self.msg = None
		self._method = None
		self.begin()


def interface_addresses(family=socket.AF_INET):
    for fam, _, _, _, sockaddr in socket.getaddrinfo('', None):
        if family == fam:
            yield sockaddr[0]


def msearch():
	socket.setdefaulttimeout(3)
	addr = '192.168.3.101'

	print 'broadcast'
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
	sock.bind((addr, 0))

	DISCOVERY_MSG = ('M-SEARCH * HTTP/1.1\r\n' +
			 'ST: %(library)s:%(service)s\r\n' +
			 'MX: 3\r\n' +
			 'MAN: "ssdp:discover"\r\n' +
			 'HOST: 239.255.255.250:1900\r\n\r\n')

	msg = DISCOVERY_MSG % dict(library='ssdp', service='all')
	for _ in xrange(2):
		# sending it more than once will
		# decrease the probability of a timeout
		sock.sendto(msg, ('239.255.255.250', 1900))

	data = ''
	while data != None:
		try:
			data = sock.recv(1024)
		except socket.timeout:
			data = None
			print 'timeout'
			pass
		else:
			print 'response! ->',
			response = Response(data)
			print response.getheader('Location')
	return


def server():

	socket.setdefaulttimeout(5)

	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
	sock.bind(('', 1900))

	mreq = struct.pack('4sl', socket.inet_aton('239.255.255.250'), socket.INADDR_ANY)
	sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

	cond = gobject.IO_IN | gobject.IO_HUP
	gobject.io_add_watch(sock, cond, handle_requests)

	gtk.main()


def handle_requests(sock, _):
	print 'SSDP received, parsing...',

	LOCATION_MSG =    ('HTTP/1.1 200 OK\r\n' +
					'ST: %(library)s:%(service)s\r\n'
					'USN: %(service)s\r\n'
					'Location: %(loc)s\r\n'
					'Cache-Control: max-age=900\r\n\r\n')

	SERVICE_LOCS = {'Brother': 'http://192.168.3.101:8080/brother.xml'}

	data, addr = sock.recvfrom(4096)
	request = Request(data)
	if not request.error_code and \
		request.command == 'M-SEARCH' and \
		request.path == '*' and \
		'ssdp:discover' in request.headers['MAN'] and \
		'ssdp:all' in request.headers['ST']:

		print "it's an M-SEARCH broadcast!"
		service = request.headers['ST'].strip().split(':', 2)[1]
		if service in SERVICE_LOCS:
			loc = SERVICE_LOCS[service]
			msg = LOCATION_MSG % dict(library='upnp-buddy', service='urlannounce', loc=loc)
			sock.sendto(msg, addr)
	else:
		print 'nope, not for us'

	return True


if __name__ == '__main__':
	#msearch()
	server()
