# -*- coding: utf-8 -*-
import time
from rtp import PTIME, MAXPTIME, DEF_RTPMINPORT

#Supported media
AUDIO, VIDEO = (0,1)

#Transport types
RTP, SRTP, UDP = ('RTP/AVP','RTP/SAVP', 'UDP')

#Transmisiom modes
TRANS_MODES = ('sendonly', 'recvonly', 'sendrecv')

#Dictionaries with the static payloads
AUD_STATIC_PAYLOADS = {0: ('PCMU', 8000, 1), 3: ('GSM', 8000, 1), 4: ('G723', 8000, 1), 5: ('DVI4', 8000, 1), 6: ('DVI4', 16000, 1), 7: ('LPC', 8000, 1), 8: ('PCMA', 8000, 1), 9: ('G722', 8000, 1), 10: ('L16', 44100, 2), 11: ('L16', 44100, 1), 12: ('QCELP', 8000, 1), 13: ('CN', 8000, 1), 15: ('G728', 8000, 1), 16: ('DVI4', 11025, 1), 17: ('DVI4', 22050, 1), 18: ('G729', 8000, 1), 19: ('xCN',8000,1)}

VID_STATIC_PAYLOADS = {25: ('CelB', 90000), 26: ('JPEG', 90000), 28: ('nv', 90000), 31: ('H261', 90000), 32: ('MPV', 90000), 33: ('MP2T', 90000), 34: ('H263', 90000)}


