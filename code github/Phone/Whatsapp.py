# Author: Juan Fernando Montufar Juarez
#
# To use this program you should follow the next steps:
# 1- Install selenium:
#	$ sudo pip install selenium
#
# 2- Install Chromium web browser
#	$ sudo apt install chromium-browser
# 
# 3- Download Chromium web driver at:
#	https://chromedriver.storage.googleapis.com/index.html?path=2.46/
#
# You are ready to use this program.
#
# For reading the incoming messages you should use the following command:
#	$ tail -f CHAT_FILE

#Basic imports
import time, threading, logging

#Selenium imports
from selenium import webdriver 
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC 
from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

#Logging variables
FORMAT = '%(message)s'
CHAT_FILE = '<Your chat file goes here>'

#Whatsapp messages Paths
FILTER = '_3_7SH _3DFk6 message'
CLASS_PATH = '//*[@id="main"]/div[3]/div/div/div[3]/div[last()]/div'
AUTHOR_PATH = CLASS_PATH + '/div/div[last()-1]'
READ_PATH = AUTHOR_PATH + '/div/span'
INPUT_PATH = '//*[@id="main"]/footer/div[1]/div[2]/div/div[2]'

class Chat(object):
	def __init__(self):
		#Control variables
		self.listening_isenabled = False
		self.isdone = False
		self.finished_reading = False
		self.previous_author = ''
		self.previous_text = ''

		#Chat file logging
		logging.basicConfig(filename=CHAT_FILE,level=logging.ERROR, format=FORMAT)

		#Web initiators
		self.driver = webdriver.Chrome('<web driver path>')
		self.driver.get("https://web.whatsapp.com/") 
		self.wait = WebDriverWait(self.driver, 600)

	def startChat(self, target):
		self.isdone = False
		logging.error(time.strftime("%m/%d/%Y %H:%M:%S") + ' CHAT STARTING with: '+ target)

		#Select the target in Whatsapp web
		target = '"' + target + '"'
		x_arg = '//span[contains(@title,' + target + ')]'
		group_title = self.wait.until(EC.presence_of_element_located((By.XPATH, x_arg))) 
		group_title.click()

		#Get the input box element 
		self.input_box = self.wait.until(EC.presence_of_element_located((By.XPATH, INPUT_PATH)))

		#Start thread for listening messages
		self.listening_isenabled = True
		Message_listener_starter = threading.Thread(target=self.Message_listener, args=())
		Message_listener_starter.start()

	def Message_listener(self):
		#Listen to the last message sent
		while self.listening_isenabled:
			try:
				self.finished_reading = False
				class_elt = self.driver.find_element_by_xpath(CLASS_PATH)
			
				#In Whatsapp web every copyable text has in its class the FILTER string
				if FILTER in class_elt.get_attribute('class'):
					time.sleep(0.6)
					author_elt = self.driver.find_element_by_xpath(AUTHOR_PATH)
					author = author_elt.get_attribute('data-pre-plain-text')
					read_elt = self.driver.find_element_by_xpath(READ_PATH)
					text = read_elt.text
					if author != self.previous_author or text != self.previous_text:
						self.previous_author = author
						self.previous_text = text
						logging.error(author + text)
		
				self.finished_reading = True

			except NoSuchElementException:
				self.finished_reading = True
				pass

	def SendMessage(self, message):
		#Send q for quitting the current chat, otherwise send the message to your group or person
		if message == 'q':
			self.stop()
			logging.error(time.strftime("%m/%d/%Y %H:%M:%S")  +' CHAT FINISHED...')
			self.isdone = True
		else:
			self.input_text = message
			self.input_box.send_keys(message)
			self.input_box.send_keys('\n') 

	def isDone(self):
		#Checks the chat status
		return self.isdone

	def stop(self):
		#Stops the listener
		self.listening_isenabled = False
		while True:
			if self.finished_reading:
				break
		self.previous_author = ''
		self.previous_text = ''

	def close(self):
		#Closes the webdriver
		self.driver.quit()

if __name__ == '__main__':
	WChat = Chat()
	while True:
		try:
			start_chat = raw_input('Do you wish to start a chat?(Y/N): ')
			if start_chat == 'Y':
				target = raw_input('Input the group or person you would like to chat with: ')
				WChat.startChat(target)
				while True:
					message = raw_input()
					WChat.SendMessage(message)
					if WChat.isDone():
						break

			elif start_chat == 'N':
				WChat.stop()
				time.sleep(0.5)
				WChat.close()
				break

		except KeyboardInterrupt:
			WChat.stop()
			time.sleep(0.5)
			WChat.close()
			break
