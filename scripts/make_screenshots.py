"""Regenerate Play Store screenshots at 1170x2532 using the running Expo preview.
Backend is now Railway. Tester has 2 goals seeded in Atlas.
"""
import asyncio, os, sys
from playwright.async_api import async_playwright
sys.path.insert(0, '/app/backend')

OUT = '/app/frontend/store-assets'
os.makedirs(OUT, exist_ok=True)
BASE = 'http://localhost:3000'
EMAIL, PW = 'tester@goalpilot.ai', 'Test@1234'
GOAL_ID = os.environ.get('GOAL_ID', '')


async def snap(page, name, route, settle=4500, scroll=0):
    await page.goto(f'{BASE}{route}', wait_until='domcontentloaded', timeout=30000)
    await page.wait_for_timeout(settle)
    if scroll:
        await page.evaluate(f'window.scrollBy(0, {scroll})')
        await page.wait_for_timeout(1500)
    await page.screenshot(path=f'{OUT}/{name}.png', full_page=False)
    print(f'✓ {name}.png')


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            viewport={'width': 390, 'height': 844},
            device_scale_factor=3,
            is_mobile=True, has_touch=True,
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15',
        )
        page = await ctx.new_page()
        await page.goto(BASE, wait_until='networkidle', timeout=60000)
        await page.wait_for_timeout(4000)
        try:
            await page.get_by_text('I already have an account').click(force=True, timeout=8000)
            await page.wait_for_timeout(2500)
        except Exception as e:
            print(f'welcome click: {e}')
        try:
            await page.locator("input[type='email']").first.click(force=True)
            await page.keyboard.type(EMAIL, delay=20)
            await page.locator("input[type='password']").first.click(force=True)
            await page.keyboard.type(PW, delay=20)
            try:
                await page.get_by_text('Log in', exact=True).first.click(force=True, timeout=4000)
            except Exception:
                await page.locator("input[type='password']").first.press('Enter')
            await page.wait_for_timeout(8000)
        except Exception as e:
            print(f'login: {e}')

        await snap(page, '01_today',       '/',                settle=6000)
        await snap(page, '02_goals',       '/goals',           settle=5000)
        if GOAL_ID:
            await snap(page, '03_goal_detail', f'/goal/{GOAL_ID}', settle=6000, scroll=350)
        await snap(page, '04_profile',     '/profile',         settle=4000)
        await snap(page, '05_review',      '/review',          settle=9000)
        await snap(page, '06_new_goal',    '/goal/new',        settle=4500)
        await browser.close()
        print(f'\nAll done at {OUT}/')


if __name__ == '__main__':
    asyncio.run(main())
