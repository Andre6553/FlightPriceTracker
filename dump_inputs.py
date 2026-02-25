import asyncio
from playwright.async_api import async_playwright

async def dump_inputs():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            permissions=[] 
        )
        page = await context.new_page()

        print("Navigating to FlySafair search page...")
        await page.goto("https://www.flysafair.co.za/flight/low-fare-search", wait_until="networkidle")
        await asyncio.sleep(5) 
        
        # 1. Handle Cookie popup
        try:
            accept_btn = page.get_by_role("button", name="ACCEPT")
            if await accept_btn.count() > 0:
                await accept_btn.first.click()
                await asyncio.sleep(2)
        except:
            pass
            
        print("Dumping interactive elements...")
        
        # Extract inputs and select fields
        elements_info = await page.evaluate('''() => {
            const els = document.querySelectorAll('input, select, button, mat-select, [role="button"], [role="combobox"]');
            return Array.from(els).map(el => {
                return {
                    tagName: el.tagName,
                    id: el.id,
                    name: el.name,
                    type: el.type,
                    value: el.value || '',
                    placeholder: el.placeholder || '',
                    ariaLabel: el.getAttribute('aria-label') || '',
                    innerText: el.innerText ? el.innerText.trim().substring(0, 30) : '',
                    formcontrolname: el.getAttribute('formcontrolname') || ''
                };
            });
        }''')
        
        for i, el in enumerate(elements_info):
            if any([el['id'], el['name'], el['placeholder'], el['formcontrolname'], el['innerText']]):
                print(f"{i}. <{el['tagName']}> | ID: '{el['id']}' | Name: '{el['name']}' | Placeholder: '{el['placeholder']}' | formcontrol: '{el['formcontrolname']}' | Text: '{el['innerText']}'")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(dump_inputs())
