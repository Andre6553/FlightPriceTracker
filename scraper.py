"""
FlySafair Price Scraper
Uses Playwright to navigate the Low Fare Finder page,
select routes, and extract the calendar grid prices for each month.
"""
import asyncio
from playwright.async_api import async_playwright
import time
import re
from datetime import datetime
from db_manager import init_db, save_flight_price, save_flight_detail
from pathlib import Path

# Routes to scrape — use airport codes in names to match the exact dropdown option
ROUTES = [
    {"from_name": "George", "from_code": "GRJ", "to_name": "Johannesburg", "to_code": "JNB", "to_match": "JNB"},
    {"from_name": "Johannesburg", "from_code": "JNB", "from_match": "JNB", "to_name": "George", "to_code": "GRJ"},
    {"from_name": "Cape Town", "from_code": "CPT", "to_name": "Johannesburg", "to_code": "JNB", "to_match": "JNB"},
    {"from_name": "Johannesburg", "from_code": "JNB", "from_match": "JNB", "to_name": "Cape Town", "to_code": "CPT"},
]

# How many months ahead to scrape (Feb-Oct 2026 = 8 months)
MONTHS_AHEAD = 8


async def accept_cookies(page):
    """Dismiss the cookie consent banner if present."""
    try:
        accept = page.locator("button:has-text('ACCEPT')")
        if await accept.count() > 0:
            await accept.first.click()
            await asyncio.sleep(1)
    except Exception:
        pass


async def select_one_way(page):
    """Click the 'One Way' radio button."""
    try:
        one_way = page.locator("label:has-text('One Way')")
        if await one_way.count() > 0:
            await one_way.first.click()
            await asyncio.sleep(1)
    except Exception:
        pass


async def fill_origin(page, city_name, match_code=None):
    """Fill the origin vue-select dropdown."""
    origin = page.get_by_placeholder("Please select origin")
    await origin.click()
    await asyncio.sleep(0.5)
    await origin.fill(city_name)
    await asyncio.sleep(1.5)  # Wait for dropdown, but click fast before it disappears

    # Use match_code (e.g. 'JNB') to pick the exact airport if specified
    search_text = match_code if match_code else city_name
    try:
        option = page.locator(f"li.vs__dropdown-option:has-text('{search_text}')")
        await option.first.click(timeout=3000)
    except Exception:
        try:
            option = page.locator(f"li[role='option']:has-text('{search_text}')")
            await option.first.click(timeout=3000)
        except Exception:
            await page.keyboard.press("ArrowDown")
            await asyncio.sleep(0.3)
            await page.keyboard.press("Enter")
    await asyncio.sleep(2)

    # Verify origin was selected by waiting for destination to become enabled
    try:
        await page.wait_for_selector(
            "input[placeholder='Please select destination']:not([disabled])",
            timeout=10000
        )
    except Exception:
        print("    Warning: destination still disabled after origin selection")


async def fill_destination(page, city_name, match_code=None):
    """Fill the destination vue-select dropdown."""
    dest = page.get_by_placeholder("Please select destination")
    await dest.click(force=True)
    await asyncio.sleep(0.5)
    await dest.fill(city_name)
    await asyncio.sleep(1.5)  # Click fast before dropdown disappears

    search_text = match_code if match_code else city_name
    try:
        option = page.locator(f"li.vs__dropdown-option:has-text('{search_text}')")
        await option.first.click(timeout=3000)
    except Exception:
        try:
            option = page.locator(f"li[role='option']:has-text('{search_text}')")
            await option.first.click(timeout=3000)
        except Exception:
            await page.keyboard.press("ArrowDown")
            await asyncio.sleep(0.3)
            await page.keyboard.press("Enter")
    await asyncio.sleep(1)


async def click_search(page):
    """Click the SEARCH button and wait for calendar to load."""
    search = page.locator("button:has-text('SEARCH')")
    await search.scroll_into_view_if_needed()
    await asyncio.sleep(0.5)
    await search.click()
    await asyncio.sleep(10)  # Wait for calendar to fully render


def extract_prices_from_text(body_text):
    """
    Parse calendar prices from the page body text.
    Calendar renders: "1\nR2369.83\n2\n...\n3\nR1069.82"
    """
    results = []
    price_pattern = re.findall(r'(\d{1,2})\s*\n\s*R([\d,]+\.\d{2})', body_text)
    for day_str, price_str in price_pattern:
        day = int(day_str)
        if 1 <= day <= 31:
            price = float(price_str.replace(',', ''))
            results.append({"day": day, "price": price})
    return results


