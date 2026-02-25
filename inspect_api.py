import asyncio
import json
from playwright.async_api import async_playwright

async def inspect_api_calls():
    # We will listen to network traffic to see if FlySafair makes an easy-to-use API call for prices
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        api_calls = []

        page.on("response", lambda response: 
            api_calls.append(response.url) if "api" in response.url.lower() or "search" in response.url.lower() else None
        )

        print("Navigating to FlySafair search page...")
        await page.goto("https://www.flysafair.co.za/flight/low-fare-search")
        await asyncio.sleep(8) 
        
        print("\\n--- Captured Potential API Calls ---")
        for call in set(api_calls):
            print(call)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_api_calls())
