#!/usr/bin/env python3
"""
Passionwaves Media — site builder.

Workflow:
  1. Write an article as Markdown in  content/your-slug.md  (with a small header).
  2. Run:  python3 build.py
  3. Upload everything in  public/  to your S3 bucket.

That's it. You never edit HTML by hand. No pip installs — pure standard library.
"""
import html
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent
PUBLIC = ROOT / "public"

# ----------------------------------------------------------------------
# Tiny Markdown -> HTML (enough for articles: headings, lists, quotes,
# code, links, images, bold/italic, rules).
# ----------------------------------------------------------------------
def _inline(text):
    codes = []
    text = re.sub(r"`([^`]+)`", lambda m: (codes.append(m.group(1)), f"\x00{len(codes)-1}\x00")[1], text)
    text = html.escape(text, quote=False)
    text = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1">', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    text = re.sub(r"\x00(\d+)\x00", lambda m: "<code>" + html.escape(codes[int(m.group(1))], quote=False) + "</code>", text)
    return text


def md_to_html(md):
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if line.strip() == "":
            i += 1; continue
        if line.strip().startswith("```"):
            i += 1; buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            out.append("<pre><code>" + html.escape("\n".join(buf), quote=False) + "</code></pre>")
            continue
        if re.match(r"^\s*-{3,}\s*$", line):
            out.append("<hr>"); i += 1; continue
        h = re.match(r"^(#{1,4})\s+(.*)$", line)
        if h:
            lvl = len(h.group(1)); out.append(f"<h{lvl}>{_inline(h.group(2).strip())}</h{lvl}>"); i += 1; continue
        if line.lstrip().startswith(">"):
            buf = []
            while i < len(lines) and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
            out.append("<blockquote>" + _inline(" ".join(buf)) + "</blockquote>"); continue
        if re.match(r"^\s*[-*]\s+", line):
            buf = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                buf.append(re.sub(r"^\s*[-*]\s+", "", lines[i])); i += 1
            out.append("<ul>" + "".join(f"<li>{_inline(x)}</li>" for x in buf) + "</ul>"); continue
        if re.match(r"^\s*\d+\.\s+", line):
            buf = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                buf.append(re.sub(r"^\s*\d+\.\s+", "", lines[i])); i += 1
            out.append("<ol>" + "".join(f"<li>{_inline(x)}</li>" for x in buf) + "</ol>"); continue
        buf = []
        while (i < len(lines) and lines[i].strip() != ""
               and not re.match(r"^(#{1,4})\s|^\s*[-*]\s+|^\s*\d+\.\s+|^\s*>", lines[i])
               and not lines[i].strip().startswith("```")):
            buf.append(lines[i]); i += 1
        out.append("<p>" + _inline(" ".join(buf)) + "</p>")
    return "\n".join(out)


def parse_md(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    meta, body = {}, text
    if m:
        for l in m.group(1).splitlines():
            if ":" in l:
                k, v = l.split(":", 1); meta[k.strip()] = v.strip()
        body = m.group(2)
    return meta, body


# ----------------------------------------------------------------------
# HTML building blocks
# ----------------------------------------------------------------------
WAVE = ('<svg viewBox="0 0 24 16" fill="none"><path d="M2 10 q3 -6 6 0 t6 0 t6 0" '
        'stroke="#fff" stroke-width="2.2" stroke-linecap="round"/></svg>')

LINKEDIN = ('<svg viewBox="0 0 24 24" fill="currentColor"><path d="M4.98 3.5C4.98 4.88 3.87 6 2.5 6S0 4.88 0 3.5 '
            '1.12 1 2.5 1 4.98 2.12 4.98 3.5zM0 8h5v16H0V8zm7.5 0h4.78v2.19h.07c.67-1.27 2.3-2.61 4.73-2.61 '
            '5.06 0 6 3.33 6 7.66V24h-5v-6.99c0-1.67-.03-3.82-2.33-3.82-2.33 0-2.69 1.82-2.69 3.7V24h-5V8z"/></svg>')
XICON = ('<svg viewBox="0 0 24 24" fill="currentColor"><path d="M18.24 2H21l-6.55 7.48L22 22h-6.15l-4.82-6.3L5.5 22H2.74'
         'l7.01-8-7.4-12h6.3l4.36 5.77L18.24 2zm-1.08 18h1.7L7.02 3.9H5.2L17.16 20z"/></svg>')

HEART = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M12 21s-7.5-4.6-10-9.2'
         'C.4 8.4 2 5 5.3 5c2 0 3.3 1.1 4.7 2.8C11.4 6.1 12.7 5 14.7 5 18 5 19.6 8.4 22 11.8 19.5 16.4 12 21 12 21z"/></svg>')