def parse_month_year(month_text):
    """Parse 'March 2026' into (month, year)."""
    try:
        dt = datetime.strptime(month_text.strip(), "%B %Y")
        return dt.month, dt.year
    except Exception:
        return None, None


async def extract_calendar_data(page):
    """Extract month text and all prices from the departure calendar."""
    month_text = ""
    # Look for month headers - the departure calendar header contains "Month Year"
    month_names = ["January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    try:
        body_text = await page.inner_text("body")
        # Find the first "MonthName 20XX" pattern in the body text
        for line in body_text.split("\n"):
            line = line.strip()
            for m in month_names:
                if m in line and ("2025" in line or "2026" in line or "2027" in line):
                    month_text = line
                    break
            if month_text:
                break
    except Exception:
        body_text = ""

    if not body_text:
        body_text = await page.inner_text("body")
    prices = extract_prices_from_text(body_text)

    return month_text, prices


async def wait_for_prices_loaded(page, max_wait=15):
    """Wait until price elements appear on the calendar (up to max_wait seconds)."""
    for _ in range(max_wait):
        try:
            count = await page.evaluate("""
                () => {
                    const cells = document.querySelectorAll('.lfm-day-cell__price, .lfm-calendar__price');
                    if (cells.length > 0) return cells.length;
                    // Fallback: check for R-prefixed prices in calendar area
                    const body = document.body.innerText;
                    const matches = body.match(/R\\d[\\d,]*\\.\\d{2}/g);
                    return matches ? matches.length : 0;
                }
            """)
            if count >= 5:  # At least 5 prices visible = month is loaded
                return True
        except Exception:
            pass
        await asyncio.sleep(1)
    return False


async def navigate_next_month(page):
    """Click the next month arrow on the departure calendar. Retries up to 3 times."""
    for attempt in range(3):
        try:
            # First, scroll the calendar into view
            await page.evaluate("""
                () => {
                    const cal = document.querySelector('.lfm-navigation__next-month');
                    if (cal) cal.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            """)
            await asyncio.sleep(1)

            # Try Playwright click first
            next_btn = page.locator("button.lfm-navigation__next-month")
            if await next_btn.count() > 0:
                await next_btn.first.click(force=True)
                # Wait for prices to load instead of fixed sleep
                loaded = await wait_for_prices_loaded(page)
                if not loaded:
                    print(f"    -> Prices slow to load, waiting extra...")
                    await asyncio.sleep(5)
                return True

            # Fallback: JS click
            clicked = await page.evaluate("""
                () => {
                    const btn = document.querySelector('.lfm-navigation__next-month');
                    if (btn) { btn.click(); return true; }
                    return false;
                }
            """)
            if clicked:
                loaded = await wait_for_prices_loaded(page)
                if not loaded:
                    print(f"    -> Prices slow to load, waiting extra...")
                    await asyncio.sleep(5)
                return True

        except Exception as e:
            print(f"    -> Month nav attempt {attempt + 1}/3 failed: {e}")
            await asyncio.sleep(2)

    return False

async def find_cheapest_days(page):
    """Find the day numbers that have the cheapest (pink highlighted) price on the calendar."""
    try:
        cheapest_days = await page.evaluate("""
            () => {
                const days = [];
                // Pink cells have the 'lowest-fare-day--cheapest' class
                const cheapestCells = document.querySelectorAll('button.lowest-fare-day.lowest-fare-day--cheapest');
                for (const cell of cheapestCells) {
                    const dayEl = cell.querySelector('.lowest-fare-day__day');
                    if (dayEl) {
                        const day = parseInt(dayEl.textContent.trim());
                        if (day >= 1 && day <= 31) days.push(day);
                    }
                }
                
                // Fallback: if 'cheapest' class isn't used, fallback to the old method
                if (days.length === 0) {
                    const allCells = document.querySelectorAll('button.lowest-fare-day');
                    for (const cell of allCells) {
                        const style = window.getComputedStyle(cell);
                        const bg = style.backgroundColor;
                        const isPink = bg.includes('233') || bg.includes('255, 64') || bg.includes('rgb(236');
                        
                        if (isPink) {
                            const dayEl = cell.querySelector('.lowest-fare-day__day');
                            if (dayEl) {
                                const day = parseInt(dayEl.textContent.trim());
                                if (day >= 1 && day <= 31) days.push(day);
                            }
                        }
                    }
                }
                
                return [...new Set(days)]; // deduplicate
            }
        """)
        return cheapest_days
    except Exception as e:
        print(f"    -> Error finding cheapest days: {e}")
        return []


async def extract_flight_details_page(page):
    """Extract flight details from the flight selection page using DOM evaluation."""
    try:
        await asyncio.sleep(4)  # Let the page fully load
        
        flights = await page.evaluate("""
            () => {
                const flights = [];
                // Find all elements that might contain a price (buttons or spans)
                const priceElements = Array.from(document.querySelectorAll('button, span, div, p')).filter(el => {
                    // Only check elements that have no children (leaf nodes) OR are buttons
                    if (el.children.length === 0 || el.tagName === 'BUTTON') {
                        return el.textContent && el.textContent.match(/R\\s*[\\d,]+\\.\\d{2}/);
                    }
                    return false;
                });

                for (const el of priceElements) {
                    const priceMatch = el.textContent.match(/R\\s*([\\d,]+\\.\\d{2})/);
                    if (!priceMatch) continue;
                    
                    let price = parseFloat(priceMatch[1].replace(/,/g, ''));
                    if (price <= 0) continue; // Ignore R 0.00 balances in the sidebar widget
                    
                    // Walk up the DOM to find the parent row containing the flight number
                    let row = el.parentElement;
                    let flightNum = null;
                    let depTime = null;
                    let arrTime = null;
                    let isSpecial = false;
                    
                    for (let i = 0; i < 10 && row; i++) {
                        if (row.tagName === 'BODY' || row.tagName === 'HTML' || row.tagName === 'MAIN') break;
                        
                        const text = row.innerText || row.textContent || "";
                        const faMatches = text.match(/(?:FA)\\s*\\d+/g);
                        
                        if (faMatches) {
                            // Find unique flight numbers within this DOM container
                            const uniqueFlights = [...new Set(faMatches.map(f => f.replace(/\\s+/, ' ').trim()))];
                            
                            if (uniqueFlights.length === 1) {
                                // Perfect! This container only describes ONE flight.
                                flightNum = uniqueFlights[0];
                                const times = text.match(/(\\d{2}:\\d{2})/g);
                                if (times && times.length >= 2) {
                                    depTime = times[0];
                                    arrTime = times[1];
                                }
                                isSpecial = text.includes("SPECIAL") || text.includes("EXCLUSIVE");
                                break;
                            } else if (uniqueFlights.length > 1) {
                                // Uh oh, we've climbed too high and reached a container with multiple flights.
                                // We shouldn't assign this price to all of them, so we stop climbing.
                                break;
                            }
                        }
                        row = row.parentElement;
                    }
                    
                    if (flightNum && price > 0) {
                        flights.push({
                            flight_number: flightNum,
                            departure_time: depTime || "unknown",
                            arrival_time: arrTime || "unknown",
                            price: price,
                            is_special: isSpecial
                        });
                    }
                }
                
                // Deduplicate: Keep only the lowest fare for each distinct flight number
                const flightMap = {};
                for (const f of flights) {
                    if (!flightMap[f.flight_number] || f.price < flightMap[f.flight_number].price) {
                        flightMap[f.flight_number] = f;
                    }
                }
                
                return Object.values(flightMap);
            }
        """)
        
        return flights
        
    except Exception as e:
        print(f"    -> Error extracting flight details: {e}")
        return []


async def capture_cheapest_flight_details(page, route_str, month_text, month_num, year_num, 
                                           today, scrape_dt, cheapest_days, route_info):
    """Click on cheapest day(s), hit Continue, extract flights, save to DB, navigate back."""
    if not cheapest_days or not month_num or not year_num:
        return 0
    
    total_saved = 0
    
    for day in cheapest_days:
        try:
            flight_date = datetime(year_num, month_num, day)
            flight_date_str = flight_date.strftime("%Y-%m-%d")
            days_before = (flight_date - today).days
            if days_before < 0:
                continue
        except ValueError:
            continue
        
        try:
            print(f"    -> Clicking cheapest day {day} ({month_text})...")
            
            # 1. Reload the calendar fresh for each day to ensure clean DOM
            await page.goto("https://www.flysafair.co.za/flight/low-fare-search", wait_until="domcontentloaded", timeout=60000)
            await asyncio.sleep(8)
            await accept_cookies(page)
            await select_one_way(page)
            await fill_origin(page, route_info['from_name'], route_info.get('from_match'))
            await fill_destination(page, route_info['to_name'], route_info.get('to_match'))
            await click_search(page)
            
            # 2. Navigate to the correct month
            # Calculate how many next clicks we need from the current month
            # Assume we always start at current month
            start_date = today
            target_date = datetime(year_num, month_num, 1)
            months_diff = (target_date.year - start_date.year) * 12 + target_date.month - start_date.month
            
            for _ in range(months_diff):
                if not await navigate_next_month(page):
                    print(f"    -> Could not navigate to {month_text} for day {day}")
                    break
            
            await wait_for_prices_loaded(page)
            await asyncio.sleep(2)
            
            # 3. Click the specific day cell using Playwright locators
            # We must ignore "ghost" days from the previous month (like Jan 27th appearing on the Feb calendar).
            # Active days are NOT disabled and contain a price label.
            day_locator = page.locator(f"button.lowest-fare-day:not([disabled]):has(.lowest-fare-day__day:text-is('{day}'))")
            
            if await day_locator.count() > 0:
                await day_locator.first.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)
                await day_locator.first.click(force=True)
                clicked = True
            else:
                clicked = False
            
            if not clicked:
                print(f"    -> Could not find button for day {day}")
                continue
            
            await asyncio.sleep(2)
            
            # 4. Click Continue button
            continue_btn = page.locator("button:has-text('CONTINUE'), a:has-text('CONTINUE')")
            if await continue_btn.count() > 0:
                await continue_btn.first.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)
                await continue_btn.first.click()
                await asyncio.sleep(8)  # Wait for flight selection page to load
            else:
                print(f"    -> Continue button not found")
                continue
            
            # 5. Extract flight details
            flights = await extract_flight_details_page(page)
            
            if flights:
                min_price = min(f['price'] for f in flights)
                
                for flight in flights:
                    is_cheapest = 1 if flight['price'] == min_price else 0
                    save_flight_detail(
                        route=route_str,
                        flight_date=flight_date_str,
                        flight_number=flight['flight_number'],
                        departure_time=flight['departure_time'],
                        arrival_time=flight['arrival_time'],
                        price=flight['price'],
                        is_cheapest=is_cheapest,
                        is_special=1 if flight['is_special'] else 0,
                        scrape_datetime=scrape_dt,
                        days_before_flight=days_before
                    )
                    total_saved += 1
                
                print(f"    -> Saved {len(flights)} flights for {flight_date_str} (cheapest: R{min_price:.2f})")
            else:
                print(f"    -> No flights found on detail page")
            
        except Exception as e:
            print(f"    -> Error capturing day {day} details: {e}")
    
    return total_saved


