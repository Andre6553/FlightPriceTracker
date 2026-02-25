import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time

def run_uc_interactive():
    options = uc.ChromeOptions()
    options.headless = False  
    options.add_argument('--disable-popup-blocking')
    
    print("Starting Chrome Scraper in interactive mode...")
    driver = uc.Chrome(options=options)
    driver.set_window_size(1280, 800)
    
    print("Navigating to FlySafair homepage...")
    driver.get("https://www.flysafair.co.za")
    
    wait = WebDriverWait(driver, 15)
    
    print("Waiting for 'Book a Flight' header...")
    try:
        # Wait until the page structure is generally loaded
        time.sleep(5)
        
        print("Checking for cookie popup...")
        try:
            btn = driver.find_element(By.XPATH, "//button[contains(text(), 'ACCEPT')]")
            btn.click()
            print("- Clicked Accept Cookies")
            time.sleep(2)
        except:
            pass
            
        print("Attempting to fill Origin...")
        origin_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Please select origin']")))
        origin_input.click()
        time.sleep(1)
        origin_input.send_keys("George")
        time.sleep(2) # Wait for drop-down to populate
        ActionChains(driver).send_keys(Keys.ARROW_DOWN).perform()
        time.sleep(1)
        ActionChains(driver).send_keys(Keys.ENTER).perform()
        time.sleep(1)
        driver.save_screenshot("step_1_origin.png")
        
        print("Attempting to fill Destination...")
        dest_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Please select destination']")))
        dest_input.click()
        time.sleep(1)
        dest_input.send_keys("Johannesburg")
        time.sleep(2)
        ActionChains(driver).send_keys(Keys.ARROW_DOWN).perform()
        time.sleep(1)
        ActionChains(driver).send_keys(Keys.ENTER).perform()
        time.sleep(1)
        driver.save_screenshot("step_2_destination.png")
        
        print("Clicking SEARCH...")
        # Find the Search button - FlySafair buttons often contain a span
        search_btn = driver.find_element(By.XPATH, "//button[contains(., 'SEARCH')]")
        
        # Scroll to it
        driver.execute_script("arguments[0].scrollIntoView(true);", search_btn)
        time.sleep(2)
        driver.save_screenshot("step_3_before_search.png")
        search_btn.click()
        
        print("Waiting 10 seconds for results to load...")
        time.sleep(10)
        
        driver.save_screenshot("uc_interactive_success.png")
        print("Saved screenshot to uc_interactive_success.png")

        body_text = driver.find_element(By.TAG_NAME, "body").text
        with open("uc_interactive_body.txt", "w", encoding="utf-8") as f:
            f.write(body_text)
            
        import re
        prices = re.findall(r'R\\s*(\\d{1,3}(?:,\\d{3})*)', body_text)
        if prices:
            print(f"Found potential prices: {prices[:10]}")
        else:
            print("Price regex found nothing.")
            
    except Exception as e:
        print(f"Interaction Error: {e}")
        driver.save_screenshot("uc_interactive_error.png")

    driver.quit()

if __name__ == "__main__":
    run_uc_interactive()
