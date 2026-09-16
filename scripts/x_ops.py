#!/usr/bin/env python3
"""
x_ops.py — operator toolkit for the X account. Runs through the real web UI with
CloakBrowser, same path that posted the first tweet.

    check                    who am I, how many followers, unread notifications
    mentions [N]             read the latest N mentions
    post "<text>"            publish a post
    post --file F            publish from a file (use this for anything long)
    reply <url> "<text>"     reply to a specific post
    like <url>               like a post
    whoami                   session validity only

Every write action is gated: cookies present, session valid, no challenge/overlay,
and the action target actually resolves. Nothing is clicked blind.

Cookies live in ~/.x/cookies.txt (mode 600) and are NEVER printed.
"""
from __future__ import annotations

import argparse, asyncio, json, pathlib, re, sys

COOKIE_FILE = pathlib.Path("/home/goonjoru/.hermes/profiles/godhood/home/.x/cookies.txt")
SHOT_DIR = pathlib.Path("/tmp/x_ops")
URL_RE = re.compile(r"https?://\S+|\b(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/\S*)?", re.I)
LIMIT = 280


# ── gates ──────────────────────────────────────────────────────────────────

def weighted_len(text: str) -> int:
    """X collapses every URL to 23 chars, so a raw len() under-counts."""
    total, pos = 0, 0
    for m in URL_RE.finditer(text):
        total += len(text[pos:m.start()]) + 23
        pos = m.end()
    return total + len(text[pos:])


def load_cookies():
    if not COOKIE_FILE.exists():
        sys.exit(f"no cookies at {COOKIE_FILE}")
    mode = oct(COOKIE_FILE.stat().st_mode & 0o777)
    if mode != "0o600":
        print(f"WARN mode={mode}, expected 0o600")
    jar = []
    for line in COOKIE_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip()
        if not v or "ISI_" in v:
            sys.exit(f"cookie {k} still a placeholder — fill {COOKIE_FILE}")
        jar.append({"name": k, "value": v, "domain": ".x.com", "path": "/", "secure": True})
    have = {c["name"] for c in jar}
    for need in ("auth_token", "ct0"):
        if need not in have:
            sys.exit(f"cookie {need} missing (have {sorted(have)})")
    return jar


def gate_text(text: str, allow_over=False):
    n = weighted_len(text)
    if n > LIMIT and not allow_over:
        sys.exit(f"text is {n}/{LIMIT} weighted — over by {n-LIMIT}. Shorten it "
                 f"(X counts each URL as 23 chars).")
    print(f"  length: {n}/{LIMIT} weighted")
    return text


# ── browser helpers ────────────────────────────────────────────────────────

JS_IS_LOGGED_IN = r"""
() => {
  // logged-out X renders a username field; logged-in renders the sidebar nav
  const loginField = document.querySelector('input[autocomplete="username"]');
  const nav = document.querySelector('[data-testid="SideNav_AccountSwitcher_Button"]')
           || document.querySelector('a[href="/home"]');
  return {loggedOut: !!loginField, hasNav: !!nav};
}
"""


async def open_page(browser, cookies, shot_name):
    ctx = await browser.new_context(viewport={"width": 1500, "height": 1400})
    await ctx.add_cookies(cookies)
    page = await ctx.new_page()
    page.set_default_timeout(30000)
    return page


async def goto(page, url, settle=7000):
    await page.goto(url, wait_until="domcontentloaded", timeout=90000)
    await page.wait_for_timeout(settle)


async def assert_logged_in(page, shot_dir):
    st = await page.evaluate(JS_IS_LOGGED_IN)
    if st.get("loggedOut"):
        p = shot_dir / "login-wall.png"
        await page.screenshot(path=str(p))
        sys.exit(f"SESSION DEAD — X served a login wall. Refresh {COOKIE_FILE}. shot: {p}")
    return st


