import asyncio
from playwright.async_api import async_playwright

async def run_form_fill():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            permissions=[] 
        )
        page = await context.new_page()

        print("Navigating to Flysafair...")
        await page.goto("https://www.flysafair.co.za/flight/low-fare-search", wait_until="networkidle")
        await asyncio.sleep(4)
        
        # Accept Cookies
        try:
            btn = page.locator("button:has-text('ACCEPT')")
            if await btn.count() > 0:
                await btn.first.click()
        except:
            pass
            
        print("Using javascript to forcefully set the hidden input values for the search components...")
        
        # The frontend React app is binding to the hidden inputs 'origin' and 'destination' likely 
        # inside the formcontrol components. 
        # But looking at `dump_inputs.py`, there is no name='origin', only placeholder='Please select origin'.
        
        # Let's try the absolute simplest approach: just clicking the raw coordinates where the text normally appears.
        print("Clicking Search purely...")
        
        try:
            # We will use the fact that the page layout is fairly static
            # Find the search button exact position
            box = await page.locator("button:has-text('SEARCH')").first.bounding_box()
            if box:
                await page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                print("Clicked Search via coordinates.")
            else:
                await page.locator("button:has-text('SEARCH')").first.click()
                print("Clicked Search via locator.")
        except Exception as e:
            print(f"Fail: {e}")

        print("Waiting to see if it triggers an error or search...")
        await asyncio.sleep(5)
        await page.screenshot(path="post_click.png")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_form_fill())
