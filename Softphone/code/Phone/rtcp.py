# -*- coding: utf-8 -*-
import struct, random, os, getpass, time
from Audio import SAMPLE_RATE

#Package types
PT_SR, PT_RR, PT_SDES, PT_BYE, PT_APP = 200, 201, 202, 203, 204

#SDES types
END, CNAME, NAME, EMAIL, PHONE, LOC, TOOL, NOTE, PRIV = 0, 1, 2, 3, 4, 5, 6, 7, 8

# half of lost packages gap
GAP = 1500

#RTCP version
V = 2 << 6

class RTCPHandler(object):

	def __init__(self, ip):

		#Own report counters
		self.sender_pcount = 0
		self.sender_ocount = 0

		#canonical name
		self.cname = getpass.getuser() + "@"+ ip 

		#RTCP dictionaries (SSRC:[CNAME, collision_detected])
		self.participants = {}

		#Report dictionary variables (SSRC:[packets_lost, base_Seq, extended_Seq, cycle_count_enabler, Si, Ri, Ji, RTCP_arrival_TS])
		self.Rvars = {}

		#BYE variables
		self.send_bye = False
		self.reason_bye = ""

		#RTCP result variables
		self.last_jitter = 0
		self.lag_isnegative = True
		self.lag = 0
		self.signed_jitter = 0

	def setSSRC(self, SSRC):
		#Set own SSRC 
		if len(self.participants) != 0:
			del self.participants[self.SSRC]
		self.participants[SSRC] = [self.cname, False]
		self.SSRC = SSRC

	def setFirstRTP_TS(self, RTP_TS):
		#Set base RTP_timestamps
		self.firstRTP_TS = RTP_TS
		self.firstNTP_TS = time.time()
	
	def getLag(self):
		return self.lag, self.signed_jitter

	def addtoSCounters(self, ocount, pcount = 1):
		self.sender_pcount += 1
		self.sender_ocount += ocount
	
	def collisionDetector(self, SSRC, cname):
		#Collision detector method
		if not SSRC in self.participants:
			self.participants[SSRC] = [cname, False]

		elif SSRC == self.SSRC:
			self.participants[SSRC][1] = True
			self.send_bye = True

			if cname != self.cname:		
				#print "Own collision detected... appending BYE packet"
				self.reason_bye = "Collision detected"
			else:
				#print "Own loop detected... appending BYE packet"
				self.reason_bye = "RTP loop detected"


		elif cname != self.participants[SSRC][0]:
			#print "Third party collision or loop detected"
			self.participants[SSRC][1] = True


	def analyzeRTP(self, rtp_packet):
		#RTP packet analyzer
		Seq = int(rtp_packet[2:4].encode('hex'), 16)
		Si = int(rtp_packet[4:8].encode('hex'), 16)   
		SSRC = int(rtp_packet[8:12].encode('hex'), 16)

		#If there's a third party collision or loop, don't process the SSRC
		if SSRC in self.participants:
			if self.participants[SSRC][1]:
				return 0

		#Calculation of the time of arrival based on our own RTP timestamp
		Ri = self.firstRTP_TS + int((time.time() - self.firstNTP_TS) * SAMPLE_RATE)

		#Add to Report dictionary (SSRC:[packets_lost, base_Seq, extended_Seq, cycle_count_enabler, Si, Ri, Ji, RTCP_arrival_TS])
		if SSRC in self.Rvars:
			#Calculate the amount of lost packages based on the Sequence number 
			last_seq = self.Rvars[SSRC][2] & 65535
			if last_seq > 65535 - GAP and Seq < GAP:
				self.Rvars[SSRC][0] += Seq + (65535 - last_seq)
			else:
				self.Rvars[SSRC][0] += Seq - last_seq - 1
			
			self.Rvars[SSRC][2] = Seq | (self.Rvars[SSRC][2] & 4294901760)
		
			#Sequence cycles detector
			if Seq < self.Rvars[SSRC][1]:
				self.Rvars[SSRC][3] = True
			else:
				if self.Rvars[SSRC][3]:
					self.Rvars[SSRC][2] += 65536
					self.Rvars[SSRC][3] = False
			
			#Jitter calculation:
			# D(i-1, i) = (R_i - R_i-1) - (S_i - S_i-1)
			# J_i = J_i-1 + (|D(i-1, i)| - J_i-1) / 16 
			D = (Ri - self.Rvars[SSRC][5]) - (Si - self.Rvars[SSRC][4]) 
			Ji = self.Rvars[SSRC][6] + (abs(D) - self.Rvars[SSRC][6]) / 16

			#Introduction of the jitter variables into the list
			self.Rvars[SSRC][4] = Si
			self.Rvars[SSRC][5] = Ri
			self.Rvars[SSRC][6] = Ji
		else:
			self.Rvars[SSRC] = [0, Seq, Seq, False, Si, Ri, 0, 0]
			
	def analyzeRTCP(self, rtcp_packet):
		#Recursive RTCP packet analyzer
		length = 0
		PT = ord(rtcp_packet[1])

		#Packet selector
		if PT == PT_SR:
			RC = ord(rtcp_packet[0]) & 31
			P = (ord(rtcp_packet[0]) & 32) >> 5
			length = int(rtcp_packet[2:4].encode('hex'), 16) * 4
			SSRC = int(rtcp_packet[4:8].encode('hex'), 16)

			#Save NTP arrival time
			if SSRC in self.Rvars:
				self.Rvars[SSRC][7] = time.time()

			#Catch our own report variables
			for n in range(RC):
				init_Rblock = 28 + n * 24
				SSRC_n = int(rtcp_packet[init_Rblock:init_Rblock + 4].encode('hex'), 16)
				if SSRC_n == self.SSRC:
					jitter = int(rtcp_packet[init_Rblock + 12: init_Rblock + 16].encode('hex'), 16)
					if jitter > self.last_jitter:
						self.lag_isnegative = not self.lag_isnegative

					self.lag = jitter * 0.000125
					self.last_jitter = jitter
					self.signed_jitter = jitter

					if self.lag_isnegative:
						self.signed_jitter = -self.signed_jitter
						self.lag = -self.lag

					#print 'SR'
					#print '\tSSRC:', SSRC
					#print '\tfraction lost:', int(rtcp_packet[init_Rblock + 4].encode('hex'), 16)
					#print '\tpackets lost:', int(rtcp_packet[init_Rblock + 5:init_Rblock + 8].encode('hex'), 16)
					#print '\tExtended Seq:', int(rtcp_packet[init_Rblock + 8:init_Rblock + 12].encode('hex'), 16)
					#print '\tjitter: ', jitter, 'lag:', self.lag
					#print '\tLSR(secs): ', int(rtcp_packet[init_Rblock + 16: init_Rblock + 18].encode('hex'), 16)
		
		elif PT == PT_RR:
			RC = ord(rtcp_packet[0]) & 31
			P = (ord(rtcp_packet[0]) & 32) >> 5
			length = int(rtcp_packet[2:4].encode('hex'), 16) * 4
			SSRC = int(rtcp_packet[4:8].encode('hex'), 16)

			if SSRC in self.Rvars:
				self.Rvars[SSRC][6] = time.time()


			#Catch our own report variables
			for n in range(RC):
				
				init_Rblock = 8 + n * 24
				SSRC_n = int(rtcp_packet[init_Rblock:init_Rblock + 4].encode('hex'), 16)
				if SSRC_n == self.SSRC:

					jitter = int(rtcp_packet[init_Rblock + 12: init_Rblock + 16].encode('hex'), 16)
					if jitter > self.last_jitter:
						self.lag_isnegative = not self.lag_isnegative

					self.lag = jitter * 0.000125
					self.last_jitter = jitter

					if self.lag_isnegative:
						self.lag = - self.lag

					#print 'RR'
					#print '\tSSRC:', SSRC
					#print '\tfraction lost:', ord(rtcp_packet[init_Rblock + 4])
					#print '\tpackets lost:', int(rtcp_packet[init_Rblock + 5:init_Rblock + 8].encode('hex'), 16)
					#print '\tExtended Seq:', int(rtcp_packet[init_Rblock + 8:init_Rblock + 12].encode('hex'), 16)
					#print '\tjitter: ', jitter, 'lag:', self.lag
					#print '\tLSR(secs): ', int(rtcp_packet[init_Rblock + 16: init_Rblock + 18].encode('hex'), 16)
			
		elif PT == PT_SDES:
			SC = ord(rtcp_packet[0]) & 31
			P = (ord(rtcp_packet[0]) & 32) >> 5
			length = int(rtcp_packet[2:4].encode('hex'), 16) * 4
			item_type_position = 8
			for n in range(SC):
				SSRC = int(rtcp_packet[item_type_position - 4:item_type_position].encode('hex'), 16)
				
				#analyze while there's no end package
				item_type = ord(rtcp_packet[item_type_position])
				while item_type != END: 
					item_length = ord(rtcp_packet[item_type_position + 1])
					if item_type == CNAME:
						cname = rtcp_packet[item_type_position + 2: item_type_position + item_length + 3]
						#Check for colisions
						self.collisionDetector(SSRC, cname)
						
					item_type_position += item_length + 3
					item_type = ord(rtcp_packet[item_type_position])
				
				if item_type_position % 4 != 0:
					item_type_position += 8 - (item_type_position % 4)

		elif PT == PT_BYE:
			#print 'BYE was sent..'
			length = int(rtcp_packet[2:4].encode('hex'), 16) * 4
			SSRC = int(rtcp_packet[4:8].encode('hex'), 16)
			if SSRC in self.Rvars:
				del self.Rvars[SSRC]
			
			if SSRC in self.participants:
				del self.participants[SSRC]

		elif PT == PT_APP:
			length = int(rtcp_packet[2:4].encode('hex'), 16) * 4

		try:
			#analyze the next RTCP packet
			self.analyzeRTCP(rtcp_packet[length + 4:])
		
		except IndexError:
			return 0
	
	def genNTPbytes(self, NTP_time):
		#time conversor from January 1st 1970 from Guatemala to January 1st 1900 UTC 
		utc_time = NTP_time + 2208988800
		Hbytes_NTP = int(utc_time)
		Lbytes_NTP = int((utc_time - Hbytes_NTP) * 4294967296)
		return struct.pack('!II', Hbytes_NTP, Lbytes_NTP)

	def genReportBlock(self, SSRC, NTP_time):
		#Report block generator (SSRC:[packets_lost, base_Seq, extended_Seq, cycle_count_enabler, Si, Ri, Ji, RTCP_arrival_TS])

		last_seq = self.Rvars[SSRC][2] & 65535
		if last_seq < self.Rvars[SSRC][1]:
			packets_expected = last_seq + (65536 - self.Rvars[SSRC][1])
		else:
			packets_expected = last_seq - self.Rvars[SSRC][1] + 1

		packets_expected += (self.Rvars[SSRC][2] >> 16) * self.Rvars[SSRC][1]
		fraction_lost = (self.Rvars[SSRC][0] * 256/ packets_expected)
		lost_int = self.Rvars[SSRC][0] | (fraction_lost << 24)
		LSR = self.genNTPbytes(self.Rvars[SSRC][7])[2:6]
		DLSR = self.genNTPbytes(NTP_time - self.Rvars[SSRC][7])[2:6]
		#print SSRC, lost_int, self.Rvars[SSRC][2], self.Rvars[SSRC][6]
		return struct.pack('!IIII', SSRC, lost_int, self.Rvars[SSRC][2], self.Rvars[SSRC][6]) + LSR + DLSR		

	def genSR(self):
		#Sender Report generator
		length = 6
		NTP_time = time.time()
		RTP_TS = self.firstRTP_TS + int((time.time() - self.firstNTP_TS) * SAMPLE_RATE)
		reportblocks = ''
		for SSRC in self.Rvars:
			if SSRC in self.participants:
				if not self.participants[SSRC][1]:
					reportblocks += self.genReportBlock(SSRC, NTP_time)
					length += 6
			else:
				reportblocks += self.genReportBlock(SSRC, NTP_time)
				length += 6

		RC = len(self.Rvars)
		header = struct.pack('!BBHI', V | RC, PT_SR, length, self.SSRC)
		sender_info = self.genNTPbytes(NTP_time)
		sender_info += struct.pack('!III', RTP_TS, self.sender_pcount, self.sender_ocount)
		return header + sender_info + reportblocks

	def genRR(self):
		#Receiver Report generator
		length = 1
		NTP_time = time.time()
		reportblocks = ''
		for SSRC in self.Rvars:
			if not self.participants[SSRC][1]:
				reportblocks += self.genReportBlock(SSRC, NTP_time)
				length += 6

		RC = len(self.Rvars)
		header = struct.pack('!BBHI', V | RC, PT_RR, length, self.SSRC)
		return header + reportblocks
	
	def genSDES(self):
		cname_length = len(self.cname)
		items = ''
		items += chr(CNAME) + chr(cname_length) + self.cname
		items += chr(END)
		if len(items) % 4 != 0:
			items += chr(0) * (4 - len(items) % 4)
		length = 1 + len(items) / 4
		header = struct.pack('!BBHI', V | 1, PT_SDES, length, self.SSRC)
		return header + items

	def genBYE(self):
		#BYE package generator
		reason_length = len(self.reason_bye)

		#Counting the source identifier word
		length = 1
		if reason_length != 0:

			if (1 + reason_length) % 4 != 0:
				self.reason_bye += chr(0) * (4 - (1 + reason_length) % 4)
				reason_length = len(self.reason_bye)
		
			length += 1 + (1 + reason_length) / 4

		data = struct.pack('!BBHI', V | 1, PT_BYE, length, self.SSRC)
		if reason_length != 0:
			data += chr(reason_length) + self.reason_bye

		return data

	def reset(self):
		self.sender_pcount = 0
		self.sender_ocount = 0
		self.participants = {}
		self.Rvars = {}
		self.send_bye = False
		self.reason_bye = ""
		self.last_jitter = 0
		self.lag_isnegative = True
		self.lag = 0
		self.signed_jitter = 0

	def genPackage(self):
		if self.send_bye:
			data = self.genSR() + self.genSDES() + self.genBYE()
			self.reset()
		else:
			data = self.genSR() + self.genSDES()
		return data
