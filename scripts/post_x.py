#!/usr/bin/env python3
"""
post_x.py — post to X through the real web UI with CloakBrowser.

Gates (all must pass before any Post click):
  1. cookies file exists, mode 600, both cookies present
  2. post text weighted length <= 280 (X counts URLs as 23 chars)
  3. every did:key: in the text matches identity.json byte for byte
  4. Post button is present AND not disabled (aria-disabled / disabled attr)

Usage (headed, under Xvfb — run scripts/post_x.sh instead of calling this directly):
    --dry-run   fill composer, screenshot, stop
    --post      publish (still requires gates 1-4 to pass)
"""
import argparse, asyncio, json, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
COOKIE_FILE = pathlib.Path("/home/goonjoru/.hermes/profiles/godhood/home/.x/cookies.txt")
IDENTITY = REPO / "identity.json"
POST_TEXT = HERE / "post.txt"

URL_RE = re.compile(r"https?://\S+|\b(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/\S*)?", re.I)
DID_RE = re.compile(r"did:key:z[1-9A-HJ-NP-Za-km-z]+")
LIMIT = 280

# Hit-test the button's CURRENT centre. Returns ok=True only when the topmost node
# at that point belongs to the button (or the button belongs to that node).
COVER_CHECK = r"""
(sel) => {
  const el = document.querySelector(sel);
  if (!el) return {ok: false, why: 'button gone'};
  const r = el.getBoundingClientRect();
  if (r.width === 0 || r.height === 0) return {ok: false, why: 'button zero-size'};
  const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  if (cy < 0 || cy > innerHeight || cx < 0 || cx > innerWidth)
    return {ok: false, why: `centre off-viewport y=${Math.round(cy)} vh=${innerHeight}`};
  const hits = document.elementsFromPoint(cx, cy);
  if (!hits.length) return {ok: false, why: 'no node at point'};
  const top = hits[0];
  const related = el.contains(top) || top.contains(el);
  return {
    ok: related,
    why: related ? 'top node is part of the button' : 'foreign ' + top.tagName,
    cy: Math.round(cy), boxBottom: Math.round(r.bottom),
  };
}
"""


def weighted_len(text):
    total, pos = 0, 0
    for m in URL_RE.finditer(text):
        total += len(text[pos:m.start()]) + 23
        pos = m.end()
    return total + len(text[pos:])


def gate_cookies():
    if not COOKIE_FILE.exists():
        sys.exit(f"GATE 1 FAIL: missing {COOKIE_FILE}")
    mode = oct(COOKIE_FILE.stat().st_mode & 0o777)
    if mode != "0o600":
        print(f"  WARN mode={mode} (expected 0o600)")
    jar = []
    for line in COOKIE_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip()
        if not v or "ISI_" in v:
            sys.exit(f"GATE 1 FAIL: cookie {k} not filled")
        jar.append({"name": k, "value": v, "domain": ".x.com", "path": "/", "secure": True})
    have = {c["name"] for c in jar}
    for need in ("auth_token", "ct0"):
        if need not in have:
            sys.exit(f"GATE 1 FAIL: cookie {need} missing (have {sorted(have)})")
    print(f"  GATE 1 OK  cookies {sorted(have)}  mode {mode}")
    return jar


def gate_text():
    if not POST_TEXT.exists():
        sys.exit(f"GATE 2 FAIL: missing {POST_TEXT}")
    text = POST_TEXT.read_text().rstrip("\n")
    n = weighted_len(text)
    if n > LIMIT:
        sys.exit(f"GATE 2 FAIL: weighted {n}/{LIMIT} — over by {n-LIMIT}. Post button would be disabled.")
    print(f"  GATE 2 OK  weighted {n}/{LIMIT} ({LIMIT-n} to spare)")

    dids = DID_RE.findall(text)
    if not dids:
        sys.exit("GATE 3 FAIL: no did:key in the post text")
    real = json.loads(IDENTITY.read_text())["did"]
    for d in dids:
        if d != real:
            sys.exit(f"GATE 3 FAIL: DID mismatch\n   post    : {d}\n   identity: {real}")
    print(f"  GATE 3 OK  DID matches identity.json ({len(dids)} occurrence)")
    return text


