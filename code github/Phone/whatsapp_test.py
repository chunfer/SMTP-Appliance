
from selenium import webdriver 
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.webdriver.support import expected_conditions as EC 
from selenium.webdriver.common.keys import Keys 
from selenium.webdriver.common.by import By 
from selenium.common.exceptions import NoSuchElementException
import time 
  
# Replace below path with the absolute path 
# to chromedriver in your computer 
driver = webdriver.Chrome('/home/fmadmin/Softphone/info/chromedriver_linux64/chromedriver') 
  
driver.get("https://web.whatsapp.com/") 
wait = WebDriverWait(driver, 600) 

while True:
	try:
		# or the name of a group 
		x_path = raw_input('Insert XPATH: ')
		attr = raw_input('Insert attribute: ')
		if x_path == 'q':
			driver.quit()
			break
			
		test =  driver.find_element_by_xpath(x_path)
		if attr == 'text':
			print test.text
		else:
			print test.get_attribute(attr)
		#target = raw_input('Ingrese nombre de grupo o persona a enviar el mensaje: ')
		#target = '"' + target + '"'
		#x_arg = '//span[contains(@title,' + target + ')]'
		#group_title = wait.until(EC.presence_of_element_located((By.XPATH, x_arg))) 
		#group_title.click()

	except NoSuchElementException:
		print 'No element found...'
		

	except KeyboardInterrupt:
		driver.quit()
		break

		
