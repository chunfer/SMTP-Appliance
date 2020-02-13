# -*- coding: utf-8 -*-
import serial, time, threading, os
from Audio.TTSDevice import TTSDev

#Device characteristics
DEVICE = '/dev/ttyUSB0'
BAUDRATE = 9600
TIMEOUT = 1

class ATMaster(object):
	
	def __init__(self):
		self.audio = TTSDev()
		self.listening_isenabled = False
		self.is_sending = False
		self.command = ''
		self.CLCC_isenabled = False
		self.CLCC_answer = ''
		self.CLCC_flag = False
		self.has_played = False
		self.init_ring_enabled = True
		self.init_ring_time = 0

	def open(self):
		self.ATSerial = serial.Serial(DEVICE, BAUDRATE, timeout=TIMEOUT)
		
		#set SMS mode text
		self.writeCommand('ATZ')
		time.sleep(0.4)
		self.writeCommand('AT+CMGF=1')

		#start listener
		self.listening_isenabled = True
		AT_listener_starter = threading.Thread(target=self.AT_listener, args=())
		AT_listener_starter.start()

	def makeCall(self, phone, text, lang = 'en'):
		self.audio.open(text, lang)
		self.writeCommand('ATD' + phone + ';')
		self.CLCC_isenabled = True
		self.has_played = False
		CLCC_loop_starter = threading.Thread(target=self.CLCC_loop, args=())
		CLCC_loop_starter.start()

		#Make infinite loop until the call gets finished
		while True:
			if not self.CLCC_isenabled:
				break
        
	def sendSMS(self, phone, text):
		self.writeCommand('''AT+CMGS="''' + phone + '''"\r''', False)
		time.sleep(0.4)
		self.writeCommand(text)
		time.sleep(0.4)
		self.writeCommand(chr(26), False)

	def CLCC_loop(self):
		while self.CLCC_isenabled:
			self.writeCommand('AT+CLCC')
			time.sleep(0.4)

	def writeCommand(self, command, r_enabled = True):
		if command == 'ATDDET=1':
			command = 'ATDDET=1\r\n'
			r_enabled = False
		
		if command == 'ATSO=2':
			command = 'ATSO=2\r\n'
			r_enabled = False

		self.command = command
		if r_enabled:
			self.ATSerial.write(command + '\r')
		else:
			self.ATSerial.write(command)

	def processCLCC_answer(self, answer):
		state = answer[11]

		if state == '0':
			if not self.has_played:
				time.sleep(2)
				os.system('aplay '+ self.audio.getname())
				time.sleep(2)
				self.writeCommand('ATH')
				self.has_played = True
				self.init_ring_enabled = True
				self.CLCC_isenabled = False

	def readline(self):
		eol = '\r'
		line = ''
		while True:
			char = self.ATSerial.read()
			if len(char) > 0:
				if char == eol: 
					break
				elif ord(char) >= 32:
					line += char
			else:
				break
		return line

	def AT_listener(self):
		while self.listening_isenabled:
			if self.ATSerial.inWaiting() > 0:
				data = self.readline()
				if data == 'Call Ready':
					print 'EQUIPMENT IS READY TO MAKE CALLS'

				if data != self.command and len(data) > 0:
					if data.startswith('+CLCC'):
						self.processCLCC_answer(data)

	def is_incall(self):
		return self.CLCC_isenabled
			
	def stop(self):
		self.listening_isenabled = False
		self.is_sending = False
		self.CLCC_isenabled = False
		time.sleep(0.5)
		self.writeCommand('ATH')
		time.sleep(0.1)
		self.command = ''
		self.CLCC_flag = False
		self.has_played = False
		self.init_ring_enabled = True
		self.init_ring_time = 0
		
	def close(self):
		self.ATSerial.close()
