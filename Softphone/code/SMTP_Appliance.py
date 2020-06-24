# -*- coding: utf-8 -*-
# SMTP Appliance
import base64, re, time, myip, mysql.connector

#Importing Phone 
from Phone import Softphone, MAIL, VOIP_CALL, SIM_CALL, SMS, LANG, SOFTPHONE_MAIL, DEFAULT_EMAIL

#Importing server
from serverlib import SMTPServer, DEFAULT_TIMEOUT

#Zabbix database variables
ZABBIX_HOST = 'localhost'
ZABBIX_USER = 'Zabbix_DBA'
ZABBIX_PASSWD = '@@ManaG3r1'
ZABBIX_DB = 'zabbix'

def getHeader(header, data, add_header_to_string = True):
	#checkout for special headers 'From' and 'To'
	if header in ('From:', 'To:'):
		header_content = re.findall(header + ' <(.*?)>', data)
	else:
		header_content = re.findall(header + ' (.*?)\n', data)
	#Verify if header has any content
	if header_content:
		if add_header_to_string:
			return header + ' ' + header_content[0] + '\n'
		else:
			return header_content[0]
	return ''


class SMTP_Softphone(SMTPServer):

	def __init__(self, timeout = DEFAULT_TIMEOUT, lang = LANG):
		#Startup softphone
		self.ip = myip.getmyIPaddress()
		self.softphone = Softphone(self.ip, timeout)
		
		#Check if the message have finished of being processed
		self.finished_process = True

		#Define the order that the messages will be sent
		self.order = (MAIL, VOIP_CALL, SIM_CALL, SMS)

		#Define language
		self.lang = lang

		#Get total messages received 
		self.total_messages = 0

		#Initiate server	
		SMTPServer.__init__(self, timeout = timeout)

	def addUser(self, new_user = DEFAULT_EMAIL, phone_number = '', extension = '', username = '', group = 'My Gruop'):
		self.softphone.add_user(new_user, phone_number, extension)
		self.add_user(new_user, username, group)

	def updateUser(self, new_user = DEFAULT_EMAIL, phone_number = '', extension = '', username = '', group = 'My Gruop', position = 0):
		try:
			old_user = self.smtp_users.keys()[position]

			#Update Zabbix database and dictionaries' users if user is not the same
			if old_user != new_user:
				#Update database
				zabbix_conn = mysql.connector.connect(host=ZABBIX_HOST, user=ZABBIX_USER, passwd=ZABBIX_PASSWD, database=ZABBIX_DB)
				zabbix_cursor = zabbix_conn.cursor()
				query = 'UPDATE media SET sendto = %s WHERE sendto = %s'
				zabbix_cursor.execute(query, (new_user, old_user))
				zabbix_conn.commit()

				#Update dictionaries
				self.softphone.update_user(new_user, position)
				self.update_user(new_user, position)

			self.addUser(new_user, phone_number, extension, username, group)
			print 'User has been updated successfully...'	

		except IndexError:
			print 'Position', position, 'not found'

		except:
			print 'Database parameters not recognized...'
			

	def enableMail(self):
		self.softphone.enableMail()

	def disableMail(self):
		self.softphone.disableMail()

	def enableSIMCall(self):
		self.softphone.enableSIMCall()

	def disableSIMCall(self):
		self.softphone.disableSIMCall()
	
	def enableSMS(self):
		self.softphone.enableSMS()

	def enableSMS_fulltext(self):
		self.softphone.enableSMS_fulltext()

	def disableSMS_fulltext(self):
		self.softphone.disableSMS_fulltext()

	def disableSMS(self):
		self.softphone.disableSMS()

	def enableVoIP(self):
		self.softphone.enableVoIP(self.ip)

	def disableVoIP(self):
		self.softphone.disableVoIP()

	def setLang(self, lang = LANG):
		self.lang = lang

	def setOrder(self, order = (0, 1, 2, 3)):
		self.order = order

	def process_message(self, mailfrom, rcpttos, data):

		#Processing the message received in the queue of SMTPServer
		self.finished_process = False
		mail_text = data.replace(mailfrom, SOFTPHONE_MAIL)
		sms_text, call_text = self.process_email(data)
		self.softphone.run(rcpttos, mail_text, sms_text.rstrip(), call_text, self.order, self.lang)

		#Indicate that the message received have been processed
		self.filter_dict[call_text] = (self.filter_dict[call_text][0], True)

		self.finished_process = True
		self.total_messages += 1
		print 'Messages processed: ', self.total_messages

	def process_email(self, data):
		body = ''

		#Catch up headers information from data
		headers = getHeader('From:', data) + getHeader('Subject:', data) + getHeader('Date:', data)
		subject = getHeader('Subject:', data, False)
		body_encoding = getHeader('Content-Transfer-Encoding:', data, False)

		#Check out if a regular mail is received
		try:
			body = data[data.index('\n\n') + 2:]
			if body_encoding == 'base64':
				body = base64.b64decode(body)
				body = body.replace('\r','')

			body = '\n' + body

		except ValueError:
			if not headers:
				body = data

		#If there is no subject use the whole data as the subject
		if not subject:
			subject = data

		#Returning SMS text and call text
		return headers + body, subject

	def stop(self):
		self.softphone.stop()


if __name__ == '__main__':
	try:
		server = SMTP_Softphone()

	except KeyboardInterrupt:
		server.stop()
		server.close()

