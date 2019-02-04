# -*- coding: utf-8 -*-
import struct, sys, random, os, hashlib, socket, threading, time
from Audio import SAMPLE_RATE, TTSMODE, OSMODE, FILEMODE, GSMMODE, PCMUMODE, PCMAMODE
from Audio.Device import AudioDev
from rtcp import RTCPHandler

#Supported payloads
PAYD_PCMU, PAYD_GSM, PAYD_PCMA, PAYD_CN = 0, 3, 8, 13
	
#Package time
PTIME = 20
MAXPTIME = 150

#Dynamic payload for a telephone-event
PAYD_TELEVENT = 101
TELEVENT_PARAMS = ('telephone-event', 8000, 1)

#The first byte of the rtp headers with V = 2, P = 0, X = 0 and CC = 0
FIRST_BYTE = 0x80

#Default minimum and maximum rtp ports
DEF_RTPMINPORT, DEF_RTPMAXPORT = 10000, 20000

#Delay (in seconds) after sending the message
DELAY = 2

#half minimum time (in seconds) to send rtcp packets
HALF_TMIN = 2.5

#TIMEOUT VARIABLES
MAX_TIMEOUT_COUNT = 100

class RTPHandler(object):

	def __init__(self, ip, rtp_minport=DEF_RTPMINPORT, rtp_maxport=DEF_RTPMAXPORT):
		self.ip = ip
		self.rtp_minport = rtp_minport
		self.rtp_maxport = rtp_maxport
		self.sending_isenabled = False
		self.is_transmitting = False
		self.listening_isenabled = False
		self.timeout = False
		self.audio_device = AudioDev()
		self.rtcp = RTCPHandler(ip) 

	def open(self):
		#Open a socket for RTP and RTCP
		self.rtp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		self.rtcp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

		#Found available ports for RTP and RTCP 
		while True:
			try:
				self.rtp_bindport = random.randint(self.rtp_minport, self.rtp_maxport)
				if self.rtp_bindport % 2 == 1:
					self.rtp_bindport += 1

				self.rtcp_bindport = self.rtp_bindport + 1
				self.rtp_socket.bind(('', self.rtp_bindport)) 			
				self.rtcp_socket.bind(('', self.rtcp_bindport))

				return self.rtp_bindport

			except socket.error:
				continue

	def getRandomValues(self):
		#Random SSRC, TS and Seq generator
		hostname = socket.gethostname()
		timestamp = str(time.time())
		port = str(self.rtp_bindport)
		string =  port + timestamp + hostname
		hexstring = hashlib.sha256(string).hexdigest()
		
		#Get 32 bits of randomness
		RTP_TSstring = ''
		SSRCstring = ''
		for n in range(8):
			SSRCstring += random.choice(hexstring)
			RTP_TSstring += random.choice(hexstring)

		SSRC = int(SSRCstring, base=16)
		firstRTP_TS = int(RTP_TSstring, base=16)
		firstRTP_TS -= firstRTP_TS % 2
		firstSeq = int(random.random() * 10000)
		firstSeq -= firstSeq % 4
 
		return SSRC, firstRTP_TS, firstSeq

	def PrepareTransmission(self, AUDIO_MODE = TTSMODE, text = 'sample text', lang = 'en', audiofile = "tmp.mp3", rmtmps = True):
		self.audio_device.open(AUDIO_MODE, text, lang, audiofile, rmtmps)
		self.audio_SSRC, self.RTP_TS, self.Seq = self.getRandomValues()
		self.rtcp.setSSRC(self.audio_SSRC)

	def StartTransmission(self, ip, dport):
		self.dport = dport
		self.receiver_ip = ip
		self.sending_isenabled = True
		self.listening_isenabled = True
		self.is_transmitting = True
		self.timeout = False

		#Start thread for listening RTP
		RTP_listener_starter = threading.Thread(target=self.RTP_listener, args=())
		RTP_listener_starter.start()

		#Start thread for listening RTCP
		print time.time()
		RTCP_listener_starter = threading.Thread(target=self.RTCP_listener, args=())
		RTCP_listener_starter.start()

		self.rtcp.setFirstRTP_TS(self.RTP_TS)

		#Start thread for sending control information
		RTCP_sending_starter = threading.Thread(target=self.SendRTCPPackages, args=())
		RTCP_sending_starter.start()

		data = chr(0) * 160
		self.start_time = time.time()
		current_time = time.time()

		for n in range(int(DELAY / 0.02)):
			#Increase sequence number and RTP timestamp
			self.Seq += 1
			self.RTP_TS += 160
			self.Seq = self.Seq % 65536
			self.RTP_TS = self.RTP_TS % 4294967296

			#Increase RTCP counters
			self.rtcp.addtoSCounters(160)

			#Send data packages of CN
			headers = struct.pack('!BBHII', FIRST_BYTE, PAYD_CN, self.Seq, self.RTP_TS, self.audio_SSRC)

			#Accurate timer
			while ((current_time - self.start_time) * 1000) < 20:
				current_time = time.time()

			self.rtp_socket.sendto(headers + data, (self.receiver_ip, self.dport))
			self.start_time = current_time

		#Start thread for sending audio stream
		RTP_sending_starter = threading.Thread(target=self.SendRTPPackages, args=())
		RTP_sending_starter.start()

		return self.is_transmitting

	def SendRTCPPackages(self):
		while self.sending_isenabled:
			try:
				time.sleep(HALF_TMIN)
				self.rtcp_socket.sendto(self.rtcp.genPackage(), (self.receiver_ip, self.dport + 1))
				time.sleep(HALF_TMIN)
			except Exception as e:
				break
		sys.exit()

	def SendRTPPackages(self):
		#Send data until the transmission is stopped
		eod = False
		timeout_counter = 0
		current_time = time.time()
		while self.sending_isenabled:
			try:
				#Increase sequence number and RTP timestamp
				self.Seq += 1 
				self.RTP_TS += 160
				self.Seq = self.Seq % 65536
				self.RTP_TS = self.RTP_TS % 4294967296
		
				if not eod:
					data, eod = self.audio_device.read(160, PCMAMODE)
					headers = struct.pack('!BBHII', FIRST_BYTE, PAYD_PCMA, self.Seq, self.RTP_TS, self.audio_SSRC)
				else:
					data = chr(0)*160
					headers = struct.pack('!BBHII', FIRST_BYTE, PAYD_CN, self.Seq, self.RTP_TS, self.audio_SSRC)

				#Increase RTCP counters
				self.rtcp.addtoSCounters(len(data))

				#Accurate timer
				while ((current_time - self.start_time) * 1000) < 20:
					current_time = time.time()

				self.rtp_socket.sendto(headers + data, (self.receiver_ip, self.dport))
				self.start_time = current_time

				if eod:
					timeout_counter += 1
					if timeout_counter == MAX_TIMEOUT_COUNT:
						self.timeout = True 

			except Exception as e:
				print e
				break
		sys.exit()

	def StopTransmission(self):
		#Stop sending and listening
		self.timeout = False
		self.sending_isenabled = False
		self.listening_isenabled = False
		self.is_transmitting = False

	def getTimeout(self):
		return self.timeout

	def RTP_listener(self):
		#Listening to every RTP package 
		try:
			while self.listening_isenabled:
				data, addr = self.rtp_socket.recvfrom(2048)
				self.rtcp.analyzeRTP(data)		
		except Exception as e:
			print 'RTP:', e

	def RTCP_listener(self):
		#Listening to every RTCP package 
		try:
			while self.listening_isenabled:
				data, addr = self.rtcp_socket.recvfrom(2048)
				self.rtcp.analyzeRTCP(data)		
		except Exception as e:
			print 'RTCP', e

	def close(self):
		#Closing sockets
		self.rtcp_socket.sendto('Close port', (self.ip, self.rtp_bindport))
		self.rtp_socket.sendto('Close port', (self.ip, self.rtcp_bindport))
		time.sleep(0.1)
		self.rtp_socket.close()
		self.rtcp_socket.close()
		self.audio_device.close()
		self.rtcp.reset()

		del self.rtp_socket
		del self.rtcp_socket
