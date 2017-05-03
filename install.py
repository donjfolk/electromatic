#!/usr/bin/python
import os, time



print ""
print ""
print "Installing Python lxml"
os.system('apt-get install python-lxml')  

print ""
print ""
print "Installing Python Web Framework"
os.system('pip install web.py')  



sFile = """[Unit]
Description=Serial Server Service
     
[Service]
ExecStart=/etc/electromatic/serserv.py
StandardOutput=null
     
[Install]
WantedBy=multi-user.target
Alias=serserv.service
"""

print ""
print ""
print "Configuring Serial Server Software"
oFile = open('/lib/systemd/system/serserv.service','wr+')
oFile.write(sFile)
oFile.close()
os.system('chmod +x /lib/systemd/system/serserv.service')
os.system('systemctl enable serserv.service')
os.system('systemctl start serserv.service')
os.system('systemctl restart serserv.service')





sFile = """[Unit]
Description=Serial Server Web Service
     
[Service]
ExecStart=/etc/electromatic/www.py
StandardOutput=null
     
[Install]
WantedBy=multi-user.target
Alias=www.service
"""

print ""
print ""
print "Configuring Serial Server Web Software"
oFile = open('/lib/systemd/system/www.service','wr+')
oFile.write(sFile)
oFile.close()
os.system('chmod +x /lib/systemd/system/www.service')
os.system('systemctl enable www.service')
os.system('systemctl start www.service')
os.system('systemctl restart www.service')


