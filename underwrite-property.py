import datetime
from dateutil.relativedelta import relativedelta
import json
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

with open("config.json", "r") as f:
    cfg = json.load(f)
  
PROPERTY_ADDRESS = cfg["targets"]["property_address"]
PROPSTREAM_EMAIL = cfg["propstream"]["email"]
PROPSTREAM_PASSWORD = cfg["propstream"]["password"]
COMPASS_EMAIL = cfg["compass"]["email"]
COMPASS_PASSWORD = cfg["compass"]["password"]
DEFAULT_TIMEOUT = cfg["timeouts"]["default"]
LOGIN_TIMEOUT = cfg["timeouts"]["login"]
SEARCH_TIMEOUT = cfg["timeouts"]["search"]
URL_REDFIN = "https://www.redfin.com/"

def initialize_chrome_options():
  # Initialize special chrome options for selenium to utilize
  chrome_options = webdriver.ChromeOptions()
  chrome_options.add_experimental_option("detach", True) # Keep browser open after completion
  chrome_options.add_argument("--start-maximized")
  chrome_options.add_argument("--disable-notifications")
  chrome_options.add_argument("--disable-site-isolation-trials")
  return chrome_options

def initialize_chrome_webdriver(chrome_options):
  return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

chrome_options = initialize_chrome_options()
driver = initialize_chrome_webdriver(chrome_options)
actions = ActionChains(driver)

def switch_to_recently_opened_tab():
  driver.switch_to.window(driver.window_handles[len(driver.window_handles) - 1])

def sign_into_propstream(email, password):
  # Autofill email and password fields.
  WebDriverWait(driver, DEFAULT_TIMEOUT).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='username']")))
  if (email):
    driver.find_element(By.CSS_SELECTOR, "input[name='username']").send_keys(email)
  if (password):
    driver.find_element(By.CSS_SELECTOR, "input[name='password']").send_keys(password)
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
  # Wait until property address field after login is clickable
  WebDriverWait(driver, LOGIN_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='Enter County, City, Zip Code(s) or APN #']")))

def get_info_from_propstream(property_address):
  # Once in PropStream, look up property address and grab all important information
  WebDriverWait(driver, DEFAULT_TIMEOUT).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[placeholder='Enter County, City, Zip Code(s) or APN #']")))
  driver.find_element(By.CSS_SELECTOR, "input[placeholder='Enter County, City, Zip Code(s) or APN #']").send_keys(property_address)
  
  # Click Details button
  details = WebDriverWait(driver, SEARCH_TIMEOUT).until(EC.presence_of_element_located((By.XPATH, "//span[text()='Details']")))
  actions.move_to_element(details).perform()
  details.click()

  # Grab owner and mortgage info
  WebDriverWait(driver, DEFAULT_TIMEOUT).until(EC.presence_of_element_located((By.XPATH, "//div[text()='Owner 1 Name']/following-sibling::div")))
  owner = driver.find_element(By.XPATH, "//div[text()='Owner 1 Name']/following-sibling::div").text
  mortgage = driver.find_element(By.XPATH, "//div[text()='Est. Mortgage Balance']/preceding-sibling::div").text
  driver.find_element(By.XPATH, "//div[text()='Comparables & Nearby Listings']").click()

  # Filter by year built
  year_built = WebDriverWait(driver, DEFAULT_TIMEOUT).until(EC.presence_of_element_located((By.XPATH, "//div[contains(text(),'Year Built')]/following-sibling::div")))
  actions.move_to_element(year_built).perform()
  if (year_built.text):
    year_built = int(year_built.text)
    driver.find_element(By.CSS_SELECTOR, "input[name='yearBuiltMin']").send_keys(year_built - 10)
    driver.find_element(By.CSS_SELECTOR, "input[name='yearBuiltMax']").send_keys(year_built + 10)

  # Grab square footage
  square_footage = driver.find_element(By.XPATH, "//div[contains(text(),'SqFt')]/following-sibling::div")
  if (square_footage.text):
    square_footage = int(square_footage.text.replace(",", ""))

  # Filter by public record
  public_record = driver.find_element(By.XPATH, "//span[text()='Public Record']/preceding-sibling::input")
  driver.execute_script("arguments[0].click()", public_record)

  # Setting Sale Date Min doesn't work because date picker is finicky
  #sale_date_min = driver.find_element(By.CSS_SELECTOR, "input[name='saleDateMin']")
  #three_months_ago = (datetime.today() - relativedelta(months=3)).replace(day=1).strftime("%m/%d/%Y")
  #sale_date_min.clear()
  #sale_date_min.send_keys(three_months_ago)

  return {
    "owner": owner,
    "mortgage": mortgage,
    "square_footage": square_footage
  }

def sign_into_compass(email, password):
  log_in = WebDriverWait(driver, SEARCH_TIMEOUT).until(EC.presence_of_element_located((By.CSS_SELECTOR, "button[data-label='Log In']")))
  log_in.click()
  driver.implicitly_wait(DEFAULT_TIMEOUT)
  driver.find_element(By.CSS_SELECTOR, ".uc-authentication button:nth-child(5)").click()
  if email:
    driver.find_element(By.CSS_SELECTOR, "input[name='email']").send_keys(email)
    driver.find_element(By.ID, "continue").click()
    if password:
      driver.find_element(By.CSS_SELECTOR, "input[name='password']").send_keys(password)
      driver.find_element(By.ID, "continue").click()
  
  # Wait for user to log into compass.com
  # Wait for "Forgot Password" button to disappear
  forgot_password = driver.find_element(By.CSS_SELECTOR, ".uc-authentication-footer button")
  WebDriverWait(driver, LOGIN_TIMEOUT).until(EC.staleness_of(forgot_password))

