import asyncio
from playwright.async_api import async_playwright

async def test_flysafair_scrape():
    async with async_playwright() as p:
        # Launch visible browser for debugging
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("Navigating to FlySafair search page...")
        await page.goto("https://www.flysafair.co.za/flight/low-fare-search")
        
        # Wait a bit
        await asyncio.sleep(5)
        
        # Output title to ensure we're there
        print(f"Page title: {await page.title()}")

        # Let's see if we hit a captcha or cloudflare
        content = await page.content()
        if "captcha" in content.lower() or "cloudflare" in content.lower():
            print("Hit bot protection.")
        else:
            print("Page loaded successfully.")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_flysafair_scrape())
