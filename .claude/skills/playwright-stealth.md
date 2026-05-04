# Playwright Stealth & Multi-Account Skill

Use this skill when automating Amazon (scraping bestsellers/reviews) or KDP (publishing).

## Browser context isolation (per KDP account)
Each account gets:
- Dedicated `BrowserContext` with own `storageState` file (encrypted at rest)
- Dedicated residential proxy endpoint from same country as account holder
- Stable fingerprint (UA, viewport, timezone, locale, screen) — set once, never change

```python
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async

async def get_context(account):
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, proxy={
        "server": account.proxy_endpoint,
        "username": account.proxy_user,
        "password": account.proxy_pass,
    })
    ctx = await browser.new_context(
        storage_state=account.storage_state_path,
        user_agent=account.fingerprint.user_agent,
        viewport=account.fingerprint.viewport,
        locale=account.fingerprint.locale,
        timezone_id=account.fingerprint.timezone,
        screen=account.fingerprint.screen,
    )
    page = await ctx.new_page()
    await stealth_async(page)
    return ctx, page
```

## Anti-detection rules
- NEVER share storageState between accounts
- NEVER use the same proxy IP for two accounts
- NEVER use datacenter proxies for KDP (Amazon detects them); residential only
- Add human-like delays: `await asyncio.sleep(random.uniform(1.5, 4.0))` between actions
- Move mouse before clicking (Playwright `page.mouse.move` + `page.mouse.click`)
- Type with delays: `await page.type(selector, text, delay=80)` not `fill()`

## Rate limits (DB-enforced via accounts.daily_quota)
- KDP publishes: max 5/day for first 60 days per account, then 10/day
- Amazon scrapes: max 200 pages/hour per proxy IP
- Reviews scrape: max 50/min per proxy
- Always check quota in DB before action; raise QuotaExceeded if over

## Storage state lifecycle
1. First login: manual via `python kdp_cli.py login --account=X` on operator machine
2. File encrypted with age (operator's age key), copied to VPS
3. VPS decrypts at process start to tmpfs `/run/colorforge/state/{account}.json`
4. Re-login needed every ~30 days when Amazon expires session
5. System detects expiry by 3xx redirect to login page -> fires alert

## Common failure modes
- Captcha: Amazon shows captcha -> halt, alert operator, do not auto-solve
- 2FA prompt mid-session: only happens on suspicious activity -> halt, alert
- IP block: scraping returns 503 repeatedly -> rotate proxy endpoint, alert
- Selector changed: action fails with structured SelectorMissingError -> screenshot saved, alert
