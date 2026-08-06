#!/usr/bin/env python3
"""Restore study-system UI to V7 forest style (pre-anime)."""
from pathlib import Path
import re

path = Path(__file__).resolve().parents[1] / "index.html"
html = path.read_text(encoding="utf-8")

# Paths: icons-v7, no anime bg
html = html.replace("/static/assets/icons-v10/", "/static/assets/icons-v7/")
html = html.replace("const ASSET = '/static/assets/icons-v10/';", "const ASSET = '/static/assets/icons-v7/';")
html = html.replace("/static/assets/icons/", "/static/assets/icons-v7/")  # any leftover
html = html.replace("const ASSET = '/static/assets/icons/';", "const ASSET = '/static/assets/icons-v7/';")

# Remove background image layers → soft forest gradient only
html = re.sub(
    r"body\{\s*font-family:var\(--font-ui\);.*?padding:0 0 90px;\s*\}",
    """body{
  font-family:var(--font-ui);
  background:
    radial-gradient(1200px 500px at 50% -10%, rgba(107,143,113,.18), transparent 60%),
    radial-gradient(800px 400px at 100% 20%, rgba(196,137,74,.08), transparent 50%),
    linear-gradient(180deg, #e4ecdf 0%, var(--bg) 45%, #e2e9dc 100%);
  color:var(--text);
  min-height:100dvh;
  padding:0 0 90px;
}""",
    html,
    count=1,
    flags=re.S,
)

# Remove dark body bg image overrides if present
html = re.sub(
    r"\[data-theme=\"dark\"\] body\{[^}]*\}",
    "",
    html,
    count=1,
    flags=re.S,
)

# Learning overlay: solid/soft bg, no image
html = re.sub(
    r"\.learning-overlay\{position:fixed;inset:0;z-index:90;[^}]*\}",
    ".learning-overlay{position:fixed;inset:0;z-index:90;background:var(--bg);display:none;flex-direction:column}",
    html,
    count=1,
    flags=re.S,
)
html = re.sub(
    r"\[data-theme=\"dark\"\] \.learning-overlay\{[^}]*\}",
    "",
    html,
    count=1,
    flags=re.S,
)

# Forest palette (V7) instead of anime pastel
html = re.sub(
    r":root \{.*?\nimg\.ui-icon,img\.ui-icon-nav,img\.ui-icon-logo,img\.ui-icon-avatar,img\.ui-icon-sm,img\.ui-icon-md,img\.ui-icon-lg,img\.ui-icon-xl\{user-select:none;-webkit-user-drag:none\}",
    r""":root {
  --green-1: #4a7c59;
  --green-2: #3a6348;
  --green-bg: rgba(74,124,89,.14);
  --blue-1: #5b8a8a;
  --blue-2: #4a7272;
  --orange-1: #c4894a;
  --red-1: #b05a4a;
  --yellow-1: #d4a84b;
  --purple-1: #7a8f71;
  --text: #2c3a2e;
  --text-sub: #6d7b6e;
  --bg: #e9efe4;
  --card: #faf7f0;
  --card-border: #d5dece;
  --shadow: rgba(44,58,46,.08);
  --radius: 18px;
  --radius-sm: 14px;
  --font-ui: -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC",sans-serif;
  --moss: #6b8f71;
  --bark: #8b6b4a;
}
[data-theme="dark"] {
  --text: #e6ede4;
  --text-sub: #9aab9c;
  --bg: #161e18;
  --card: #1f2a22;
  --card-border: #334038;
  --shadow: rgba(0,0,0,.4);
  --green-bg: rgba(107,143,113,.16);
}

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{
  font-family:var(--font-ui);
  background:
    radial-gradient(1200px 500px at 50% -10%, rgba(107,143,113,.18), transparent 60%),
    radial-gradient(800px 400px at 100% 20%, rgba(196,137,74,.08), transparent 50%),
    linear-gradient(180deg, #e4ecdf 0%, var(--bg) 45%, #e2e9dc 100%);
  color:var(--text);
  min-height:100dvh;
  padding:0 0 90px;
}
.app{max-width:480px;margin:0 auto;padding:16px}
.ui-icon{width:1.25em;height:1.25em;object-fit:cover;border-radius:8px;vertical-align:-.2em;display:inline-block;box-shadow:0 1px 3px var(--shadow)}
.ui-icon-sm{width:18px;height:18px;border-radius:5px}
.ui-icon-md{width:26px;height:26px;border-radius:8px}
.ui-icon-lg{width:44px;height:44px;border-radius:12px}
.ui-icon-xl{width:72px;height:72px;border-radius:16px;box-shadow:0 4px 14px var(--shadow)}
.ui-icon-nav{width:24px;height:24px;border-radius:7px;display:block;margin:0 auto 3px;box-shadow:none}
.ui-icon-logo{width:30px;height:30px;border-radius:9px}
.ui-icon-avatar{width:32px;height:32px;border-radius:50%;object-fit:cover;box-shadow:0 0 0 2px var(--card)}
img.ui-icon,img.ui-icon-nav,img.ui-icon-logo,img.ui-icon-avatar,img.ui-icon-sm,img.ui-icon-md,img.ui-icon-lg,img.ui-icon-xl{user-select:none;-webkit-user-drag:none}""",
    html,
    count=1,
    flags=re.S,
)

