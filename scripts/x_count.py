#!/usr/bin/env python3
"""
x_count.py — count a post the way X does.

X collapses every URL to 23 characters (t.co) regardless of its real length.
A plain len() therefore under-counts and lets an over-limit post through.

Usage:
    python3 x_count.py post.txt          # count a file
    python3 x_count.py --text "hello"    # count a literal

Exit 1 if over the 280 weighted limit, so scripts can gate on it.
"""
import argparse, pathlib, re, sys

LIMIT = 280
URL_RE = re.compile(r"https?://\S+|\b(?:[a-z0-9-]+\.)+[a-z]{2,}(?:/\S*)?", re.I)


def weighted(text: str):
    total, pos, parts = 0, 0, []
    for m in URL_RE.finditer(text):
        pre = text[pos:m.start()]
        total += len(pre)
        if pre:
            parts.append((len(pre), "text"))
        total += 23
        parts.append((23, f"url: {m.group(0)[:52]} (raw {len(m.group(0))})"))
        pos = m.end()
    tail = text[pos:]
    total += len(tail)
    if tail:
        parts.append((len(tail), "text"))
    return total, parts


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("file", nargs="?", help="file containing the post text")
    g.add_argument("--text", help="post text as a literal")
    a = ap.parse_args()

    text = pathlib.Path(a.file).read_text() if a.file else a.text
    n, parts = weighted(text)

    print(f"raw chars  : {len(text)}")
    print(f"X-weighted : {n} / {LIMIT}")
    for w, d in parts:
        print(f"   {w:4}  {d}")

    if n > LIMIT:
        print(f"\nOVER LIMIT by {n - LIMIT} — Post button will be disabled.")
        return 1
    print(f"\nOK — {LIMIT - n} chars to spare.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
