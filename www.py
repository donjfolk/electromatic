#!/usr/bin/env python
import web
from os import walk
import sys, time, socket, re, os,  signal, gc, datetime, fcntl, codecs, struct
from lxml import etree
import xml.etree.cElementTree as ET

def getserial():
    # Extract serial from cpuinfo file
    cpuserial = "0000000000000000"
    try:
	f = open('/proc/cpuinfo','r')
	for line in f:
	    if line[0:6]=='Serial':
		cpuserial = line[10:26]
	f.close()
    except:
	cpuserial = "ERROR000000000"

    return cpuserial


urls = (
  '/', 'index',
  '/logs', 'logs',
  '/images/(.*)', 'images'
)
render = web.template.render('/etc/electromatic/templates/')

class images:
    def GET(self,name):
        ext = name.split(".")[-1] # Gather extension

        cType = {
            "png":"images/png",
            "jpg":"images/jpeg",
            "gif":"images/gif",
            "ico":"images/x-icon"            }

        if name in os.listdir('/etc/electromatic/images'):  # Security
            web.header("Content-Type", cType[ext]) # Set the Header
            return open('/etc/electromatic/images/%s'%name,"rb").read() # Notice 'rb' for reading images
        else:
            raise web.notfound()


class logs:
	def GET(self):
		aRet = []
		oFile = open('/var/log/serserv.log', 'r')
		for sLine in oFile.readlines():
			aRet.append(sLine)
		return render.logs(reversed(aRet))


class index:
	def GET(self):
		aBaud = [1200,4800,9600,19200,38400]
		aPort = [2101,2102,2103,2104]
		aKill = [0,0.5,1.0,1.5,2,2.5,3,3.5,4,4.5,5,5.5,6,6.5,7,7.5,8,8.5,9,9.5,10]
		aDatabit = [7,8]
		aParity = ['E','N','O']
		dData = {}
		sConfigFile = "/etc/electromatic/config.xml"
		oDoc = etree.parse(sConfigFile)
		oRoot = oDoc.getroot()
		dData['activation_date'] = oRoot.attrib['activation_date']
		dData['license'] = oRoot.attrib['license']
		aDevice = []
		for oDevices in oRoot:
		    for oDevice in oDevices:
			dDevice =  oDevice.attrib
			for key, value in dDevice.items():
				try:
					dDevice[key] = int(value)
				except:
					pass
			aDevice.append(dDevice)
			if dDevice['name'] == 'slave':
				dSlave = dDevice
			elif dDevice['name'] == 'master':
				dMaster = dDevice
			    
			elif dDevice['name'] == 'tcp':
				dTCP = dDevice
		
		
		dData['date'] = datetime.datetime.now().strftime("%Y-%m-%d")
		dData['master_device'] = []
		dData['slave_device'] = []
		dData['master_baud'] = []
		dData['slave_baud'] = []
		dData['master_width'] = []
		dData['slave_width'] = []
		dData['master_parity'] = []
		dData['slave_parity'] = []
		dData['master_stopbits'] = []
		dData['slave_stopbits'] = []
		dData['master_xon'] = []
		dData['master_rtc'] = []
		dData['slave_xon'] = []
		dData['slave_rtc'] = []
		dData['tcp_port'] = []
		dData['tcp_killport'] = []
		f = []
		for (dirpath, dirnames, filenames) in walk('/dev'):
			f.extend(filenames)
			break
		for sFile in f:
			if 'ttyU' in sFile:
				dData['master_device'].append('/dev/%s'%sFile)
				dData['slave_device'].append('/dev/%s'%sFile)
		for i in aBaud:
			dData['master_baud'].append(i)
			dData['slave_baud'].append(i)
		for i in aDatabit:
			dData['master_width'].append(i)
			dData['slave_width'].append(i)
		for i in aParity:
			dData['master_parity'].append(i)
			dData['slave_parity'].append(i)
		for i in [0,1]:
			dData['master_stopbits'].append(i)
			dData['slave_stopbits'].append(i)
		for i in [1,0]:
			dData['master_xon'].append(i)
			dData['master_rtc'].append(i)
			dData['slave_xon'].append(i)
			dData['slave_rtc'].append(i)
		for i in aPort:
			dData['tcp_port'].append(i)
		for i in aKill:
			dData['tcp_killport'].append(i)
			
		s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		ifname = 'eth0'
		dData['IP'] = socket.inet_ntoa(fcntl.ioctl(s.fileno(),0x8915,struct.pack('256s', ifname[:15]))[20:24])
		
		dData['serial'] = getserial()
		os.system('systemctl restart serserv.service')
		
		return render.index(dData, dMaster, dSlave, dTCP)
	def POST(self):
		dPost = web.input()
		sConfigFile = "/etc/electromatic/config.xml"
		oDoc = etree.parse(sConfigFile)
		oRoot = oDoc.getroot()
		aDevice = []
		for oDevices in oRoot:
		    for oDevice in oDevices:
			dDevice =  oDevice.attrib
			for key, value in dDevice.items():
				try:
					dDevice[key] = int(value)
				except:
					pass
			aDevice.append(dDevice)
			if dDevice['name'] == 'slave':
				dSlave = dDevice
			elif dDevice['name'] == 'master':
				dMaster = dDevice
			    
			elif dDevice['name'] == 'tcp':
				dTCP = dDevice
	    
		oMux =  ET.Element("mux")
		oDevices = ET.SubElement(oMux, "devices")
		
		#LICENSE 
		for key, value in oRoot.attrib.items():
		    try:
			oMux.set(key, value)
		    except:
			pass
		if str(dPost['license']) != oRoot.attrib['license']:
		    oMux.set('license', dPost['license'])
		    oMux.set('activation_date', datetime.datetime.now().strftime("%Y-%m-%d"))
		try:
		     oMux.set('serial', dPost['serial'])
		except:
		    pass
		
		

		#MASTER
		oDevice = ET.SubElement(oDevices, "device", name="master")
		for key, value in dMaster.items():
			try:
			    oDevice.set(key, value)
			except:
			    pass
		for key, value in dPost.items():
			if 'master_' in key:
			    try:
				oDevice.set(key.replace('master_',''), value)
			    except Exception, ex:
				return ex
		
		#SLAVE
		oDevice = ET.SubElement(oDevices, "device", name="slave")
		for key, value in dSlave.items():
			try:
			    oDevice.set(key, value)
			except:
			    pass
		for key, value in dPost.items():
			if 'slave_' in key:
			    try:
				oDevice.set(key.replace('slave_',''), value)
			    except Exception, ex:
				return ex
			    
		
		#TCP
		oDevice = ET.SubElement(oDevices, "device", name="tcp")
		for key, value in dTCP.items():
			try:
			    oDevice.set(key, value)
			except:
			    pass
		for key, value in dPost.items():
			if 'tcp_' in key:
			    try:
				oDevice.set(key.replace('tcp_',''), value)
			    except Exception, ex:
				return ex
		
		oTree = ET.ElementTree(oMux)
		oTree.write(sConfigFile)
		raise web.seeother('/')











if __name__ == "__main__": 
    app = web.application(urls, globals())
    app.run()    