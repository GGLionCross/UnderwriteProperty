import datetime
import json
import re
from decimal import Decimal
from re import sub
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from python_utils.functions import cprint, load_json
from python_utils.logging import setup_logging, get_line_number
from selenium_utils import Base, JavaScript, Wait

def main():
  setup_logging()

  def initialize_chrome_options():
    # Initialize special chrome options for selenium to utilize
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_experimental_option("detach", True) # Keep browser open after completion
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-site-isolation-trials")
    return chrome_options
  # end of initialize_chrome_options

  def initialize_chrome_webdriver(chrome_options):
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
  # end of initialize_chrome_webdriver

  config = load_json("config.json")

  #region Constants
  CURRENT_DATE = datetime.date.today().strftime('%m/%d/%y')  
  PROPERTY_ADDRESS = config["targets"]["property_address"]
  PROPSTREAM_EMAIL = config["propstream"]["email"]
  PROPSTREAM_PASSWORD = config["propstream"]["password"]
  PROPSTREAM_ZOOM = config["propstream"]["zoom"]
  COMPASS_EMAIL = config["compass"]["email"]
  COMPASS_PASSWORD = config["compass"]["password"]
  RENO_T1 = config["renovation"]["tier_1"]
  RENO_T1_5 = config["renovation"]["tier_1.5"]
  RENO_T2 = config["renovation"]["tier_2"]
  RENO_T2_5 = config["renovation"]["tier_2.5"]
  RENO_T3 = config["renovation"]["tier_3"]
  RENO_T3_5 = config["renovation"]["tier_3.5"]
  RENO_T1925 = config["renovation"]["tier_1925"]
  TIMEOUT_DEFAULT = config["timeouts"]["default"]
  TIMEOUT_LOGIN = config["timeouts"]["login"]
  TIMEOUT_SEARCH = config["timeouts"]["search"]
  URL_REDFIN = "https://www.redfin.com/"
  #endregion Constants

  cprint(f"<g>Underwriting {PROPERTY_ADDRESS}...")

  base = Base()
  driver = base.initialize_driver()
  actions = ActionChains(driver)
  wait = Wait(driver, TIMEOUT_DEFAULT)
  js = JavaScript(driver)

  def switch_to_recently_opened_tab():
    driver.switch_to.window(driver.window_handles[len(driver.window_handles) - 1])
  # end of switch_to_recently_opened_tab

  def sign_into_propstream(email, password):
    # Autofill email and password fields.
    wait.until_clickable((By.CSS_SELECTOR, "input[name='username']"))
    if (email):
      input_email_css = "input[name='username']"
      input_email = driver.find_element(By.CSS_SELECTOR, input_email_css)
      input_email.send_keys(email)
    if (password):
      input_password_css = "input[name='password']"
      input_password = driver.find_element(By.CSS_SELECTOR, input_password_css)
      input_password.send_keys(password)
      submit_css = "button[type='submit']"
      submit = driver.find_element(By.CSS_SELECTOR, submit_css)
      submit.click()
    # Wait until property address field after login is clickable
    input_css = "input[placeholder='Enter County, City, Zip Code(s) or APN #']"
    wait.for_element_located((By.CSS_SELECTOR, input_css), TIMEOUT_LOGIN)
  # end of sign_into_propstream

  def get_info_from_propstream(property_address):
    # Once in PropStream, look up property address and grab all important information
    # Search address
    input_placeholder = "Enter County, City, Zip Code(s) or APN #"
    input_xpath = f"//input[@placeholder='{input_placeholder}']"
    input = wait.until_clickable((By.XPATH, input_xpath))
    input.send_keys(property_address)
    
    try:
      # Click Details button
      details_xpath = "//span[text()='Details']"
      details = wait.for_element_located((By.XPATH, details_xpath), TIMEOUT_SEARCH)
      actions.move_to_element(details).perform()
      details.click()
    except TimeoutException:
      pass

    # Grab owner and mortgage info
    owner_xpath = "//div[text()='Owner 1 Name']/following-sibling::div"
    owner = wait.for_element_located((By.XPATH, owner_xpath), TIMEOUT_SEARCH)
    owner = owner.text
    mortgage_xpath = "//div[text()='Est. Mortgage Balance']/preceding-sibling::div"
    mortgage = driver.find_element(By.XPATH, mortgage_xpath).text
    comps_tab_xpath = "//div[text()='Comparables & Nearby Listings']"
    comps_tab = driver.find_element(By.XPATH, comps_tab_xpath)
    comps_tab.click()

    # Grab Distressed Condition
    # We don't want to waste our time with bank-owned properties.
    distressed_xpath = "//div[contains(text(),'Distressed')]/following-sibling::div"
    distressed = driver.find_element(By.XPATH, distressed_xpath).text

    # Grab Distressed Condition
    # We don't want to waste our time with bank-owned properties.
    owner_status_xpath = "//div[contains(text(),'Owner Status')]/following-sibling::div"
    owner_status = driver.find_element(By.XPATH, owner_status_xpath).text

    # Filter by year built
    year_built_xpath = "//div[contains(text(),'Year Built')]/following-sibling::div"
    year_built = wait.for_element_located((By.XPATH, year_built_xpath))
    actions.move_to_element(year_built).perform()
    if (year_built.text):
      year_built = int(year_built.text)
      input_min_xpath = "//input[@name='yearBuiltMin']"
      input_min = driver.find_element(By.XPATH, input_min_xpath)
      input_min.send_keys(year_built - 10)
      input_max_xpath = "//input[@name='yearBuiltMax']"
      input_max = driver.find_element(By.XPATH, input_max_xpath)
      input_max.send_keys(year_built + 10)

    # Grab square footage
    sqft_xpath = "//div[contains(text(),'SqFt')]/following-sibling::div"
    square_footage = driver.find_element(By.XPATH, sqft_xpath)
    if (square_footage.text):
      square_footage = int(square_footage.text.replace(",", ""))

    # Grab year built
    year_built = driver.find_element(By.XPATH, "//div[contains(text(),'Year Built')]/following-sibling::div")
    if (year_built.text):
      year_built = int(year_built.text.replace(",", ""))
    else:
      year_built = ""

    # Filter by public record
    public_record = driver.find_element(By.XPATH, "//span[text()='Public Record']/preceding-sibling::input")
    driver.execute_script("arguments[0].click()", public_record)

    # Setting Sale Date Min doesn't work because date picker is finicky
    #sale_date_min = driver.find_element(By.CSS_SELECTOR, "input[name='saleDateMin']")
    #three_months_ago = (datetime.today() - relativedelta(months=3)).replace(day=1).strftime("%m/%d/%Y")
    #sale_date_min.clear()
    #sale_date_min.send_keys(three_months_ago)
    
    # Grab all comps and take the average
    # #e4f3e6 is the light green that indicates public record
    avg_sale_price_xpath = "//div[contains(text(), 'Avg. Sale Price:')]"
    try:
      avg_sale_price = driver.find_element(By.XPATH, avg_sale_price_xpath).text
      price_regex = r"(\$[\d,]*)"
      price_match = re.search(price_regex, avg_sale_price)
      avg_sale_price = Decimal(sub(r"[^\d.]", "", price_match.group(1)))
    except:
      avg_sale_price = "N/A"

    return {
      "owner": owner,
      "mortgage": mortgage,
      "square_footage": square_footage,
      "distressed": distressed,
      "owner_status": owner_status,
      "year_built": year_built,
      "average_sale_price": avg_sale_price
    }
  # end of get_info_from_propstream

  def sign_into_compass(email, password):
    log_in = wait.for_element_located((By.CSS_SELECTOR, "button[data-label='Log In']"), TIMEOUT_SEARCH)
    log_in.click()
    driver.implicitly_wait(TIMEOUT_DEFAULT)
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
    WebDriverWait(driver, TIMEOUT_LOGIN).until(EC.staleness_of(forgot_password))
  # end of sign_into_compass

  def get_info_from_compass(property_address):
    search = wait.until_clickable((By.CSS_SELECTOR, "input[aria-describedBy='location-lookup-input-description']"))
    search.click()
    search.send_keys(property_address)
    try:
      mls_number = wait.for_element_located((By.XPATH, "//th[text()='MLS #']/following-sibling::td")).text
    except TimeoutException:
      return 1
    try:
      try:
        remarks = driver.find_element(By.XPATH, "//div[contains(@class, 'textIntent-body')]/div/span[2]").get_attribute("textContent")
      except Exception as e:
        cprint(f"<r>{e}\n<y>Line {get_line_number()}")
        remarks = driver.find_element(By.XPATH, "//div[contains(@class, 'textIntent-body')]/div/span").text
    except Exception as e:
      cprint(f"<r>{e}\n<y>Line {get_line_number()}")
      remarks = "Didn't find on Compass"

    # Get Listing Agent Info
    try:
      listing_agent_xpath = "//div[contains(@class, 'contact-agent')]/p[1]"
      listing_agent = driver.find_element(By.XPATH, listing_agent_xpath).text

      listing_brokerage_xpath = "//div[contains(@class, 'contact-agent')]/p[2]"
      listing_brokerage = driver.find_element(By.XPATH, listing_brokerage_xpath).text

      listing_agent_dre_xpath = "//div[contains(@class, 'contact-agent')]/p[contains(text(), 'DRE #')]"
      listing_agent_dre = driver.find_element(By.XPATH, listing_agent_dre_xpath).text

      listed_by = f"{listing_brokerage}, {listing_agent}, {listing_agent_dre}"

      listing_agent_phone_xpath = "//div[contains(@class, 'contact-agent')]/div/p[contains(text(), 'P:')]"
      listing_agent_phone = driver.find_element(By.XPATH, listing_agent_phone_xpath).text
      phone_regex = r".*(\d{3})\.(\d{3})\.(\d{4})"
      listing_agent_phone = re.sub(phone_regex, r"(\1) \2-\3", listing_agent_phone)

      listing_agent_email_xpath = "//div[contains(@class, 'contact-agent')]/a[contains(@href, 'mailto')]"
      listing_agent_email = driver.find_element(By.XPATH, listing_agent_email_xpath).text
    except:
      try:
        courtesy_xpath = "//span[@data-tn='courtesy-of-text']"
        courtesy = driver.find_element(By.XPATH, courtesy_xpath).text
        listed_by = sub("Listing Courtesy of ", "", courtesy)
      except:
        listed_by = "Didn't find on Compass"

      listing_agent_phone = "Didn't find on Compass"
      listing_agent_email = "Didn't find on Compass"
    
    # Get Ask Price
    try:
      ask_price = driver.find_element(By.XPATH, "//div[text()='Price']//preceding-sibling::div").text
    except Exception as e:
      cprint(f"<r>{e}\n<y>Line {get_line_number()}")
      ask_price = "Didn't find on Compass"
    try:
      days_on_market = "Days on Compass: " + driver.find_element(By.XPATH, "//th[text()='Days on Compass']/following-sibling::td").text
    except NoSuchElementException:
      days_on_market = "Days on Compass: N/A"
    try:
      pool = driver.find_element(By.XPATH, "//div[contains(text(), 'Pool')]/span").text
    except NoSuchElementException:
      pool = "Didn't find on Compass"
    return {
      "mls_number": mls_number,
      "remarks": remarks,
      "listed_by": listed_by,
      "listing_agent_phone": listing_agent_phone,
      "listing_agent_email": listing_agent_email,
      "ask_price": ask_price,
      "days_on_market": days_on_market,
      "pool": pool,
      "pictures": driver.current_url
    }
  # end of get_info_from_compass

  def get_info_from_redfin(property_address):
    driver.get("https://www.google.com/")
    search = driver.find_element(By.CSS_SELECTOR, "input[title='Search']")
    search.send_keys(f"redfin {property_address}")
    driver.find_element(By.CSS_SELECTOR, "input[value='Google Search']").submit()
    try:
      redfin_link = driver.find_element(By.CSS_SELECTOR, f"a[href*='{URL_REDFIN}']")
      redfin_link.click()
    except Exception as e:
      cprint(f"<r>{e}\n<y>Line {get_line_number()}")
      return 1
    try:
      mls_number = wait.for_element_located((By.XPATH, "//div[contains(@class, 'sourceContent')]/span[2]")).text
    except Exception as e:
      cprint(f"<r>{e}\n<y>Line {get_line_number()}")
      return 1
    try:
      remarks = driver.find_element(By.XPATH, "//div[contains(@class, 'remarks')]/p/span").text
    except Exception as e:
      cprint(f"<r>{e}\n<y>Line {get_line_number()}")
      remarks = "Couldn't locate on Redfin"
    
    # Get Listing Agent Info
    try:
      listing_agent_xpath = "//span[contains(text(), 'Listed by')]/span[1]"
      listing_agent = driver.find_element(By.XPATH, listing_agent_xpath).text
      listing_brokerage_xpath = "//span[contains(text(), 'Listed by')]/span[3]"
      listing_brokerage = driver.find_element(By.XPATH, listing_brokerage_xpath).text
      listing_agent_dre_xpath = "//span[contains(text(), 'Listed by')]/span[2]"
      listing_agent_dre = driver.find_element(By.XPATH, listing_agent_dre_xpath).text
      listed_by = f"{listing_brokerage}, {listing_agent}, {listing_agent_dre}"
    except:
      listed_by = "Didn't find on Redfin"

    # Get Ask Price
    try:
      ask_price = driver.find_element(By.XPATH, "//div[contains(@class, 'statsValue')]").text
    except Exception as e:
      cprint(f"<r>{e}\n<y>Line {get_line_number()}")
      ask_price = "Didn't find on Redfin"
    
    # Get Time on Redfin
    try:
      days_on_market_xpath = "//span[contains(text(), 'Time on Redfin')]/ancestor::span[contains(@class,'header')]/following-sibling::span"
      days_on_market = "Time on Redfin: " + driver.find_element(By.XPATH, days_on_market_xpath).text
    except Exception as e:
      cprint(f"<r>{e}\n<y>Line {get_line_number()}")
      days_on_market = "Time on Redfin: Could not find Time on Redfin"
    pictures = driver.current_url
    return {
      "mls_number": mls_number,
      "remarks": remarks,
      "listed_by": listed_by,
      "listing_agent_phone": "Redfin doesn't show this info",
      "listing_agent_email": "Redfin doesn't show this info",
      "ask_price": ask_price,
      "days_on_market": days_on_market,
      "pool": "Redfin doesn't list pool status",
      "pictures": pictures
    }
  # end of get_info_from_redfin

  driver.get("https://login.propstream.com/")
  sign_into_propstream(PROPSTREAM_EMAIL, PROPSTREAM_PASSWORD)
  propstream_info = get_info_from_propstream(PROPERTY_ADDRESS)
  if (PROPSTREAM_ZOOM):
    driver.execute_script(f"document.body.style.zoom='{PROPSTREAM_ZOOM}%'")

  driver.execute_script("window.open('https://www.compass.com/');")
  switch_to_recently_opened_tab()
  sign_into_compass(COMPASS_EMAIL, COMPASS_PASSWORD)
  listing_info = get_info_from_compass(PROPERTY_ADDRESS)
  if listing_info == 1:
    listing_info = get_info_from_redfin(PROPERTY_ADDRESS)
  if listing_info == 1:
    listing_info = {
      "mls_number": "Couldn't find on Compass or Redfin",
      "remarks": "Couldn't find on Compass or Redfin",
      "listed_by": "Couldn't find on Compass or Redfin",
      "listing_agent_phone": "Couldn't find on Compass or Redfin",
      "listing_agent_email": "Couldn't find on Compass or Redfin",
      "ask_price": "Couldn't find on Compass or Redfin",
      "days_on_market": "DOM: Couldn't find on Compass or Redfin",
      "pool": "Couldn't find on Compass or Redfin",
      "pictures": "Couldn't find on Compass or Redfin"
    }

  notes = PROPERTY_ADDRESS + "\n"
  notes += f"-MLS #: {listing_info['mls_number']}\n"
  notes += f"-{listing_info['days_on_market']} as of {CURRENT_DATE}\n"
  notes += f"-Listed by: {listing_info['listed_by']}\n"
  notes += f"-Agent's Phone: {listing_info['listing_agent_phone']}\n"
  notes += f"-Agent's Email: {listing_info['listing_agent_email']}\n"
  notes += f"-Owner: {propstream_info['owner']}\n"
  notes += f"-Owner Status: {propstream_info['owner_status']}\n"
  notes += f"-Distressed: {propstream_info['distressed']}\n"
  notes += f"-Year Built: {propstream_info['year_built']}\n"
  notes += f"-Pool: {listing_info['pool']}\n"
  notes += f"Pictures: {listing_info['pictures']}\n"
  notes += "Listing Remarks:\n"
  notes += f"\"{listing_info['remarks']}\"\n\n"

  if propstream_info['average_sale_price'] != "N/A":
    avg_sale_price = "${:,.2f}".format(propstream_info['average_sale_price'])
    avg_sale_price_multiply = "${:,.2f}".format(propstream_info['average_sale_price'] * Decimal('0.6'))
    notes += "Quick Check:\n"
    notes += f"-Average Market Sale Price: {avg_sale_price}\n"
    notes += f"-Price * 60%: {avg_sale_price_multiply}\n\n"

  notes += f"*ORIGINAL {CURRENT_DATE}*\n"
  notes += f"Asking Price {listing_info['ask_price']}\n"
  notes += "ARV \n"
  notes += "Repairs \n"
  notes += "Your Fee $15,000\n"
  notes += "Credit to your buyer $0\n"
  notes += "Wholesale Discount 80%\n"
  notes += "MAO Wholesale \n"
  notes += "% of ARV \n"
  notes += "Amount under asking \n"
  notes += f"Est. Mortgage {propstream_info['mortgage']}\n"
  notes += "Seller Profit Est \n"

  notes += "\n"

  notes += "Comp:\n"
  notes += "-#### Street\n"
  notes += "-Sold on mm/dd/yy for $___k\n"
  notes += "-Pool: \n"
  notes += "Compass link\n\n"

  notes += "ARV Adjustments:\n"
  notes += "-Comp Sold For: \n"
  notes += "-Comp PPSF: $___.__\n"
  notes += "-Subj Adj ARV: $___k\n"
  notes += "-Market Adjustment (-10%): $__k\n"
  notes += "-Comp has extra bed: -$10k\n"
  notes += "-Comp has extra bath: -$10k\n"
  notes += "Final ARV (rounded down): \n\n"

  tier_1 = '${:,}'.format(propstream_info['square_footage'] * RENO_T1)
  tier_1_5 = '${:,}'.format(propstream_info['square_footage'] * RENO_T1_5)
  tier_2 = '${:,}'.format(propstream_info['square_footage'] * RENO_T2)
  tier_2_5 = '${:,}'.format(propstream_info['square_footage'] * RENO_T2_5)
  tier_3 = '${:,}'.format(propstream_info['square_footage'] * RENO_T3)
  tier_3_5 = '${:,}'.format(propstream_info['square_footage'] * RENO_T3_5)
  tier_1925 = '${:,}'.format(propstream_info['square_footage'] * RENO_T1925)


  notes += "Reno:\n"
  notes += f"-Tier 1 (${RENO_T1}/sf): {tier_1} on {'{:,}'.format(propstream_info['square_footage'])}sf\n"
  notes += f"-Tier 1.5 (${RENO_T1_5}/sf): {tier_1_5} on {'{:,}'.format(propstream_info['square_footage'])}sf\n"
  notes += f"-Tier 2 (${RENO_T2}/sf): {tier_2} on {'{:,}'.format(propstream_info['square_footage'])}sf\n"
  notes += f"-Tier 2.5 (${RENO_T2_5}/sf): {tier_2_5} on {'{:,}'.format(propstream_info['square_footage'])}sf\n"
  notes += f"-Tier 3 (${RENO_T3}/sf): {tier_3} on {'{:,}'.format(propstream_info['square_footage'])}sf\n"
  notes += f"-Tier 3.5 (${RENO_T3_5}/sf): {tier_3_5} on {'{:,}'.format(propstream_info['square_footage'])}sf\n"

  year_built = propstream_info['year_built']
  if year_built == "" or year_built <= 1925:
    notes += f"-Year Built <= 1925 (${RENO_T1925}/sf): {tier_1925} on {'{:,}'.format(propstream_info['square_footage'])}sf\n"
  
  notes += "Final Reno Est (rounded up): $___k\n"

  with open(f"../underwriting/{PROPERTY_ADDRESS}.txt", "w", encoding="utf-8") as f:
    f.write(notes)

if __name__ == "__main__":
  main()