EYE = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M1 12s4-7 11-7 11 7 11 7'
       '-4 7-11 7S1 12 1 12z"/><circle cx="12" cy="12" r="3"/></svg>')

_TS = " ".join(["t180 0"] * 17)  # 17 half-periods after the opening curve
HERO_WAVE = f'''<div class="wave-wrap" aria-hidden="true">
  <svg viewBox="0 0 1440 150" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
    <defs><linearGradient id="wg" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="720" y2="0" spreadMethod="repeat">
      <stop offset="0%" stop-color="#FF6B4A"/><stop offset="25%" stop-color="#E5468A"/>
      <stop offset="50%" stop-color="#6B4EE6"/><stop offset="75%" stop-color="#22B0C4"/>
      <stop offset="100%" stop-color="#FF6B4A"/>
    </linearGradient></defs>
    <g class="wave-flow f3" opacity="0.26"><path fill="none" stroke="url(#wg)" stroke-width="1.5" stroke-linecap="round" d="M-720 50 q90 -26 180 0 {_TS}"/></g>
    <g class="wave-flow f2" opacity="0.5"><path fill="none" stroke="url(#wg)" stroke-width="2" stroke-linecap="round" d="M-720 95 q90 -30 180 0 {_TS}"/></g>
    <g class="wave-flow f1" opacity="0.95"><path fill="none" stroke="url(#wg)" stroke-width="2.5" stroke-linecap="round" d="M-720 70 q90 -40 180 0 {_TS}"/></g>
  </svg></div>'''


def brand(cfg, sm=False):
    cls = "brand brand--sm" if sm else "brand"
    return (f'<a href="index.html" class="{cls}"><span class="brand-mark" aria-hidden="true">{WAVE}</span>'
            f'<span class="brand-text">{cfg["brandName"]}</span></a>')


def dot(color):
    return f'<span class="dot" style="background:{color}"></span>'


def footer(cfg):
    cats = '<a href="articles.html">All articles</a>' + "".join(f'<a href="articles.html#{c}">{c}</a>' for c in cfg["categories"])
    soc = ""
    if cfg["social"].get("linkedin"):
        soc += f'<a href="{cfg["social"]["linkedin"]}" target="_blank" rel="noopener">{LINKEDIN}LinkedIn</a>'
    if cfg["social"].get("x"):
        soc += f'<a href="{cfg["social"]["x"]}" target="_blank" rel="noopener">{XICON}X</a>'
    return f'''<footer class="footer"><div class="wrap">
  <div class="footer-top">
    <div>{brand(cfg, sm=True)}<p class="colophon">Spreading passions from me to the world — one article, one wave, at a time.</p></div>
    <nav>
      <div class="col"><h4>Read</h4>{cats}</div>
      <div class="col"><h4>More</h4><a href="index.html#mission">About</a><a href="index.html#subscribe">Subscribe</a></div>
      <div class="col"><h4>Elsewhere</h4>{soc}</div>
    </nav>
  </div>
  <div class="base mono">© {datetime.now().year} {cfg["brandName"]} · Built and hosted on AWS</div>
</div></footer>'''