class SessionDescriptor(object):
	def __init__(self, ip, duration=0, version='0', username='JM_Softphone', session='test_sdp', ip_type='IP4'):
		self.ip = ip
		self.ip_type = ip_type 
		self.version = version
		self.username = username
		self.session = session
		self.duration = duration
		self.audio_string = ''
		self.video_string = ''
		self.rtpmap_string = ''
		self.payloads = {}
		self.hasaudio = False
		self.hasvideo = False
		
		#Default settings of mode and package time
		self.mode_string = 'a=sendrecv\r\n'
		self.ptime_string = 'a=ptime: ' + str(PTIME) + '\r\na=maxptime: ' +  str(MAXPTIME) + '\r\n'

		#Generates the session part
		self.genStart()
		self.genMedia()

	def genStart(self):
		#Session Generator
		self.ts = int(time.time())
		self.start = 'v=' + self.version + '\r\n'
		self.start += 'o=' + self.username + ' ' + str(self.ts) + ' ' + str(self.ts) + ' IN ' + str(self.ip_type) + ' ' + self.ip + '\r\n'
		self.start += 's=' + self.session + '\r\n'
		self.start += 'c=IN ' + self.ip_type + ' ' + self.ip + '\r\n'
		if self.duration == 0:
			self.start += 't=0 0\r\n'
		else:
			self.start += 't=' + str(self.ts) + ' ' + str(self.ts + self.duration) + '\r\n' 

	def genMedia(self, port = DEF_RTPMINPORT, MEDIA_TYPE=AUDIO, TRANSPORT_TYPE=RTP):
		#Only use users ports
		if port < 1024:
			return 'Port unavailable... please use another port'
		elif MEDIA_TYPE == AUDIO:
			self.hasaudio = True
			self.audio_port = port
			self.audio_string = 'm=audio ' + str(port) + ' ' + TRANSPORT_TYPE 
		elif MEDIA_TYPE == VIDEO:
			self.hasvideo = True
			self.video_port = port
			self.video_string = 'm=video ' + str(port) + ' ' + TRANSPORT_TYPE 
			

	def rtpmap(self, PAYLOAD, PARAMS=(), ALLOW_DTMF_EVENTS=False, ALLOWED_EVENTS='0-16'):
		#The PARAMS is made for dynamic ports
		if PAYLOAD in self.payloads:
			return 'payload already mapped...'

		elif PAYLOAD in AUD_STATIC_PAYLOADS:
			if self.hasaudio:
				self.payloads[PAYLOAD] = AUD_STATIC_PAYLOADS[PAYLOAD]
				FORMAT, SAMPLE_RATE, CHANNELS = self.payloads[PAYLOAD]
				self.audio_string += ' ' + str(PAYLOAD)
				self.rtpmap_string += 'a=rtpmap:' + str(PAYLOAD) + ' ' + FORMAT + '/' + str(SAMPLE_RATE)
				if CHANNELS != 1:
					  self.rtpmap_string += '/' + str(CHANNELS)
				self.rtpmap_string += '\r\n'
			else:
				return 'Has no audio generated... please generate the audio'

		elif PAYLOAD in VID_STATIC_PAYLOADS:
			if self.hasvideo:
				self.payloads[PAYLOAD] = VID_STATIC_PAYLOADS[PAYLOAD]
				FORMAT, FREQUENCY = self.payloads[PAYLOAD]
				self.video_string += ' ' + str(PAYLOAD)
				self.rtpmap_string += 'a=rtpmap:' + str(PAYLOAD) + ' ' + FORMAT + '/' + str(FREQUENCY) + '\r\n'
			else:
				return 'Has no video generated... please generate the video'
		
		else:
			#If the PARAMS has 2 items, it recognizes the payload as a video type. PARAMS = (PAYLOAD_FORMAT, FREQUENCY)
			if len(PARAMS) == 2:
				if self.hasvideo:
					self.payloads[PAYLOAD] = PARAMS
					FORMAT, FREQUENCY = PARAMS
					self.video_string += ' ' + str(PAYLOAD)
					self.rtpmap_string += 'a=rtpmap:' + str(PAYLOAD) + ' ' + FORMAT + '/' + str(FREQUENCY) + '\r\n'
				else:
					return 'Has no video generated... please generate the video'

			#If the PARAMS has 3 items, it recognizes the payload as a audio type. PARAMS = (PAYLOAD_FORMAT, SAMPLE_RATE, CHANNELS)
			elif len(PARAMS) == 3:
				if self.hasaudio:
					self.payloads[PAYLOAD] = PARAMS
					FORMAT, SAMPLE_RATE, CHANNELS = PARAMS
					self.audio_string += ' ' + str(PAYLOAD)
					self.rtpmap_string += 'a=rtpmap:' + str(PAYLOAD) + ' ' + FORMAT + '/' + str(SAMPLE_RATE)
					if CHANNELS != 1:
					 	 self.rtpmap_string += '/' + str(CHANNELS)
					self.rtpmap_string += '\r\n'
				else:
					return 'Has no audio generated... please generate the audio'				
			else:
				return 'Please check your parameters...'	
			
			if ALLOW_DTMF_EVENTS:
				self.rtpmap_string += 'a=fmtp:' + str(PAYLOAD) + ' ' + ALLOWED_EVENTS + '\r\n' 

	def changeRTPport(self, new_port, MEDIA_TYPE=AUDIO):
		#RTP port changer
		if new_port < 1024:
			return 'Port unavailable... please use another port'
		elif MEDIA_TYPE == AUDIO:
			if self.hasaudio:
				self.audio_string = self.audio_string.replace(str(self.audio_port), str(new_port))
				self.audio_port = new_port
			else:
				return 'Has no audio generated... please generate the audio'

		elif MEDIA_TYPE == VIDEO:	
			if self.hasvideo:
				self.video_string = self.video_string.replace(str(self.video_port), str(new_port))
				self.video_port = new_port
			else:
				return 'Has no video generated... please generate the video'

	def changeTime(self, new_duration = 0):
		#Time variables changer
		new_ts = int(time.time())
		if new_duration != 0:
			if self.duration != 0:
				self.start = self.start.replace(str(self.ts + self.duration), str(new_ts + new_duration))
			else:
				self.start = self.start.replace('t=0 0', 't=' + str(new_ts) + ' ' + str(new_ts + new_duration))
		else:
			if self.duration != 0:
				self.start = self.start.replace('t=' + str(self.ts) + ' ' + str(self.ts + self.duration), 't=0 0')

		self.duration = new_duration
		self.start = self.start.replace(str(self.ts), str(new_ts))
		self.ts = new_ts


	def setMode(self, mode='sendrecv'):
		#Changes the mode in which data is trasmitted
		if mode in TRANS_MODES:
			self.mode_string = 'a=' + mode + '\r\n'
		else:
			return 'the mode you set is not available...'

	def setPtime(self, ptime=20 , maxptime=150):
		self.ptime_string = 'a=ptime: ' + str(ptime) + '\r\na=maxptime: ' + str(maxptime) + '\r\n'

	def __str__(self):
		string = self.start
		if len(self.audio_string) != 0:
			string += self.audio_string + '\r\n'

		if len(self.video_string) != 0:
			string += self.video_string + '\r\n'
		
		string += self.rtpmap_string + self.ptime_string + self.mode_string
		return string
