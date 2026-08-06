#!/usr/bin/env python3
from pathlib import Path
import re

path = Path(__file__).resolve().parents[1] / "index.html"
html = path.read_text(encoding="utf-8")

pat = re.compile(
    r":root \{.*?\nimg\.ui-icon,img\.ui-icon-nav,img\.ui-icon-logo,img\.ui-icon-avatar,img\.ui-icon-sm,img\.ui-icon-md,img\.ui-icon-lg,img\.ui-icon-xl\{user-select:none;-webkit-user-drag:none\}",
    re.S,
)
new = r""":root {
  --green-1: #6bbf7a;
  --green-2: #4ea05e;
  --green-bg: rgba(107,191,122,.16);
  --blue-1: #7eb8d4;
  --blue-2: #5f9dbd;
  --orange-1: #f0a35e;
  --red-1: #e57a7a;
  --yellow-1: #f2d066;
  --purple-1: #b39ddb;
  --text: #3d4a42;
  --text-sub: #889690;
  --bg: #f3faf4;
  --card: #ffffff;
  --card-border: #e0eee3;
  --shadow: rgba(80,120,90,.10);
  --radius: 20px;
  --radius-sm: 14px;
  --font-ui: -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC",sans-serif;
  --moss: #7bc48a;
  --bark: #d4a574;
}
[data-theme="dark"] {
  --text: #e8f2ea;
  --text-sub: #9bb5a3;
  --bg: #1a2420;
  --card: #24302a;
  --card-border: #354840;
  --shadow: rgba(0,0,0,.4);
  --green-bg: rgba(107,191,122,.14);
}

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{
  font-family:var(--font-ui);
  background:
    radial-gradient(900px 420px at 20% -5%, rgba(126,184,212,.20), transparent 55%),
    radial-gradient(800px 400px at 100% 10%, rgba(179,157,219,.14), transparent 50%),
    radial-gradient(700px 360px at 50% 100%, rgba(107,191,122,.12), transparent 50%),
    linear-gradient(180deg, #eef8f1 0%, var(--bg) 50%, #eaf6ee 100%);
  color:var(--text);
  min-height:100dvh;
  padding:0 0 90px;
}
.app{max-width:480px;margin:0 auto;padding:16px}
.ui-icon{width:1.25em;height:1.25em;object-fit:cover;border-radius:10px;vertical-align:-.2em;display:inline-block;box-shadow:0 0 0 1.5px var(--card-border);background:#fff}
.ui-icon-sm{width:20px;height:20px;border-radius:7px}
.ui-icon-md{width:28px;height:28px;border-radius:9px}
.ui-icon-lg{width:48px;height:48px;border-radius:14px}
.ui-icon-xl{width:80px;height:80px;border-radius:22px;box-shadow:0 0 0 2px var(--card-border),0 8px 20px var(--shadow)}
.ui-icon-nav{width:26px;height:26px;border-radius:9px;display:block;margin:0 auto 3px;box-shadow:0 0 0 1.5px var(--card-border);background:#fff}
.ui-icon-logo{width:32px;height:32px;border-radius:11px;box-shadow:0 0 0 1.5px var(--card-border)}
.ui-icon-avatar{width:34px;height:34px;border-radius:50%;object-fit:cover;box-shadow:0 0 0 2px #fff,0 0 0 3px var(--card-border);background:#fff}
img.ui-icon,img.ui-icon-nav,img.ui-icon-logo,img.ui-icon-avatar,img.ui-icon-sm,img.ui-icon-md,img.ui-icon-lg,img.ui-icon-xl{user-select:none;-webkit-user-drag:none}"""

m = pat.search(html)
if not m:
    raise SystemExit("css block not found")
html = html[: m.start()] + new + html[m.end() :]

html = html.replace("v8 · 森林", "v9 · 動漫")
html = html.replace('title="Forest UI"', 'title="Anime UI"')
html = html.replace(
    ".btn-secondary{background:var(--card);color:var(--text);border:2px solid var(--card-border)}",
    ".btn-secondary{background:var(--card);color:var(--text);border:2px solid var(--card-border);border-radius:999px}",
)

# cache bust icons
html = html.replace("${ASSET}${name}.jpg", "${ASSET}${name}.jpg?v=9")
html = html.replace("ASSET + lvl.icon + '.jpg'", "ASSET + lvl.icon + '.jpg?v=9'")
html = html.replace(
    "ASSET + (theme==='dark' ? 'theme-sun' : 'theme-moon') + '.jpg'",
    "ASSET + (theme==='dark' ? 'theme-sun' : 'theme-moon') + '.jpg?v=9'",
)
html = html.replace(
    "ASSET + leaves[Math.floor(Math.random()*leaves.length)] + '.jpg'",
    "ASSET + leaves[Math.floor(Math.random()*leaves.length)] + '.jpg?v=9'",
)
html = re.sub(r'(src="/static/assets/icons/[^"?]+\.jpg)"', r'\1?v=9"', html)

path.write_text(html, encoding="utf-8")
print("ok", "v9 · 動漫" in html, "#6bbf7a" in html)
