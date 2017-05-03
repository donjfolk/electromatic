#! /usr/bin/env python


import select, socket, serial, datetime, sys, os, time,fcntl, codecs, struct, hashlib
from lxml import etree
import logging
import logging.handlers
import argparse
import os





# Deafults
LOG_FILENAME = "/var/log/serserv.log"
LOG_LEVEL = logging.INFO  # Could be e.g. "DEBUG" or "WARNING"

# Define and parse command line arguments
parser = argparse.ArgumentParser(description="Serial Server service")
parser.add_argument("-l", "--log", help="file to write log to (default '" + LOG_FILENAME + "')")

# If the log file is specified on the command line then override the default
args = parser.parse_args()
if args.log:
        LOG_FILENAME = args.log

# Configure logging to log to a file, making a new file at midnight and keeping the last 3 day's data
# Give the logger a unique name (good practice)
logger = logging.getLogger(__name__)
# Set the log level to LOG_LEVEL
logger.setLevel(LOG_LEVEL)
# Make a handler that writes to a file, making a new file at midnight and keeping 3 backups
handler = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME, when="midnight", backupCount=3)
# Format each log message like this
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
# Attach the formatter to the handler
handler.setFormatter(formatter)
# Attach the handler to the logger
logger.addHandler(handler)

# Make a class we can use to capture stdout and sterr in the log
class MyLogger(object):
        def __init__(self, logger, level):
                """Needs a logger and a logger level."""
                self.logger = logger
                self.level = level

        def write(self, message):
                # Only log if there is a message (not just a new line)
                if message.rstrip() != "":
                        self.logger.log(self.level, message.rstrip())

# Replace stdout with logging to file at INFO level
sys.stdout = MyLogger(logger, logging.INFO)
# Replace stderr with logging to file at ERROR level
sys.stderr = MyLogger(logger, logging.ERROR)


#SERIAL PORT MUX WITH TCP IP CONNECTIONS
REVISION = 1.3
MODULE_DATE = '2017-05-03'
AUTHOR = 'TRAVIS PARKER'





_READ_ONLY = select.POLLIN | select.POLLPRI

