import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from automation.gmail_code_reader import get_latest_verification_code
from automation.captcha_solver import solve_captcha_beast
import logging

# Settings
SIGNUP_URL = "https://schools.myp2e.org/"
DEFAULT_PASSWORD = "asdf@000"

logger = logging.getLogger(__name__)

async def automate_signup_playwright(cred):
    email = cred["email"]
    password = cred["password"]
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                await page.goto(SIGNUP_URL, timeout=30000)
                await page.click("text=SIGN IN")
                await page.click("text=Sign up now")
                await page.fill("input[name=\"email\"]", email)
                await page.click("button:has-text(\"Send verification code\")")
                # Wait for code to arrive in Gmail
                code = get_latest_verification_code(email, password)
                if not code:
                    await browser.close()
                    return False, "No verification code"
                await page.fill("input[name=\"code\"]", code)
                await page.click("button:has-text(\"Verify code\")")
                await page.fill("input[name=\"newPassword\"]", DEFAULT_PASSWORD)
                await page.fill("input[name=\"confirmPassword\"]", DEFAULT_PASSWORD)
                # Captcha
                captcha_img = None
                try:
                    captcha_img = await page.query_selector("img[alt*='captcha'], img[src*='captcha']")
                except Exception: pass
                if captcha_img:
                    path = "captcha.png"
                    await captcha_img.screenshot(path=path)
                    captcha_code = solve_captcha_beast(path)
                    if captcha_code:
                        await page.fill("input[name=\"captcha\"]", captcha_code)
                await page.click("button:has-text(\"Sign Up\")")
                await asyncio.sleep(2)
                if "dashboard" in page.url or "success" in (await page.content()):
                    await browser.close()
                    return True, ""
                await browser.close()
                return False, "Signup failed (unknown reason)"
            except PlaywrightTimeoutError as te:
                logger.error("Playwright timeout: %s", te)
                await browser.close()
                return False, "Timeout"
            except Exception as e:
                logger.error("Signup error: %s", e)
                await browser.close()
                return False, f"Exception: {e}"
    except Exception as e:
        logger.error("Playwright launch error: %s", e)
        return False, f"Launch error: {e}"
