# Author: Juan Fernando Montufar Juarez
# Whatsapp chat app version 2
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
CHAT_FILE = '<your chat file path goes here>'

#Whatsapp messages Paths
FILTER = '_3_7SH _3DFk6 message'
TARGET_SEARCH_PATH = '//label[@class="_2MSJr"]/input'
CLASS_PATH = '//div[@class="_9tCEa"]/div[last()]/div'
AUTHOR_PATH = CLASS_PATH + '/div/div[last()-1]'
READ_PATH = AUTHOR_PATH + '/div/span'
INPUT_PATH = '//*[@id="main"]/footer/div[1]/div[2]/div/div[2]'

#Deletion variable
BACKSPACES = 30

class Chat(object):
	def __init__(self):
		#Control variables
		self.listening_isenabled = False
		self.isdone = False
		self.finished_reading = True
		self.first_message = True
		self.previous_author = ''
		self.previous_text = ''

		#Chat file logging
		logging.basicConfig(filename=CHAT_FILE,level=logging.ERROR, format=FORMAT)

		#Web initiators
		self.driver = webdriver.Chrome('<Your Chromium Web driver path goes here>')
		self.driver.get("https://web.whatsapp.com/") 
		self.wait = WebDriverWait(self.driver, 600)

	def startChat(self, target):
		self.isdone = False
		logging.error(time.strftime("%m/%d/%Y %H:%M:%S") + ' CHAT STARTING with: '+ target)

		#Search for the target
		target_box = self.wait.until(EC.presence_of_element_located((By.XPATH, TARGET_SEARCH_PATH)))
		target_box.click()

		#Delete target box content and input the text
		target_box.send_keys(Keys.BACKSPACE * BACKSPACES)
		target_box.send_keys(target)

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
			
				#In Whatsapp web every copyable 
				if FILTER in class_elt.get_attribute('class'):
					author_elt = self.driver.find_element_by_xpath(AUTHOR_PATH)
					author = author_elt.get_attribute('data-pre-plain-text')
					read_elt = self.driver.find_element_by_xpath(READ_PATH)
					text = read_elt.text
					if author != self.previous_author or text != self.previous_text:
						time.sleep(0.7)
						# Redo search for debuging errors
						author_elt = self.driver.find_element_by_xpath(AUTHOR_PATH)
						author = author_elt.get_attribute('data-pre-plain-text')
						read_elt = self.driver.find_element_by_xpath(READ_PATH)
						text = read_elt.text

						self.previous_author = author
						self.previous_text = text
						
						#Ignore the first chat message
						if self.first_message:	
							self.first_message = False
						else:		
							logging.error(author + text)

				self.finished_reading = True

			except NoSuchElementException:
				self.first_message = False
				self.finished_reading = True
				pass

	def SendMessage(self, message):
		if message == 'q':
			self.stop()
			logging.error(time.strftime("%m/%d/%Y %H:%M:%S")  +' CHAT FINISHED...')
			self.isdone = True
		else:
			self.input_box.send_keys(message)
			self.input_box.send_keys('\n') 

	def isDone(self):
		return self.isdone

	def stop(self):
		self.listening_isenabled = False
		self.first_message = True
		while True:
			if self.finished_reading:
				break
		self.previous_author = ''
		self.previous_text = ''

	def close(self):
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
					message = raw_input('Write a message here (send \'q\' to quit): ')
					WChat.SendMessage(message)
					if WChat.isDone():
						break

			elif start_chat == 'N':
				WChat.stop()
				WChat.close()
				break

		except KeyboardInterrupt:
			WChat.stop()
			WChat.close()
			break