def card_html(cfg, p, idx=0, extra=False):
    col = cfg["categories"].get(p["category"], "#999")
    cls = "card reveal in extra" if extra else "card reveal"
    return (f'<a href="{p["slug"]}.html" class="{cls}" style="--i:{idx}" data-cat="{p["category"]}">'
            f'<span class="catline mono">{dot(col)}{p["category"]}</span>'
            f'<h3>{p["title"]}</h3><p>{p["excerpt"]}</p>'
            f'<div class="foot mono"><span>{p["card_date"]} · {p["minutes"]} min</span></div></a>')


def nav(cfg, home=False, active=""):
    about = "#mission" if home else "index.html#mission"
    sub = "#subscribe" if home else "index.html#subscribe"
    def cls(x):
        return "navlink active" if x == active else "navlink"
    return (f'<header class="masthead"><div class="wrap masthead-inner">{brand(cfg)}<nav class="nav">'
            f'<a class="{cls("read")}" href="articles.html">Read</a>'
            f'<a class="{cls("about")}" href="{about}">About</a>'
            f'<a href="{sub}"><button class="btn btn-grad" style="padding:9px 18px;font-size:14.5px">Subscribe</button></a>'
            f'</nav></div></header>')


def subscribe_section(cfg):
    if not cfg["newsletter"].get("enabled"):
        return ""
    action = cfg["newsletter"].get("action", "")
    action_attr = f'action="{action}"' if action else ""
    return f'''<section class="section subscribe" id="subscribe"><div class="wrap">
  <div class="sub-band reveal"><div class="ribbon"></div>
    <div class="mono">The list</div>
    <h2>Get new pieces the moment they're out.</h2>
    <p>No account, no noise — just the next article in your inbox. Unsubscribe in one click, anytime.</p>
    <form class="signup" {action_attr} method="post" target="_blank" onsubmit="return pwSubscribe(this)">
      <input type="email" name="email" aria-label="Email address" placeholder="you@email.com" required>
      <button class="btn btn-grad" type="submit">Subscribe free</button>
    </form>
    <p class="signup-note">Free forever · No spam, ever.</p>
  </div></div></section>'''


def page_head(cfg, title, desc, canonical, jsonld):
    fonts = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" '
             'href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?'
             'family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;1,9..144,400;1,9..144,500'
             '&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">')
    return f'''<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{html.escape(desc, quote=True)}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{html.escape(title, quote=True)}">
<meta property="og:description" content="{html.escape(desc, quote=True)}">
<meta property="og:image" content="{cfg['domain']}/og-cover.jpg">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{jsonld}</script>
{fonts}
<style>{STYLES}</style></head><body>'''


def page_tail(cfg, init_js=""):
    pw = json.dumps({"supabaseUrl": cfg["supabase"].get("url", ""), "supabaseAnonKey": cfg["supabase"].get("anonKey", "")})
    return f'<script>window.PW={pw};</script>\n<script>{APP_JS}</script>\n<script>{init_js}</script>\n</body></html>'


