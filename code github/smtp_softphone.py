# -*- coding: utf-8 -*-
# SMTP-Softphone
import asyncore, base64, myip, re, time
from smtpd import SMTPServer
from Phone import Softphone, MAIL, VOIP_CALL, SIM_CALL, SMS, LANG, SOFTPHONE_MAIL

class SMTP_Softphone(SMTPServer):

	def start(self, ip):
		self.softphone = Softphone(ip)
		self.queue_isenabled = True
		self.finished_process = False
		self.mails_queue = []
		QueueLoop_starter = threading.Thread(target=self.QueueLoop, args=())
		QueueLoop_starter.start()	
	
	def process_message(self, peer, mailfrom, rcpttos, data):
		self.mails_queue.append((mailfrom, rcpttos, data))
	
	def QueueLoop(self):
		while self.queue_isenabled:
			if len(self.mails_queue) > 0:
				self.finished_process = False
				mailfrom, rcpttos, data = self.mails_queue.pop(0) #First in, first out queue
				mail_text = data.replace(mailfrom, SOFTPHONE_MAIL)
				sms_text, call_text = self.process_data(data)
				self.softphone.run(mail_text, rcpttos, sms_text, call_text, (MAIL, VOIP_CALL, SIM_CALL, SMS), LANG)
				self.finished_process = True

	def process_data(self, data):
		encoding = re.findall(r'Content-Transfer-Encoding: (.*?)\n', data)[0]
		call_text = re.findall(r'Subject: (.*?)\n', data)[0]

		if encoding == 'base64':
			body_b64 = ''
			headers = ''
			is_body = False
			for line in data.split('\n'):
				if len(line) == 0:
					is_body = True

				if is_body:
					body_b64 += line
				elif line.startswith('From') or line.startswith('To') or line.startswith('Date') or line.startswith('Subject'):
					 headers += line + '\n'

			body = base64.b64decode(body_b64)
			body = body.replace('\r','')
			return headers + '\n' + body, call_text
			
	def stop(self):
		self.queue_isenabled = False
		while True:
			if self.finished_process:
				break

		time.sleep(0.1)
		self.softphone.stop()

def run():
	ip = myip.getIPaddress()
	SMTP_Phone = SMTP_Softphone((ip, 25), None)
	SMTP_Phone.start(ip)
	try:
		asyncore.loop()
	except KeyboardInterrupt:
		SMTP_Phone.stop()
		pass

if __name__ == '__main__':
	run()
	
