import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timedelta

async def scrape_via_url_injection():
    # Bypass the search form and go directly to the results page
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            permissions=[] 
        )
        page = await context.new_page()
        
        target_date = datetime.now() + timedelta(days=14)
        date_str = target_date.strftime("%Y-%m-%d")
        
        # Direct search URL used by Flysafair SPA routing
        search_url = f"https://www.flysafair.co.za/flight/search?origin=GRJ&destination=JNB&departureDate={date_str}&adult=1&child=0&infant=0"

        print(f"Navigating to injected URL: {search_url}...")
        await page.goto(search_url, wait_until="networkidle")
        
        print("Waiting for elements to load...")
        await asyncio.sleep(10) # Let the React search finish in the background
        
        # Take a full page screenshot
        await page.screenshot(path="search_results.png", full_page=True)
        print("Saved search results screenshot to search_results.png")
        
        # Dump the text so we can see what the flight rows look like
        page_text = await page.evaluate("document.body.innerText")
        with open("search_results_text.txt", "w", encoding="utf-8") as f:
            f.write(page_text)
        print("Saved visible text to search_results_text.txt")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(scrape_via_url_injection())
