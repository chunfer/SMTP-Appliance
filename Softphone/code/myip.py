# -*- coding: utf-8 -*-
import os

def getmyIPaddress():
	os.system("ifconfig > ifconfig.txt")
	ifconfig = open("ifconfig.txt")

	#Delete first line
	ifconfig.readline()

	#Get IP address from second line
	ip = ifconfig.readline()
	ip = ip.split()[1]
	os.system("rm ifconfig.txt") 
	return ip