class MuxServer(object):
	def __init__(self):
		sConfigFile = "%s/config.xml"%os.path.dirname(os.path.abspath(__file__))
		oDoc = etree.parse(sConfigFile)
		oRoot = oDoc.getroot()
		dRoot = oRoot.attrib
		
		m = hashlib.md5()
		sString = "%s%s"%(dRoot['activation_date'], dRoot['serial'])
		m.update(sString)
		sHash = m.hexdigest()
		if str(dRoot['license']) != sHash:
		    raise RuntimeError('INVALID LICENSE')
		    time.sleep(30)
		    os.system('systemctl restart serserv.service')
		
		print >>sys.stdout, '\nMux Init: 30 Sec'
		time.sleep(5)
		
		for oDevices in oRoot:
		    for oDevice in oDevices:
			dDevice =  oDevice.attrib
			if dDevice['name'] == 'slave':
			    self.device = dDevice['device']
			    self.baudrate = int(dDevice['baudrate'])
			    self.width = int(dDevice['width'])
			    self.parity = dDevice['parity']
			    self.stopbits = int(dDevice['stopbits'])
			    self.xon = int(dDevice['xon'])
			    self.rtc = int(dDevice['rtc'])
			elif dDevice['name'] == 'master':
			    self.device1 = dDevice['device']
			    self.baudrate1 = int(dDevice['baudrate'])
			    self.width1 = int(dDevice['width'])
			    self.parity1 = dDevice['parity']
			    self.stopbits1 = int(dDevice['stopbits'])
			    self.xon1 = int(dDevice['xon'])
			    self.rtc1 = int(dDevice['rtc'])
			    
			elif dDevice['name'] == 'tcp':
			    self.host = dDevice['host']
			    self.port = int(dDevice['port'])
			    self.IPkillport = float(dDevice['killport'])
		self.start()
			    
		
		
		
		
		
	def start(self):	
		
		# Create a TCP/IP socket
		self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server.setblocking(0)

		self.poller = select.poll()

		self.fd_to_socket = {}
		self.clients = []
		self.pollingClient = ''
		self.timestamp = time.time()

	def close(self):

		for client in self.clients:
			print >>sys.stdout, '\nClient Closing'
			#print >>sys.stdout, '\nClient Closing %s'%(client.getpeername())
			client.close()
		try:
		    self.master.close()
		    self.slave.close()
		except:
		    pass
		#self.server.close()

		print >>sys.stderr, 'Done! =)'
		os.system('systemctl restart serserv.service')

	def add_client(self, client):
		print >>sys.stdout, str(client.getpeername())
		client.setblocking(0)
		self.fd_to_socket[client.fileno()] = client
		self.clients.append(client)
		self.poller.register(client, _READ_ONLY)

	def remove_client(self, client, why='?'):
		try:
			name = client.getpeername()
		except:
			name = 'client %d' % client.fileno()
		print >>sys.stdout, 'Closing %s: %s'%(name, why)
		self.poller.unregister(client)
		self.clients.remove(client)
		client.close()

	def run(self):
		try:
			
			#Create Slave Serial Port
			self.slave = serial.Serial(self.device, self.baudrate,
									self.width, self.parity, self.stopbits,
									1, self.xon, self.rtc)
			
			#Create Master Serial Port
			self.master = serial.Serial(self.device1, self.baudrate,
									self.width, self.parity, self.stopbits,
									1, self.xon, self.rtc)
			
			self.slave.setTimeout(0) # NON-BLOCKING
			self.master.setTimeout(0) # NON-BLOCKING
			
			self.slave.flushInput()
			self.master.flushInput()
			
			self.slave.flushOutput()
			self.master.flushOutput()
			
			self.poller.register(self.slave, _READ_ONLY)
			self.poller.register(self.master, _READ_ONLY)
			
			self.fd_to_socket[self.slave.fileno()] = self.slave
			self.fd_to_socket[self.master.fileno()] = self.master
			print >>sys.stdout, 'Slave Serial port: %s @ %s'%(self.device, self.baudrate)
			print >>sys.stdout, 'Master Serial port: %s @ %s'%(self.device1, self.baudrate)

			# Bind the socket to the port and listen
			self.server.bind((self.host, self.port))
			self.server.listen(5)
			self.poller.register(self.server, _READ_ONLY)
			self.fd_to_socket[self.server.fileno()] = self.server
			print >>sys.stdout, ' Server: %s:%d'%self.server.getsockname()

			
			
			while True:
				if time.time() > self.timestamp:
				    self.pollingClient = ''
				else:
				    print >>sys.stdout, 'TCP PORT IN CONTROL'
				events = self.poller.poll(500)
				for fd, flag in events:
					#GET SOCKET FROM FD
					s = self.fd_to_socket[fd]

					if flag & select.POLLHUP:
						self.remove_client(s, 'HUP')

					elif flag & select.POLLERR:
						self.remove_client(s, 'RECIEVED ERROR')

					elif flag & (_READ_ONLY):
						#A READABLE SERVER SOCKET IS READY TO ACCEPT A CONNECTION
						if s is self.server:
							connection, client_address = s.accept()
							self.add_client(connection)

						#SERIAL MASTER DATA
						elif s is self.master:
							if self.pollingClient != 'IP':
							    data = s.read(1024)
							    print >>sys.stdout, 'Master Serial port: RX:%s'%(' '.join(x.encode('hex') for x in data))
							    if data: 
								print >>sys.stdout, 'Slave Serial port: TX:%s'%(' '.join(x.encode('hex') for x in data))
								self.slave.write(data)
							else:
							    self.master.flushInput()
							    self.master.flushOutput()
						
						#SERIAL SLAVE DATA
						elif s is self.slave:
							data = s.read(1024)
							print >>sys.stdout, 'Slave Serial port: RX:%s'%(' '.join(x.encode('hex') for x in data))
							if data:
							    if self.pollingClient != 'IP':
								print >>sys.stdout, 'Master Serial port: TX:%s'%(' '.join(x.encode('hex') for x in data))
								self.master.write(data)
							
							    else:
									for client in self.clients:
										print >>sys.stdout, '%s Master IP port: TX:%s'%(client.getpeername(),' '.join(x.encode('hex') for x in data))
										client.send(data)

						#TCP IP CLIENT DATA
						else:
							data = s.recv(1024)
							#TCP IP CLIENT HAS DATA
							if data:
							    print >>sys.stdout, 'IP port: RX:%s'%(' '.join(x.encode('hex') for x in data))
							    self.pollingClient = 'IP'
							    self.timestamp = time.time() + self.IPkillport
							    self.slave.flushInput()
							    self.slave.flushOutput()
							    
							    print >>sys.stdout, 'Slave Serial port: TX:%s'%(' '.join(x.encode('hex') for x in data))
							    self.slave.write(data)

							#EMPTY RESULT, NO DATA
							else: self.remove_client(s, 'NO DATA')

		except serial.SerialException, ex:
			print >>sys.stderr, '\nSerial error: "%s". Closing...' %(ex)

		except socket.error, ex:
			print >>sys.stderr, '\nSocket error: %s' %(ex.strerror)

		except (KeyboardInterrupt, SystemExit):
			pass

		finally:
			self.close()
			self.start()


if __name__ == '__main__':
	while True:
		try:
			oMux = MuxServer()
			break
		except Exception, ex:
			print >>sys.stderr, '\nMux Init: %s' %(ex)
			time.sleep(5)
	oMux.run() 
	