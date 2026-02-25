from seleniumwire.undetected_chromedriver.v2 import Chrome, ChromeOptions
import time
import json
from datetime import datetime, timedelta

def run_scraper_wire():
    options = ChromeOptions()
    options.headless = False 
    options.add_argument('--disable-popup-blocking')
    
    # Needs to match your installed Chrome version
    driver = Chrome(options=options) 
    
    target_date = datetime.now() + timedelta(days=14)
    date_str = target_date.strftime("%Y-%m-%d")
    search_url = f"https://www.flysafair.co.za/flight/search?origin=GRJ&destination=JNB&departureDate={date_str}&adult=1&child=0&infant=0"
    
    print(f"Navigating to {search_url}")
    driver.get(search_url)
    
    print("Waiting for 15 seconds to allow full render...")
    time.sleep(15)
    
    # Intercept API calls successfully made by the browser
    api_responses = []
    for request in driver.requests:
        if request.response and 'api-production-safair' in request.url and 'Search' in request.url:
            print(f">>> Found API Response: {request.url}")
            try:
                # Get the JSON response body
                body = request.response.body.decode('utf-8')
                data = json.loads(body)
                api_responses.append(data)
            except Exception as e:
                print(f"Error parsing response body: {e}")

    if api_responses:
        with open('api_data.json', 'w', encoding='utf-8') as f:
            json.dump(api_responses[0], f, indent=2)
        print("Saved API response to api_data.json!")
    else:
        print("No API response found in network traffic.")
        
    driver.quit()

if __name__ == "__main__":
    run_scraper_wire()