def get_info_from_compass(property_address):
  try:
    search = WebDriverWait(driver, SEARCH_TIMEOUT).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[aria-describedBy='location-lookup-input-description']")))
  except TimeoutException:
    return 1
  search.click()
  search.send_keys(property_address)
  mls_number = WebDriverWait(driver, SEARCH_TIMEOUT).until(EC.presence_of_element_located((By.XPATH, "//th[text()='MLS #']/following-sibling::td"))).text
  try:
    ask_price = driver.find_element(By.XPATH, "//div[text()='Price']//preceding-sibling::div").text
  except:
    ask_price = "N/A"
  return {
    "mls_number": mls_number,
    "ask_price": ask_price,
    "pictures": driver.current_url
  }

def get_info_from_redfin(property_address):
  mls_number = ""
  ask_price = ""
  pictures = ""
  driver.get("https://www.google.com/")
  search = driver.find_element(By.CSS_SELECTOR, "input[title='Search']")
  search.send_keys(f"redfin {property_address}")
  driver.find_element(By.CSS_SELECTOR, "input[value='Google Search']").submit()
  try:
    redfin_link = driver.find_element(By.CSS_SELECTOR, f"a[href*='{URL_REDFIN}']")
    redfin_link.click()
    try:
      mls_number = WebDriverWait(driver, DEFAULT_TIMEOUT).until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'sourceContent)]/span[2]"))).text
    except TimeoutException:
      pass
    try:
      ask_price = WebDriverWait(driver, DEFAULT_TIMEOUT).until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'statsValue')]"))).text
    except TimeoutException:
      pass
    pictures = driver.current_url
  except:
    return {
      "mls_number": mls_number,
      "ask_price": ask_price,
      "pictures": pictures
    }
  return {
    "mls_number": mls_number,
    "ask_price": ask_price,
    "pictures": pictures
  }

def send_text_to_word_counter(text):
  driver.execute_script("window.open('https://wordcounter.net/');")
  recently_opened_tab = driver.window_handles[len(driver.window_handles) - 1]
  driver.switch_to.window(recently_opened_tab)
  driver.find_element(By.TAG_NAME, "textarea").send_keys(text)

def main():
  driver.get("https://login.propstream.com/")
  sign_into_propstream(PROPSTREAM_EMAIL, PROPSTREAM_PASSWORD)
  propstream_info = get_info_from_propstream(PROPERTY_ADDRESS)

  driver.execute_script("window.open('https://www.compass.com/');")
  switch_to_recently_opened_tab()
  sign_into_compass(COMPASS_EMAIL, COMPASS_PASSWORD)
  listing_info = get_info_from_compass(PROPERTY_ADDRESS)
  if listing_info == 1:
    listing_info = get_info_from_redfin(PROPERTY_ADDRESS)

  notes = PROPERTY_ADDRESS + "\n"
  notes += f"-MLS #: {listing_info['mls_number']}\n"
  notes += f"-Owner: {propstream_info['owner']}\n"
  notes += f"-Est. Mortgage: {propstream_info['mortgage']}\n"
  notes += "-Pool: \n"
  notes += f"Pictures: {listing_info['pictures']}\n\n"

  notes += f"*ORIGINAL {datetime.date.today().strftime('%m/%d/%y')}*\n"
  notes += f"Asking Price {listing_info['ask_price']}\n"
  notes += "ARV \n"
  notes += "Repairs \n"
  notes += "Your Fee $15,000\n"
  notes += "Credit to your buyer $0\n"
  notes += "Wholesale Discount 80%\n"
  notes += "MAO Wholesale \n"
  notes += "% of ARV \n"
  notes += "Amount under asking \n\n"

  notes += "Comp:\n"
  notes += "-#### Street\n"
  notes += "-Sold on mm/dd/yy for $___k\n"
  notes += "-Pool: \n"
  notes += "Compass link\n\n"

  notes += "ARV Adjustments:\n"
  notes += "-Comp Sold For: \n"
  notes += "-Comp has extra bed: -$10k\n"
  notes += "-Comp has extra bath: -$10k\n"
  notes += "Final ARV: \n\n"

  notes += "Reno:\n"
  notes += f"-Tier 1 ($30/sf): {'${:,}'.format(propstream_info['square_footage'] * 30)} on {'{:,}'.format(propstream_info['square_footage'])}sf\n"
  notes += f"-Tier 1.5 ($45/sf): {'${:,}'.format(propstream_info['square_footage'] * 45)} on {'{:,}'.format(propstream_info['square_footage'])}sf\n"
  notes += f"-Tier 2 ($60/sf): {'${:,}'.format(propstream_info['square_footage'] * 60)} on {'{:,}'.format(propstream_info['square_footage'])}sf\n"
  notes += f"-Tier 3 ($90/sf): {'${:,}'.format(propstream_info['square_footage'] * 90)} on {'{:,}'.format(propstream_info['square_footage'])}sf"
  send_text_to_word_counter(notes)
  # send_text_to_word_counter("Hi")

if __name__ == "__main__":
  main()