import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime, timedelta

def run_uc_scraper():
    # Use undetected chromedriver to bypass Cloudflare / Akamai
    options = uc.ChromeOptions()
    options.headless = False  # Keep false for debugging first
    options.add_argument('--disable-popup-blocking')
    
    # Needs to match your installed Chrome version
    driver = uc.Chrome(options=options) 
    
    target_date = datetime.now() + timedelta(days=14)
    date_str = target_date.strftime("%Y-%m-%d")
    search_url = f"https://www.flysafair.co.za/flight/search?origin=GRJ&destination=JNB&departureDate={date_str}&adult=1&child=0&infant=0"
    
    print(f"Navigating to {search_url}")
    driver.get(search_url)
    
    print("Waiting for 15 seconds to allow full render and human passing checks...")
    time.sleep(15)
    
    # Take a screenshot to verify what UC sees
    driver.save_screenshot("uc_screenshot.png")
    print("Saved uc_screenshot.png")
    
    try:
        # Flysafair prices are usually in a specific container
        # Let's dump the whole body to inspect if it rendered
        body_text = driver.find_element(By.TAG_NAME, "body").text
        with open("uc_body.txt", "w", encoding="utf-8") as f:
            f.write(body_text)
        print("Saved body text to uc_body.txt")
        
        # Try to find price elements (typically R followed by numbers)
        import re
        prices = re.findall(r'R\s*\\d{3,4}', body_text)
        if prices:
            print(f"Found potential prices: {prices[:5]}")
            
    except Exception as e:
        print(f"Error extracting text: {e}")
        
    driver.quit()

if __name__ == "__main__":
    run_uc_scraper()