async def run_scraper():
    """Main async scraper function."""
    init_db()
    today = datetime.now()
    scrape_dt = today.strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 60)
    print(f"FlySafair Price Scraper - Starting at {scrape_dt}")
    print("=" * 60)

    # Create screenshots folder
    screenshots_dir = Path(__file__).parent / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)
    
    # Clean up screenshots older than 5 days
    cutoff = time.time() - (5 * 24 * 60 * 60)
    cleaned = 0
    for ss in screenshots_dir.glob("*.png"):
        try:
            if ss.stat().st_mtime < cutoff:
                ss.unlink()
                cleaned += 1
        except Exception:
            pass
    if cleaned > 0:
        print(f"  Cleanup: Deleted {cleaned} old screenshot(s).")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--disable-notifications']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            permissions=[],
            viewport={"width": 1400, "height": 900}
        )
        page = await context.new_page()

        for route in ROUTES:
            route_str = f"{route['from_code']}-{route['to_code']}"
            print(f"\n{'='*40}")
            print(f"Scraping: {route['from_name']} -> {route['to_name']}")
            print(f"{'='*40}")

            try:
                await page.goto("https://www.flysafair.co.za/flight/low-fare-search", wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(8)

                await accept_cookies(page)
                await select_one_way(page)
                await fill_origin(page, route['from_name'], route.get('from_match'))
                await fill_destination(page, route['to_name'], route.get('to_match'))
                await click_search(page)

                # Screenshot after search
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                ss_path = screenshots_dir / f"{route_str}_{ts}.png"
                await page.screenshot(path=str(ss_path), full_page=True)
                print(f"  Screenshot -> {ss_path.name}")

                # ===== PASS 1: Extract calendar prices for all months =====
                all_month_data = []  # Store (month_text, month_num, year_num, prices) per month
                for month_idx in range(MONTHS_AHEAD):
                    print(f"  Month {month_idx + 1}/{MONTHS_AHEAD}...")

                    month_text, prices = await extract_calendar_data(page)
                    month_num, year_num = parse_month_year(month_text)

                    saved = 0
                    for entry in prices:
                        day = entry["day"]
                        price = entry["price"]

                        if month_num and year_num:
                            try:
                                flight_date = datetime(year_num, month_num, day)
                                flight_date_str = flight_date.strftime("%Y-%m-%d")
                                days_before = (flight_date - today).days
                                if days_before < 0:
                                    continue
                            except ValueError:
                                continue
                        else:
                            flight_date_str = f"Unknown-{day}"
                            days_before = 0

                        save_flight_price(
                            route=route_str,
                            flight_date=flight_date_str,
                            departure_time="calendar",
                            scrape_datetime=scrape_dt,
                            days_before_flight=days_before,
                            price=price
                        )
                        saved += 1

                    # Track cheapest days and Friday/Sundays per month
                    if prices and month_num and year_num:
                        min_price = min(p["price"] for p in prices)
                        
                        target_days = []
                        for p in prices:
                            is_min = p["price"] == min_price
                            
                            try:
                                p_date = datetime(year_num, month_num, p["day"])
                                day_of_week = p_date.weekday()
                                is_weekend = day_of_week == 4 or day_of_week == 6 # Friday = 4, Sunday = 6
                            except ValueError:
                                is_weekend = False
                                
                            # OPTION 2 LOGIC: 
                            # Months 1-3 (idx 0,1,2): Check cheapest + ALL Fridays/Sundays
                            # Months 4-8 (idx 3+): Check ONLY the absolute cheapest days
                            if month_idx < 3:
                                if is_min or is_weekend:
                                    target_days.append(p["day"])
                            else:
                                if is_min:
                                    target_days.append(p["day"])
                                    
                        # Deduplicate days
                        target_days = list(set(target_days))
                        target_days.sort()

                        all_month_data.append({
                            "month_text": month_text,
                            "month_num": month_num,
                            "year_num": year_num,
                            "month_idx": month_idx,
                            "target_days": target_days,
                            "cheapest_price": min_price
                        })

                    print(f"    -> Saved {saved} prices ({month_text})")

                    if month_idx < MONTHS_AHEAD - 1:
                        if not await navigate_next_month(page):
                            print("    -> Could not navigate to next month")
                            break

                # ===== PASS 2: Capture flight details for targeted days in EVERY month =====
                if all_month_data:
                    # Execute Pass 2 only for the next 3 months to save time (Pass 1 covers all 8)
                    pass2_months = all_month_data[:3]
                    
                    # Target max 10 days per month (in case whole month is same price)
                    for m in pass2_months:
                        m["target_days"] = m["target_days"][:10]
                        
                    total_targets = sum(len(m["target_days"]) for m in pass2_months)
                    print(f"\n  --- Pass 2: Flight details for {total_targets} target day(s) across {len(pass2_months)} months ---")
                    
                    if total_targets > 0:
                        # Reload the calendar page fresh
                        await page.goto("https://www.flysafair.co.za/flight/low-fare-search", wait_until="domcontentloaded", timeout=60000)
                        await asyncio.sleep(8)
                        await accept_cookies(page)
                        await select_one_way(page)
                        await fill_origin(page, route['from_name'], route.get('from_match'))
                        await fill_destination(page, route['to_name'], route.get('to_match'))
                        await click_search(page)
                        
                        # Navigate month-by-month (sequentially, same order as pass 1)
                        for cm_idx, cm in enumerate(pass2_months):
                            # Skip if no target days to check
                            if not cm["target_days"]:
                                continue
                                
                            # Navigate to this month's position
                            if cm_idx > 0:
                                # Skip from previous month to this one
                                skips_needed = cm["month_idx"] - pass2_months[cm_idx - 1]["month_idx"]
                                for skip in range(skips_needed):
                                    if not await navigate_next_month(page):
                                        print(f"    -> Could not navigate to {cm['month_text']}")
                                        break
                            elif cm["month_idx"] > 0:
                                # First cheapest month but not the first calendar month
                                for skip in range(cm["month_idx"]):
                                    if not await navigate_next_month(page):
                                        print(f"    -> Could not navigate to {cm['month_text']}")
                                        break
                            
                            print(f"  Checking {cm['month_text']} — {len(cm['target_days'])} target day(s)")
                            
                            # Capture details for this month's target days
                            detail_count = await capture_cheapest_flight_details(
                                page, route_str, cm["month_text"],
                                cm["month_num"], cm["year_num"],
                                today, scrape_dt, cm["target_days"],
                                route
                            )
                            if detail_count > 0:
                                print(f"    -> Saved {detail_count} flight details")

                            
            except Exception as e:
                print(f"  ERROR: {e}")

            await asyncio.sleep(2)

        print(f"\n{'='*60}")
        print("Scraping complete!")
        print(f"{'='*60}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(run_scraper())
