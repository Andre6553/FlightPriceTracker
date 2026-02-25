import asyncio
import json
from playwright.async_api import async_playwright

async def get_flight_data_api():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        # Block geolocation and notifications to avoid browser popups
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            permissions=[] 
        )
        page = await context.new_page()

        api_responses = []

        async def handle_response(response):
            if "api-production-safair" in response.url and "Search" in response.url:
                try:
                    data = await response.json()
                    api_responses.append(data)
                    print(f"\\n>>> Intercepted Flight Data API from {response.url}")
                except Exception as e:
                    pass

        page.on("response", handle_response)

        print("Navigating to FlySafair search page...")
        await page.goto("https://www.flysafair.co.za/flight/low-fare-search")
        await asyncio.sleep(5) 
        
        # 1. Handle the Cookie popup if it exists
        print("Checking for cookie popup...")
        try:
            accept_btn = page.get_by_role("button", name="ACCEPT")
            if await accept_btn.count() > 0:
                print("Clicking ACCEPT on cookie banner.")
                await accept_btn.first.click()
                await asyncio.sleep(2)
        except Exception as e:
            print(f"No cookie banner found or failed to click: {e}")

        print("Simulating a search via UI clicks to trigger the API request...")
        try:
            # Fly out date default is fine for a test, we just want to trigger the search.
            
            print("Clicking Origin...")
            origin_input = page.get_by_placeholder("Please select origin")
            await origin_input.click()
            await origin_input.fill("George")
            await asyncio.sleep(1)
            await page.keyboard.press("Enter")
            await asyncio.sleep(1)
            
            print("Clicking Destination...")
            dest_input = page.get_by_placeholder("Please select destination")
            await dest_input.click()
            await dest_input.fill("Johannesburg")
            await asyncio.sleep(1)
            await page.keyboard.press("Enter")
            await asyncio.sleep(1)
            
            print("Clicking Search...")
            await page.get_by_role("button", name="SEARCH").click()
            
            print("Waiting for results...")
            await asyncio.sleep(10)
            
            if api_responses:
                with open('api_data.json', 'w') as f:
                    json.dump(api_responses[0], f, indent=2)
                print("Saved API response to api_data.json")
            else:
                print("No API response intercepted. Capturing screenshot for debugging.")
                await page.screenshot(path="screenshot.png")
                
        except Exception as e:
            print(f"UI interaction failed: {e}")
            await page.screenshot(path="error_screenshot.png")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(get_flight_data_api())
