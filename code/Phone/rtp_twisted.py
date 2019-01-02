# -*- coding: utf-8 -*-
import struct, sys, random, os, hashlib, socket, threading, time
from Audio import SAMPLE_RATE, TTSMODE, OSMODE, FILEMODE, GSMMODE, PCMUMODE, PCMAMODE
from Audio.Device import AudioDev
from rtcp_twisted import RTCPHandler

#Libraries for handling data streams
from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.internet.error import CannotListenError, ReactorNotRunning

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

#minimum time (in seconds) to send rtcp packets
TMIN = 5

class RTPHandler(DatagramProtocol):

	def __init__(self, ip, rtp_minport=DEF_RTPMINPORT, rtp_maxport=DEF_RTPMAXPORT):
		self.ip = ip
		self.rtp_minport = rtp_minport
		self.rtp_maxport = rtp_maxport
		self.sending_isenabled = False
		self.is_transmiting = False
		self.listening_isenabled = False 
		self.audio_device = AudioDev()
		self.rtcp = RTCPHandler(ip)

	def open(self):

		#Found available ports for RTP and RTCP 
		while True:
			try:
				self.rtp_bindport = random.randint(self.rtp_minport, self.rtp_maxport)
				if self.rtp_bindport % 2 == 1:
					self.rtp_bindport += 1

				self.rtcp_bindport = self.rtp_bindport + 1

				#Open a listener for RTP and RTCP
				self.RTP_Listener = reactor.listenUDP(self.rtp_bindport, self)
				self.RTCP_Listener = reactor.listenUDP(self.rtcp_bindport, self.rtcp)
				
				return self.rtp_bindport

			except CannotListenError:
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

	def PrepareTransmision(self, AUDIO_MODE = TTSMODE, text = 'sample text', lang = 'en', audiofile = "tmp.mp3", rmtmps = True):
		self.audio_device.open(AUDIO_MODE, text, lang, audiofile, rmtmps)
		self.audio_SSRC, self.RTP_TS, self.Seq = self.getRandomValues()
		self.rtcp.setSSRC(self.audio_SSRC)

	def StartTransmision(self, ip, dport):
		self.dport = dport
		self.receiver_ip = ip
		self.sending_isenabled = True
		self.listening_isenabled = True
		self.is_transmiting = True
		self.eod = False
		self.start_time = time.time()
		
		self.rtcp.setFirstRTP_TS(self.RTP_TS)

		self.transport.connect(ip, dport)
		#self.LC_RTP = LoopingCall(self.SendRTPPackages)
		#self.LC_RTP.start(float(PTIME)/1000)
		self.SendRTPPackages()

		self.rtcp.transport.connect(ip, dport + 1)
		time.sleep(TMIN / 2)
		#self.LC_RTCP = LoopingCall(self.SendRTCPPackages)
		#self.LC_RTCP.start(TMIN)
		self.SendRTCPPackages()
		reactor.run()

		return self.is_transmiting

	def SendRTPPackages(self):
		#Send data until the transmission is stopped
		if self.sending_isenabled:
			try:
				if time.time() - self.start_time < DELAY:
					data = chr(0)
					headers = struct.pack('!BBHII', FIRST_BYTE, PAYD_CN, self.Seq, self.RTP_TS, self.audio_SSRC)
				else:
					if not self.eod:
						data, self.eod = self.audio_device.read(160, PCMAMODE)
						headers = struct.pack('!BBHII', FIRST_BYTE, PAYD_PCMA, self.Seq, self.RTP_TS, self.audio_SSRC)
					else:
						data = chr(0)
						headers = struct.pack('!BBHII', FIRST_BYTE, PAYD_CN, self.Seq, self.RTP_TS, self.audio_SSRC)

				self.transport.write(headers + data)

				#Increase sequence number and RTP timestamp
				self.Seq += 1 
				self.RTP_TS += 160
				self.Seq = self.Seq % 65536
				self.RTP_TS = self.RTP_TS % 4294967296

				#Increase RTCP counters
				self.rtcp.addtoSCounters(len(data))
				reactor.callLater(float(PTIME)/1000, self.SendRTPPackages)
				
			except AttributeError:
				#self.LC_RTP.stop()
				self.sending_isenabled = False
				pass

		#else:
			#self.LC_RTP.stop()

	def SendRTCPPackages(self):
		if self.sending_isenabled:
			try:
				self.rtcp.transport.write(self.rtcp.genPackage())
				reactor.callLater(TMIN, self.SendRTCPPackages)
			except AttributeError:
				self.sending_isenabled = False
				pass
				#self.LC_RTCP.stop()
		#else:
			#self.LC_RTCP.stop()

	def StopTransmision(self):
		#Stop sending and listening
		self.sending_isenabled = False
		self.listening_isenabled = False
		self.is_transmiting = False
		self.rtcp.reset()
		self.RTP_Listener.stopListening()
		self.RTCP_Listener.stopListening()

	def close(self):
		reactor.stop()


	def datagramReceived(self, data, addr):
		#Listening to every RTP package 
		try:
			self.rtcp.analyzeRTP(data)
		except CannotListenError:
			pass

