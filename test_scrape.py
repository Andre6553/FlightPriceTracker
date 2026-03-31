import asyncio
from playwright.async_api import async_playwright

async def test_flysafair_scrape():
    import os
    async with async_playwright() as p:
        # Check environment or default to true for Linux
        is_headless = os.environ.get("HEADLESS", "True").lower() == "true"
        browser = await p.chromium.launch(headless=is_headless)
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
