import asyncio
from playwright.async_api import async_playwright

async def debug_ui():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            permissions=[] 
        )
        page = await context.new_page()

        print("Navigating to FlySafair search page...")
        await page.goto("https://www.flysafair.co.za/flight/low-fare-search", wait_until="networkidle")
        
        print("Dumping page text...")
        page_text = await page.evaluate("document.body.innerText")
        
        with open("page_text.txt", "w", encoding="utf-8") as f:
            f.write(page_text)
            
        print("Saved visible text to page_text.txt")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_ui())