# ----------------------------------------------------------------------
# Pages
# ----------------------------------------------------------------------
def build_index(cfg, posts):
    featured = next((p for p in posts if p.get("featured")), posts[0] if posts else None)
    feat_html = ""
    if featured:
        col = cfg["categories"].get(featured["category"], "#999")
        feat_html = f'''<a href="{featured['slug']}.html" class="feature reveal">
  <div class="art"><div class="coord mono">{featured['category']} · {featured['minutes']} min</div></div>
  <div class="body"><span class="catline mono">{dot(col)}Featured</span>
    <h3>{featured['title']}</h3><p>{featured['excerpt']}</p><span class="readmore">Read the article</span></div></a>'''

    latest = [q for q in posts if q is not featured][:6]
    cards = "".join(card_html(cfg, p, i) for i, p in enumerate(latest))

    mission = cfg["mission"]
    mission_body = "".join(f"<p>{b}</p>" for b in mission["body"])
    mission_html = f'''<section class="section mission" id="mission"><div class="wrap mission-inner">
  <div class="reveal"><div class="mono">The idea</div><h2>{mission['heading']}</h2></div>
  <div class="reveal">{mission_body}<p class="sig">{mission['sig']}</p></div></div></section>'''

    body = f'''{nav(cfg, home=True)}
<section class="hero"><div class="wrap">
  <div class="mono eyebrow">{cfg['hero']['eyebrow']}</div>
  <h1>{cfg['hero']['titleHtml']}</h1>
  <p class="lede">{cfg['hero']['lede']}</p>
  <div class="cues"><a href="#latest"><button class="btn btn-grad">Start reading</button></a>
  <a href="#mission"><button class="btn btn-ghost">Why this exists</button></a></div>
</div>{HERO_WAVE}</section>

<section class="section" id="latest"><div class="wrap">
  <div class="section-head reveal"><h2>Latest</h2><p>The newest dispatches — browse everything in the archive.</p></div>
  {feat_html}
  <div class="grid" id="grid">{cards}</div>
  <div class="more-cta reveal"><a href="articles.html"><button class="btn btn-ghost">Browse all articles →</button></a></div>
</div></section>

{mission_html}
{subscribe_section(cfg)}
{footer(cfg)}'''

    jsonld = json.dumps({"@context": "https://schema.org", "@type": "Blog",
                         "name": f'{cfg["brandName"]}', "url": cfg["domain"] + "/"})
    head = page_head(cfg, f'{cfg["brandName"]} — spreading what I love, from me to you',
                     "A personal publication spreading one person's passions to the world — AWS, travel, food, and life.",
                     cfg["domain"] + "/", jsonld)
    (PUBLIC / "index.html").write_text(head + body + page_tail(cfg), encoding="utf-8")


def build_archive(cfg, posts):
    total = len(posts)
    chips = '<button class="chip" aria-pressed="true" onclick="pwArchiveFilter(this,\'all\')">All</button>'
    groups = ""
    for cat, color in cfg["categories"].items():
        in_cat = [p for p in posts if p["category"] == cat]
        if not in_cat:
            continue
        chips += f'<button class="chip" aria-pressed="false" onclick="pwArchiveFilter(this,\'{cat}\')">{dot(color)}{cat}</button>'
        cards = "".join(card_html(cfg, p, i, extra=(i >= 12)) for i, p in enumerate(in_cat))
        more = f'<button class="show-more" onclick="pwShowMore(this)">Show all {len(in_cat)} in {cat}</button>' if len(in_cat) > 12 else ""
        groups += f'''<div class="cat-group reveal" data-cat="{cat}" id="{cat}">
  <h3 class="cat-head">{dot(color)}{cat}<span class="cat-count">{len(in_cat)}</span></h3>
  <div class="grid">{cards}</div>{more}</div>'''

    body = f'''{nav(cfg, active="read")}
<section class="section" style="padding-top:56px"><div class="wrap">
  <div class="section-head reveal"><h2>All articles</h2><p>{total} pieces, organized by passion.</p></div>
  <div class="filters reveal" role="group" aria-label="Filter by category">{chips}</div>
  {groups}
</div></section>
{footer(cfg)}'''

    jsonld = json.dumps({"@context": "https://schema.org", "@type": "CollectionPage",
                         "name": f'All articles — {cfg["brandName"]}', "url": cfg["domain"] + "/articles.html"})
    head = page_head(cfg, f'All articles — {cfg["brandName"]}',
                     "Browse the full archive, organized by category.",
                     cfg["domain"] + "/articles.html", jsonld)
    (PUBLIC / "articles.html").write_text(head + body + page_tail(cfg, "pwArchiveInit();"), encoding="utf-8")