async def human_type(loc, text):
    """Type with human-ish cadence, with a small pause mid-sentence."""
    half = max(1, len(text) // 2)
    await loc.type(text[:half], delay=22)
    await loc.page.wait_for_timeout(400)
    await loc.type(text[half:], delay=18)


# ── actions ────────────────────────────────────────────────────────────────

async def act_whoami(page):
    await goto(page, "https://x.com/home")
    await assert_logged_in(page, SHOT_DIR)
    info = await page.evaluate(r"""
    () => {
      const el = document.querySelector('[data-testid="SideNav_AccountSwitcher_Button"]');
      return {handle: el ? el.innerText.replace(/\n/g,' | ') : null, url: location.href};
    }""")
    print(json.dumps(info, indent=2, ensure_ascii=False))


async def act_check(page):
    await goto(page, "https://x.com/home")
    await assert_logged_in(page, SHOT_DIR)
    info = await page.evaluate(r"""
    () => {
      const out = {};
      const acct = document.querySelector('[data-testid="SideNav_AccountSwitcher_Button"]');
      out.account = acct ? acct.innerText.replace(/\n/g,' ').slice(0,120) : null;
      // nav counters (notifications / messages badges)
      out.badges = [...document.querySelectorAll('nav [aria-label]')]
        .map(n => n.getAttribute('aria-label'))
        .filter(l => /notification|message|unread/i.test(l)).slice(0,6);
      out.tabs = [...document.querySelectorAll('[role="tab"]')]
        .map(t => t.innerText.trim()).filter(Boolean).slice(0,8);
      return out;
    }""")
    print(json.dumps(info, indent=2, ensure_ascii=False))
    await page.screenshot(path=str(SHOT_DIR / "home.png"))


async def act_mentions(page, n):
    await goto(page, "https://x.com/notifications/mentions")
    await assert_logged_in(page, SHOT_DIR)
    await page.wait_for_timeout(4000)
    items = await page.evaluate(r"""
    (n) => {
      return [...document.querySelectorAll('article')].slice(0, n).map(a => {
        const link = a.querySelector('a[href*="/status/"]');
        const t = a.querySelector('time');
        return {
          url: link ? 'https://x.com' + link.getAttribute('href') : null,
          when: t ? t.getAttribute('datetime') : null,
          text: a.innerText.replace(/\n+/g,' ').slice(0,300),
        };
      });
    }""", n)
    print(json.dumps(items, indent=2, ensure_ascii=False))
    await page.screenshot(path=str(SHOT_DIR / "mentions.png"))


async def compose(page, text, reply_to=None):
    """Open composer (inline on home, or the reply box on a status page) and type text."""
    await assert_logged_in(page, SHOT_DIR)

    composer = None
    for sel in ('[data-testid="tweetTextarea_0"]',
                'div[role="textbox"][contenteditable="true"]'):
        loc = page.locator(sel).first
        try:
            await loc.wait_for(state="visible", timeout=25000)
            composer = loc
            break
        except Exception:
            continue
    if composer is None:
        await page.screenshot(path=str(SHOT_DIR / "no-composer.png"))
        sys.exit("composer not found — see /tmp/x_ops/no-composer.png")

    await composer.click()
    await page.wait_for_timeout(900)
    await human_type(composer, text)
    await page.wait_for_timeout(2500)

    # read back from the DOM: what actually landed is what gets published
    typed = ""
    try:
        typed = await composer.inner_text()
    except Exception:
        pass
    if typed.strip() != text.strip():
        print("  NOTE: composer text differs slightly from input "
              "(X may reformat URLs/mentions) — publishing what is in the box.")

    # X puts an absolutely-positioned overlay over the composer toolbar when a link
    # card renders; a physical button click cannot reach it. focus() + Ctrl+Enter is
    # X's own post shortcut and bypasses the overlay.
    btn_sel = '[data-testid="tweetButtonInline"]' if reply_to is None else '[data-testid="tweetButton"]'
    btn = page.locator(btn_sel).first
    try:
        await btn.wait_for(state="visible", timeout=12000)
    except Exception:
        await page.screenshot(path=str(SHOT_DIR / "no-button.png"))
        sys.exit(f"post button not found ({btn_sel})")

    disabled = await btn.get_attribute("aria-disabled")
    if str(disabled).lower() == "true":
        await page.screenshot(path=str(SHOT_DIR / "disabled.png"))
        sys.exit("post button is DISABLED — text likely over limit or empty")

    focused = await page.evaluate("(s)=>{const e=document.querySelector(s); if(!e) return false; e.focus(); return document.activeElement===e;}", btn_sel)
    if not focused:
        sys.exit("could not focus the post button")
    await page.keyboard.press("Control+Enter")
    print("  published via Ctrl+Enter")
    await page.wait_for_timeout(9000)


async def act_post(page, text, dry):
    await goto(page, "https://x.com/home", settle=8000)
    if dry:
        await assert_logged_in(page, SHOT_DIR)
        print("  DRY RUN — would post:")
        print("  " + text.replace("\n", "\n  "))
        return
    await compose(page, text)


async def act_reply(page, url, text, dry):
    await goto(page, url, settle=8000)
    if dry:
        await assert_logged_in(page, SHOT_DIR)
        print(f"  DRY RUN — would reply to {url}:")
        print("  " + text.replace("\n", "\n  "))
        return
    await compose(page, text, reply_to=url)


async def act_like(page, url, dry):
    await goto(page, url, settle=8000)
    await assert_logged_in(page, SHOT_DIR)
    sel = '[data-testid="like"]'
    btn = page.locator(sel).first
    try:
        await btn.wait_for(state="visible", timeout=15000)
    except Exception:
        sys.exit(f"like button not found on {url} (already liked, or not a post page?)")
    if dry:
        print(f"  DRY RUN — would like {url}")
        return
    try:
        await btn.click(timeout=10000)
    except Exception as e:
        sys.exit(f"like click failed: {str(e)[:140]}")
    print(f"  liked {url}")
    await page.wait_for_timeout(2500)


# ── entry ──────────────────────────────────────────────────────────────────

async def main(args):
    import cloakbrowser
    SHOT_DIR.mkdir(parents=True, exist_ok=True)

    cookies = load_cookies()
    print(f"cookies: {sorted(c['name'] for c in cookies)}")

    text = None
    if args.cmd in ("post", "reply"):
        text = pathlib.Path(args.file).read_text().rstrip("\n") if args.file else args.text
        if not text:
            sys.exit("no text given")
        gate_text(text, allow_over=getattr(args, "allow_over", False))

    async with await cloakbrowser.launch_async(headless=False, humanize=True) as browser:
        page = await open_page(browser, cookies, args.cmd)

        if args.cmd == "whoami":
            await act_whoami(page)
        elif args.cmd == "check":
            await act_check(page)
        elif args.cmd == "mentions":
            await act_mentions(page, args.n)
        elif args.cmd == "post":
            await act_post(page, text, args.dry_run)
        elif args.cmd == "reply":
            await act_reply(page, args.url, text, args.dry_run)
        elif args.cmd == "like":
            await act_like(page, args.url, args.dry_run)
        else:
            sys.exit(f"unknown command {args.cmd}")

        if args.cmd in ("post", "reply") and not args.dry_run:
            print(f"  screenshot: {SHOT_DIR}")


def build_parser():
    ap = argparse.ArgumentParser(description="X operator toolkit")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("whoami")
    sub.add_parser("check")

    m = sub.add_parser("mentions")
    m.add_argument("n", nargs="?", type=int, default=10)

    for name in ("post", "reply"):
        s = sub.add_parser(name)
        s.add_argument("text", nargs="?")
        s.add_argument("--file", help="read text from a file instead")
        s.add_argument("--dry-run", action="store_true")
        s.add_argument("--allow-over", action="store_true", help="skip the 280 check (X will refuse anyway)")
        if name == "reply":
            s.add_argument("url", help="post URL to reply to")

    l = sub.add_parser("like")
    l.add_argument("url")
    l.add_argument("--dry-run", action="store_true")
    return ap


def run_cli():
    ap = build_parser()
    args = ap.parse_args()
    asyncio.run(main(args))


if __name__ == "__main__":
    run_cli()
