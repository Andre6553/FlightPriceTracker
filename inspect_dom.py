import asyncio
from playwright.async_api import async_playwright

async def inspect_full_dom():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("Navigating to FlySafair search page...")
        await page.goto("https://www.flysafair.co.za/flight/low-fare-search")
        await asyncio.sleep(8) # Let dynamic Elements completely load
        
        # Save entire DOM to file for inspection
        content = await page.content()
        with open("flysafair_dom.html", "w", encoding="utf-8") as f:
            f.write(content)
        print("Saved DOM to flysafair_dom.html")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(inspect_full_dom())