# Buttons back to forest (not super pastel anime)
html = html.replace(
    ".btn-primary{background:linear-gradient(180deg,#86d492,#6bbf7a);color:#fff;box-shadow:0 3px 0 var(--green-2),0 8px 18px rgba(107,191,122,.28);border-radius:999px}",
    ".btn-primary{background:linear-gradient(180deg,#5a8f69,#4a7c59);color:#fff;box-shadow:0 3px 0 var(--green-2),0 6px 16px rgba(74,124,89,.22)}",
)
html = html.replace(
    ".btn-primary:hover{background:linear-gradient(180deg,#78ca86,#5fb56e)}",
    ".btn-primary:hover{background:var(--green-2)}",
)
html = html.replace(
    ".btn-secondary{background:var(--card);color:var(--text);border:2px solid var(--card-border);border-radius:999px}",
    ".btn-secondary{background:var(--card);color:var(--text);border:2px solid var(--card-border)}",
)
html = html.replace(
    ".add-btn{background:linear-gradient(180deg,#86d492,#6bbf7a);color:#fff;border:none;border-radius:50%;width:56px;height:56px;font-size:28px;cursor:pointer;box-shadow:0 6px 16px rgba(107,191,122,.35);transition:all .1s;display:inline-flex;align-items:center;justify-content:center}",
    ".add-btn{background:linear-gradient(180deg,#5a8f69,#4a7c59);color:#fff;border:none;border-radius:50%;width:56px;height:56px;font-size:28px;cursor:pointer;box-shadow:0 4px 12px rgba(74,124,89,.3);transition:all .1s;display:inline-flex;align-items:center;justify-content:center}",
)
html = html.replace(
    ".msg.user .msg-bubble{background:linear-gradient(180deg,#86d492,#6bbf7a);color:#fff;border-bottom-right-radius:4px}",
    ".msg.user .msg-bubble{background:linear-gradient(180deg,#5a8f69,#4a7c59);color:#fff;border-bottom-right-radius:4px}",
)
html = html.replace(
    ".xp-bar-fill{height:100%;background:linear-gradient(90deg,#f0a35e,#86d492);border-radius:99px;transition:width .6s ease}",
    ".xp-bar-fill{height:100%;background:linear-gradient(90deg,var(--bark),var(--moss));border-radius:99px;transition:width .6s ease}",
)
html = html.replace(
    ".card{background:rgba(255,255,255,.92);border:1px solid var(--card-border);border-radius:var(--radius);padding:24px 20px;margin-bottom:12px;box-shadow:0 6px 20px var(--shadow);backdrop-filter:blur(6px)}",
    ".card{background:var(--card);border:1px solid var(--card-border);border-radius:var(--radius);padding:24px 20px;margin-bottom:12px;box-shadow:0 6px 20px var(--shadow)}",
)
html = html.replace(
    'style="background:linear-gradient(180deg,#6a9a9a,#5b8a8a);box-shadow:0 3px 0 var(--blue-2)"',
    'style="background:linear-gradient(180deg,#6a9a9a,#5b8a8a);box-shadow:0 3px 0 var(--blue-2)"',
)

# Badge → simple v7
html = re.sub(
    r'<span id="buildTag"[^>]*>.*?</span>',
    '<span id="buildTag" title="V7" style="font-size:10px;font-weight:600;color:var(--text-sub);margin-left:6px;vertical-align:middle">v7</span>',
    html,
    count=1,
)

# Ensure ASSET path is icons-v7
if "const ASSET" in html:
    html = re.sub(
        r"const ASSET = '/static/assets/icons[^']*/';",
        "const ASSET = '/static/assets/icons-v7/';",
        html,
        count=1,
    )

# favicon
html = re.sub(
    r'href="/static/assets/icons[^"]*favicon\.jpg[^"]*"',
    'href="/static/assets/icons-v7/favicon.jpg"',
    html,
)

# strip any remaining bg-anime / icons-v10
html = html.replace("bg-anime-v10.jpg", "")
html = html.replace("bg-forest-anime.jpg", "")
html = html.replace("icons-v10", "icons-v7")

path.write_text(html, encoding="utf-8")
print("ASSET", re.search(r"const ASSET = '([^']+)'", html).group(1))
print("badge", "v7" in html and "v10" not in html)
print("bg image left", "bg-anime" in html or "bg-forest-anime" in html)
print("icons-v7 count in html", html.count("icons-v7"))
