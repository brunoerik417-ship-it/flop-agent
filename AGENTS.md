# AGENTS.md — flop-agent

Rules for any agent (human or AI) driving this folder. Read before acting.

---

## What this repo is

A minimal, verifiable toolkit for participating in the **Technocore** protocol
(`technocore.chat`, built by [Flop Labs](https://flop.finance)).

The point is not volume. The point is a **clean, aged, reproducible record** that a
referee can check. Everything here is designed so that a third party can reproduce
each claim with `curl`.

---

## Hard rules

### 1. One DID, forever

The identity in `identity.json` is the **only** identity this operator uses.

- **Never** mint a second DID to "increase odds". Flop Labs has published an
  analysis (`flop-labs/technocore-chat#149`) showing the sybil pattern they hunt:
  a fresh key that writes one template pair and is never seen again.
- The DID's value is its **age**. Our DID first appeared in the server archive
  2026-09-11 20:04 UTC. That timestamp already predates every contest cutoff opened
  since. A new DID resets that to zero.
- If the seed is ever suspected of leaking, **rotate the seed, keep the DID** is
  impossible — a DID is derived from its seed. So: protect the seed, do not
  casually rotate. Back it up (`GPG AES256`, off-box) instead.

### 2. Never paste a secret into a chat body

`identity.json` (seed), `~/.x/cookies.txt` (X session), API keys — these go in
**files with mode 600**, referenced by path. Never in a message body.

A message body is stored by the platform and indexed into its logs forever; you
cannot retract it. A file on the operator's own disk is a different custody path.

- `chmod 600` on every secret file. Re-assert it on every copy.
- Do not commit them. `.gitignore` already covers `identity.json`, `*.pem`, `*.key`,
  `.env`, `*.log`. Keep it that way.
- When handing a secret to the operator, send an **encrypted file**, not plaintext.

### 3. Real work or nothing

Every artifact must be something a third party can verify.

- ✅ A repo you wrote, whose claims reproduce with `curl`.
- ✅ Measured protocol behaviour with the raw numbers and the command that produced them.
- ❌ A "research summary" that restates the job title.
- ❌ Pasting a third party's URL as "evidence" of your own contribution.
- ❌ `Auto-delivered by VPS agent. Job received and processed.`

The board is full of the ❌ patterns. Participating in them makes the record
*cheaper*, not richer — it drops us into the exact cluster anti-sybil scoring is
built to catch.

### 4. Never post a DID you have not byte-checked

A DID is an identifier. One wrong character makes it unverifiable, and a post with
a broken DID is worse than no post.

Before any outbound post that carries the DID:
- compare the string in the payload against `identity.json` character by character
- if a renderer/OCR shows it differently, **trust the file, not the screenshot** —
  but re-verify by reading the value back out of the composer/DOM.

### 5. Check the length before you click Post

X counts a URL as **23 characters** regardless of its real length. A raw
`len()` count is wrong and will let a 300-char post through a 280-char limit.

Always compute the weighted length first (see `scripts/x_count.py`). A disabled
Post button with a red negative counter means the post is over limit — clicking
does nothing.

### 6. Never send text the owner has not read verbatim

A draft is approved as **an exact string, in an exact language, for an exact
target**. Approving draft #1 (Indonesian, for a post) does not approve an English
rewrite of it, and does not approve a reply.

Before any `x_post` / `x_reply`, show the literal text, name the target URL, name
the language, then **wait** for a pick or an explicit "gas". "Test it", "reply aja",
"coba dulu" mean *prepare*, not *publish*.

Learned 2026-09-19: a test reply was posted with text the owner had never seen.
See `X_OPERATOR.md` → "NEVER execute text the owner has not picked".

---

## X (Twitter) posting — bot-risk hygiene

The operator's X account must stay healthy. These rules exist so the account does
not look automated.

### Do

- Use a **real anti-detect browser** (CloakBrowser + Xvfb, headed). Never a plain
  HTTP client: X's v1.1 REST routes 404 now, GraphQL needs a runtime-injected
  `queryId`, and the page sits behind Cloudflare + Arkose.
- **Reuse one persistent browser profile** per account so fingerprint and cookie
  history stay stable across runs. A fresh profile every run is itself a signal.
- Keep **human cadence**: posts minutes apart, not seconds. Compose → pause → post.
- `humanize=True` (CloakBrowser's human mouse/timing model) on every launch.
- Post from the **same network** the account normally uses. A session appearing from
  a datacenter IP is the single strongest "this is a bot" signal.

### Don't

- Don't post in bursts. Don't schedule 10 tweets to fire together.
- Don't post identical text repeatedly. Vary it.
- Don't mix accounts in one browser profile.
- Don't automate engagement (mass like/follow/reply). That is what actually gets
  accounts suspended — not posting.

### Cookies: fixed path, leave it alone

`~/.x/cookies.txt` is the operator's session credential and is meant to **persist**
at that path — that is what makes the tooling usable without re-doing setup.

- **Never delete, shred, or truncate it.** Not after a run, not during "cleanup".
  If you want to reduce exposure, copy it to a `.bak` first and say so.
- If the operator wants to revoke access, *they* log the session out at
  `x.com/settings/sessions`; that kills the server-side session without destroying
  the local file. Only then does the file become inert.
- See `X_OPERATOR.md` → "NEVER delete a credential file the operator supplied".

### What actually triggers suspension (priority order)

1. **Automated engagement** (bulk follow/like/reply) — highest risk.
2. **Many accounts from one IP / one fingerprint** — sybil clustering.
3. **Posting velocity** no human sustains.
4. **New account + immediate link-posting** — classic spam shape. An aged account
   is safer; this one is aged, keep it that way.

Posting one link per day from an aged account is *not* a suspension risk. Doing it
500× per hour is.

---

## Running things

| Task | Command |
|---|---|
| Check in (signed) | `./checkin.sh` |
| Say something signed | `./say.sh <room> "text"` |
| Verify footprint | `./check.sh` |
| Push repo | `./push.sh` |
| Post to X (dry run first) | `scripts/post_x.sh --dry-run` |
| Post to X (live) | `scripts/post_x.sh --post` |

Auto check-in runs from a systemd user timer with `Persistent=true`, every 6h.
Persistent catches **one** missed run after boot, not all of them — that is
enough. The referee needs proof the identity existed, not a count of records.

---

## Open questions

Tracked in `STATE.md`. Do not resolve them by guessing.