def build_article(cfg, p):
    col = cfg["categories"].get(p["category"], "#999")
    header = nav(cfg)

    reactions = f'''<div class="reactions">
  <button class="like-btn" id="likeBtn" aria-label="Like this article">{HEART}<span id="likeCount">0</span></button>
  <span class="views">{EYE}<span id="viewCount"></span></span></div>'''

    body = f'''{header}
<article>
  <div class="article a-head">
    <a href="index.html#read" class="back">← All articles</a>
    <div class="kicker mono"><span class="dot" style="background:{col}"></span>{p['category']} · {p['minutes']} min read · {p['display_date']}</div>
    <h1>{p['title']}</h1>
    <p class="dek">{p['excerpt']}</p>
    <div class="byline"><div class="avatar"></div><div class="who"><b>{cfg['author']['name']}</b><br><span>{cfg['author']['role']}</span></div></div>
  </div>
  <div class="article"><div class="hero-art"><div class="caption mono">{p['category']}</div></div>
    <div class="prose">{p['html']}<div class="endmark">〜</div></div>
    {reactions}
  </div>
</article>
<div class="more"><div class="mono">Enjoyed this?</div>
  <p style="margin:0 0 20px;color:var(--muted)">New articles go out by email the moment they're published — free, no account needed.</p>
  <a href="index.html#subscribe"><button class="btn btn-grad">Subscribe free</button></a></div>
{footer(cfg)}'''

    jsonld = json.dumps({"@context": "https://schema.org", "@type": "Article", "headline": p["title"],
                         "datePublished": p["iso"], "author": {"@type": "Person", "name": cfg["author"]["name"]},
                         "publisher": {"@type": "Organization", "name": f'{cfg["brandName"]}'}})
    head = page_head(cfg, f'{p["title"]} — {cfg["brandName"]}',
                     p["excerpt"], f'{cfg["domain"]}/{p["slug"]}.html', jsonld)
    (PUBLIC / f'{p["slug"]}.html').write_text(head + body + page_tail(cfg, f'pwInitArticle("{p["slug"]}");'), encoding="utf-8")


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    global STYLES, APP_JS
    cfg = json.loads((ROOT / "site.json").read_text(encoding="utf-8"))
    STYLES = (ROOT / "assets" / "styles.css").read_text(encoding="utf-8")
    APP_JS = (ROOT / "assets" / "app.js").read_text(encoding="utf-8") + (
        "\nwindow.pwSubscribe=function(f){if(!f.getAttribute('action')){"
        "alert('Newsletter is not connected yet — see the README to add your email provider.');return false;}return true;};")

    posts = []
    for md_file in sorted((ROOT / "content").glob("*.md")):
        meta, body = parse_md(md_file.read_text(encoding="utf-8"))
        dt = datetime.strptime(meta["date"], "%Y-%m-%d")
        words = len(re.findall(r"\w+", body))
        posts.append({
            "title": meta["title"], "slug": meta.get("slug", md_file.stem),
            "category": meta.get("category", "Life"), "excerpt": meta.get("excerpt", ""),
            "featured": str(meta.get("featured", "")).lower() == "true",
            "iso": meta["date"], "dt": dt,
            "display_date": dt.strftime("%d %b %Y"), "card_date": dt.strftime("%b %Y"),
            "minutes": max(1, round(words / 200)), "html": md_to_html(body),
        })
    posts.sort(key=lambda p: p["dt"], reverse=True)

    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    PUBLIC.mkdir()

    images_dir = ROOT / "assets" / "images"
    if images_dir.exists():
        shutil.copytree(images_dir, PUBLIC / "assets" / "images")

    build_index(cfg, posts)
    build_archive(cfg, posts)
    for p in posts:
        build_article(cfg, p)

    # robots + sitemap
    (PUBLIC / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {cfg['domain']}/sitemap.xml\n", encoding="utf-8")
    urls = [f"  <url><loc>{cfg['domain']}/</loc><priority>1.0</priority></url>",
            f"  <url><loc>{cfg['domain']}/articles.html</loc><priority>0.9</priority></url>"]
    urls += [f"  <url><loc>{cfg['domain']}/{p['slug']}.html</loc><priority>0.8</priority></url>" for p in posts]
    (PUBLIC / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(urls) + "\n</urlset>\n")

    print(f"✓ Built {len(posts)} articles → {PUBLIC}/")
    for p in posts:
        flag = " (featured)" if p["featured"] else ""
        print(f"  · {p['slug']}.html  [{p['category']}]{flag}")
    print("\nUpload everything in public/ to your S3 bucket.")


if __name__ == "__main__":
    main()
