"""Generate Google Play Store screenshots at 1170x2532.
Uses direct URL navigation (Expo Router) — no tab clicks.
"""
import asyncio
import os
from playwright.async_api import async_playwright

OUT_DIR = "/app/screenshots"
os.makedirs(OUT_DIR, exist_ok=True)

EMAIL = "tester@goalpilot.ai"
PASSWORD = "Test@1234"
BASE = "http://localhost:3000"
GOAL_ID = os.environ.get("GOAL_ID", "")


async def snap(page, name, route, settle=4000, scroll=0):
    await page.goto(f"{BASE}{route}", wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(settle)
    if scroll:
        await page.evaluate(f"window.scrollBy(0, {scroll})")
        await page.wait_for_timeout(1500)
    await page.screenshot(path=f"{OUT_DIR}/{name}.png", full_page=False)
    print(f"✓ {name}.png")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
        )
        page = await context.new_page()

        # 1) Boot + welcome -> login
        await page.goto(BASE, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(4000)
        try:
            await page.get_by_text("I already have an account").click(force=True, timeout=8000)
            await page.wait_for_timeout(2500)
        except Exception as e:
            print(f"welcome click skip: {e}")

        # 2) Login
        try:
            await page.locator("input[type='email']").first.click(force=True)
            await page.keyboard.type(EMAIL, delay=20)
            await page.locator("input[type='password']").first.click(force=True)
            await page.keyboard.type(PASSWORD, delay=20)
            try:
                await page.get_by_text("Log in", exact=True).first.click(force=True, timeout=4000)
            except Exception:
                await page.locator("input[type='password']").first.press("Enter")
            await page.wait_for_timeout(7000)
        except Exception as e:
            print(f"login error: {e}")

        # 3) Capture each route via direct URL nav
        await snap(page, "01_today",       "/",                settle=5000)
        await snap(page, "02_goals",       "/goals",           settle=4000)
        if GOAL_ID:
            await snap(page, "03_goal_detail", f"/goal/{GOAL_ID}", settle=6000, scroll=350)
        await snap(page, "04_profile",     "/profile",         settle=4000)
        await snap(page, "05_review",      "/review",          settle=9000)  # AI review loads
        await snap(page, "06_new_goal",    "/goal/new",        settle=4000)

        await browser.close()
        print(f"\nAll done. Files at {OUT_DIR}/")


if __name__ == "__main__":
    asyncio.run(main())