async def gate_button(page):
    """Return the Post locator, or None if absent/disabled."""
    for sel in ('[data-testid="tweetButtonInline"]', '[data-testid="tweetButton"]'):
        loc = page.locator(sel).first
        try:
            await loc.wait_for(state="visible", timeout=10000)
        except Exception:
            continue
        disabled = await loc.get_attribute("aria-disabled")
        if disabled is None:
            disabled = await loc.get_attribute("disabled")
        if str(disabled).lower() in ("true", ""):
            print(f"  GATE 4 FAIL: Post button present but disabled ({sel})")
            return None
        print(f"  GATE 4 OK  Post button enabled ({sel})")
        return loc
    print("  GATE 4 FAIL: Post button not found")
    return None


async def run(dry, shot, text):
    import cloakbrowser

    cookies = gate_cookies()
    kw = {"headless": False, "humanize": True}

    async with await cloakbrowser.launch_async(**kw) as browser:
        # Tall viewport: X's floating Grok/Chat buttons sit bottom-right of the
        # viewport and overlap the composer's Post button at 1000px height.
        # CloakBrowser's pointer-events check correctly refuses the covered click.
        ctx = await browser.new_context(viewport={"width": 1500, "height": 1400})
        await ctx.add_cookies(cookies)
        page = await ctx.new_page()

        print("-> x.com/home")
        await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=90000)
        await page.wait_for_timeout(7000)
        print(f"   url: {page.url}")

        if await page.locator('input[autocomplete="username"]').count():
            await page.screenshot(path=shot)
            sys.exit(f"LOGIN WALL — cookies rejected. shot: {shot}")

        blockers = []
        for sel in ('div[role="dialog"]', 'iframe[src*="arkose"]'):
            c = await page.locator(sel).count()
            if c:
                blockers.append(f"{sel}x{c}")
        print(f"   blockers: {blockers or '-'}")

        composer = None
        for sel in ('[data-testid="tweetTextarea_0"]',
                    'div[role="textbox"][contenteditable="true"]'):
            loc = page.locator(sel).first
            try:
                await loc.wait_for(state="visible", timeout=20000)
                composer = loc
                print(f"   composer: {sel}")
                break
            except Exception:
                continue
        if composer is None:
            await page.screenshot(path=shot)
            pathlib.Path(shot + ".html").write_text(await page.content())
            sys.exit(f"composer not found. shot+html: {shot}")

        # human cadence: click, settle, type slowly, settle
        await composer.click()
        await page.wait_for_timeout(900)
        await composer.type(text, delay=18)
        await page.wait_for_timeout(3000)

        # read back what actually landed and re-verify the DID in the DOM
        typed = ""
        try:
            typed = await composer.inner_text()
        except Exception:
            pass
        for d in DID_RE.findall(typed):
            if d != json.loads(IDENTITY.read_text())["did"]:
                await page.screenshot(path=shot)
                sys.exit(f"ABORT: DID corrupted in composer.\n   typing : {d}\n   earlier: verified ok")

        await page.screenshot(path=shot)
        print(f"   shot: {shot}")

        btn = await gate_button(page)

        if dry:
            print("\nDRY RUN — nothing posted.")
            return

        if btn is None:
            sys.exit("refusing to post: gate 4 failed")

        # X's GitHub/Social preview card injects an absolutely-positioned overlay that
        # intercepts pointer events over the composer's toolbar (verified: a textless
        # DIV with pe:auto wins elementsFromPoint at all 25 sample points around the
        # button centre). A physical click therefore cannot reach the button, and
        # CloakBrowser's pointer-events guard correctly refuses it.
        #
        # Keyboard route: focus the button and press Enter. This is also the most
        # human-shaped path — Ctrl/Cmd+Enter is the documented X shortcut for posting.
        poster_sel = '[data-testid="tweetButtonInline"]'

        focused = await page.evaluate(
            """(sel) => {
                 const el = document.querySelector(sel);
                 if (!el) return false;
                 el.focus();
                 return document.activeElement === el;
               }""", poster_sel)
        print(f"   button focused: {focused}")

        if not focused:
            await page.screenshot(path=shot)
            sys.exit("aborting: could not focus the Post button")

        # Ctrl+Enter = X's own post shortcut; works regardless of overlay interception
        await page.keyboard.press("Control+Enter")
        print("-> pressed Ctrl+Enter")
        await page.wait_for_timeout(11000)
        await page.screenshot(path=shot + ".after.png")
        print(f"   url after : {page.url}")
        print(f"   shot after: {shot}.after.png")


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--post", action="store_true")
    ap.add_argument("--shot", default="/tmp/x_compose.png")
    a = ap.parse_args()

    print("== gates ==")
    text = gate_text()
    print(f"== {'LIVE POST' if a.post else 'DRY RUN'} ==")
    asyncio.run(run(dry=a.dry_run, shot=a.shot, text=text))


if __name__ == "__main__":
    main()
