
from selenium import webdriver 
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC 
from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.common.by import By 
import time 
  
# Replace below path with the absolute path 
# to chromedriver in your computer 
driver = webdriver.Chrome('/home/fmadmin/Softphone/info/chromedriver2_linux64/chromedriver') 
  
driver.get("https://web.whatsapp.com/") 
wait = WebDriverWait(driver, 600) 

while True:
	try:
		# Replace 'Friend's Name' with the name of your friend  
		# or the name of a group  
		target = raw_input('Ingrese nombre de grupo o persona a enviar el mensaje: ')
		target = '"' + target + '"'
		x_arg = '//span[contains(@title,' + target + ')]'
		group_title = wait.until(EC.presence_of_element_located((By.XPATH, x_arg))) 
		group_title.click()

		# Replace the below string with your own message
		string = raw_input('Ingrese mensaje a enviar por Whatsapp: ')
		inp_xpath = '//*[@id="main"]/footer/div[1]/div[2]/div/div[2]'
		input_box = wait.until(EC.presence_of_element_located((By.XPATH, inp_xpath)))
		input_box.send_keys(string)
		input_box.send_keys('\n') 

	except KeyboardInterrupt:
		driver.quit()
		break

		#while True:
		#	x_path = raw_input('Insert XPATH: ')
		#	attr = raw_input('Insert attribute: ')
		#	if x_path == 'q':
		#		break
			
		#	test = self.wait.until(EC.presence_of_element_located((By.XPATH, x_path)))
		#	if attr == 'text':
		#		print test.text
		#	else:
		#		print test.get_attribute(attr)
