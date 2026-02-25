import asyncio
from playwright.async_api import async_playwright
import urllib.parse
import json

async def capture_api_headers():
    # To use `requests`, we often need correct Headers, Cookies and Tokens.
    # FlySafair likely uses a bearer token or specific cookies generated on the homepage.
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            permissions=[] 
        )
        page = await context.new_page()

        print("Navigating to FlySafair search page...")
        await page.goto("https://www.flysafair.co.za/flight/low-fare-search", wait_until="networkidle")
        await asyncio.sleep(5) 
        
        # Grab cookies
        cookies = await context.cookies()
        
        # Grab local storage for tokens
        local_storage = await page.evaluate("() => JSON.stringify(window.localStorage)")
        session_storage = await page.evaluate("() => JSON.stringify(window.sessionStorage)")

        import pprint
        print("\\n--- Context Dump ---")
        print(f"Cookies Count: {len(cookies)}")
        
        ls_data = json.loads(local_storage)
        print("\\nLocal Storage Keys:")
        for key in ls_data.keys():
            print(f"  - {key}")
            if "token" in key.lower() or "auth" in key.lower():
                print(f"    Value: {ls_data[key][:50]}...")
                
        ss_data = json.loads(session_storage)
        print("\\nSession Storage Keys:")
        for key in ss_data.keys():
            print(f"  - {key}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(capture_api_headers())
