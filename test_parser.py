import sys
import asyncio
from playwright.async_api import async_playwright
import re

async def run_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=['--disable-notifications'])
        context = await browser.new_context(viewport={"width": 1400, "height": 900})
        page = await context.new_page()

        # 1. Load Calendar
        print("Navigating...")
        await page.goto("https://www.flysafair.co.za/flight/low-fare-search", wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(8)
        
        # Accept cookies
        cookie_btn = page.locator("button#onetrust-accept-btn-handler, button:has-text('Accept All')")
        if await cookie_btn.count() > 0:
            await cookie_btn.first.click()
            await asyncio.sleep(1)
            
        # One Way
        await page.locator("label[for='oneway']").click()
        await asyncio.sleep(1)
        
        # Origin (GRJ)
        await page.locator("input.vs__search").first.click()
        await asyncio.sleep(0.5)
        await page.locator("input.vs__search").first.fill("George")
        await asyncio.sleep(1)
        await page.locator("li.vs__dropdown-option:has-text('George')").first.click()
        await asyncio.sleep(1)
        
        # Dest (JNB)
        dest_input = page.locator("input.vs__search").nth(1)
        await dest_input.wait_for(state="visible")
        await dest_input.click(force=True)
        await asyncio.sleep(0.5)
        await dest_input.fill("Johannesburg")
        await asyncio.sleep(1)
        await page.locator("li.vs__dropdown-option:has-text('Johannesburg')").filter(has_text=re.compile(r'JNB')).first.click()
        await asyncio.sleep(1)
        
        # Search
        await page.locator("button.lfm-search-flights__btn").click()
        await asyncio.sleep(8)
        
        # 2. Go to April
        for _ in range(2): # Feb -> Mar -> Apr
            next_btn = page.locator("button.lfm-navigation__next-month")
            if await next_btn.count() > 0:
                await next_btn.first.click(force=True)
                await asyncio.sleep(3)
        
        # Click 14
        day_locator = page.locator(f"button.lowest-fare-day:has(.lowest-fare-day__day:text-is('14'))")
        
        if await day_locator.count() > 0:
            await day_locator.first.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            await day_locator.first.click(force=True)
        else:
            print("Day 14 not found!")
            await browser.close()
            return

        await asyncio.sleep(2)
        
        # Continue
        continue_btn = page.locator("button:has-text('CONTINUE'), a:has-text('CONTINUE')")
        if await continue_btn.count() > 0:
            await continue_btn.first.click()
            await asyncio.sleep(8)
        
        # Get body text
        body_text = await page.inner_text("body")
        with open("details_dump.txt", "w", encoding="utf-8") as f:
            f.write(body_text)
            
        print("Done. Saved details_dump.txt")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_test())
