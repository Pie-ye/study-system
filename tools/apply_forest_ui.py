#!/usr/bin/env python3
"""Apply forest theme + image icons to index.html (replaces emoji UI)."""
from pathlib import Path
import re

path = Path(__file__).resolve().parents[1] / "index.html"
html = path.read_text(encoding="utf-8")

def must_replace(old: str, new: str, label: str):
    global html
    if old not in html:
        print(f"WARN missing: {label}")
        return False
    html = html.replace(old, new)
    return True

# 1) Favicon
must_replace(
    "<link rel=\"icon\" href=\"data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><text y='28' font-size='28'>🌱</text></svg>\">",
    '<link rel="icon" href="/static/assets/icons/favicon.jpg" type="image/jpeg">',
    "favicon",
)

# 2) CSS root + body
old_root = ''':root {
  --green-1: #58cc02;
  --green-2: #46a302;
  --green-bg: rgba(88,204,2,.15);
  --blue-1: #1cb0f6;
  --blue-2: #1899d6;
  --orange-1: #ff9600;
  --red-1: #ff4b4b;
  --yellow-1: #ffc800;
  --purple-1: #ce82ff;
  --text: #4b4b4b;
  --text-sub: #afafaf;
  --bg: #f7f7f7;
  --card: #fff;
  --card-border: #e5e5e5;
  --shadow: rgba(0,0,0,.08);
  --radius: 16px;
  --radius-sm: 12px;
  --font: -apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans TC",sans-serif;
}
[data-theme="dark"] {
  --text: #e0e0e0;
  --text-sub: #888;
  --bg: #1a1a2e;
  --card: #16213e;
  --card-border: #2a2a4a;
  --shadow: rgba(0,0,0,.3);
  --green-bg: rgba(88,204,2,.12);
}

*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:var(--font);background:var(--bg);color:var(--text);min-height:100dvh;padding:0 0 90px}
.app{max-width:480px;margin:0 auto;padding:16px}'''

new_root = ''':root {
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
.ui-icon{width:1.25em;height:1.25em;object-fit:cover;border-radius:7px;vertical-align:-.2em;display:inline-block;box-shadow:0 1px 2px var(--shadow)}
.ui-icon-sm{width:18px;height:18px;border-radius:5px}
.ui-icon-md{width:26px;height:26px;border-radius:8px}
.ui-icon-lg{width:44px;height:44px;border-radius:12px}
.ui-icon-xl{width:72px;height:72px;border-radius:18px;box-shadow:0 4px 14px var(--shadow)}
.ui-icon-nav{width:24px;height:24px;border-radius:7px;display:block;margin:0 auto 3px;box-shadow:none}
.ui-icon-logo{width:30px;height:30px;border-radius:9px}
.ui-icon-avatar{width:32px;height:32px;border-radius:50%;object-fit:cover;box-shadow:0 0 0 2px var(--card)}
img.ui-icon,img.ui-icon-nav,img.ui-icon-logo,img.ui-icon-avatar,img.ui-icon-sm,img.ui-icon-md,img.ui-icon-lg,img.ui-icon-xl{user-select:none;-webkit-user-drag:none}'''
must_replace(old_root, new_root, "css root")

must_replace(
    ".btn-primary{background:var(--green-1);color:#fff;box-shadow:0 4px 0 var(--green-2)}",
    ".btn-primary{background:linear-gradient(180deg,#5a8f69,#4a7c59);color:#fff;box-shadow:0 3px 0 var(--green-2),0 6px 16px rgba(74,124,89,.22)}",
    "btn-primary",
)
must_replace(
    ".btn-primary:active{box-shadow:0 2px 0 var(--green-2);transform:translateY(2px) scale(.97)}",
    ".btn-primary:active{box-shadow:0 1px 0 var(--green-2);transform:translateY(2px) scale(.97)}",
    "btn-primary active",
)
must_replace(
    ".add-btn{background:var(--green-1);color:#fff;border:none;border-radius:50%;width:56px;height:56px;font-size:28px;cursor:pointer;box-shadow:0 4px 0 var(--green-2);transition:all .1s;display:inline-flex;align-items:center;justify-content:center}",
    ".add-btn{background:linear-gradient(180deg,#5a8f69,#4a7c59);color:#fff;border:none;border-radius:50%;width:56px;height:56px;font-size:28px;cursor:pointer;box-shadow:0 4px 12px rgba(74,124,89,.3);transition:all .1s;display:inline-flex;align-items:center;justify-content:center}",
    "add-btn",
)
must_replace(
    ".completed-state .big-emoji{font-size:60px;margin-bottom:8px}",
    ".completed-state .big-emoji{font-size:60px;margin-bottom:8px;display:flex;justify-content:center}",
    "big-emoji",
)
must_replace(
    ".rex-reminder .rex-emoji{font-size:48px;margin-bottom:4px}",
    ".rex-reminder .rex-emoji{font-size:48px;margin-bottom:4px;display:flex;justify-content:center}",
    "rex-emoji",
)
must_replace(
    ".confetti{position:fixed;pointer-events:none;z-index:300;font-size:18px;animation:confetti-fall 1.5s ease forwards}",
    ".confetti{position:fixed;pointer-events:none;z-index:300;width:22px;height:22px;border-radius:50%;object-fit:cover;animation:confetti-fall 1.5s ease forwards;box-shadow:0 2px 6px rgba(0,0,0,.12)}",
    "confetti css",
)
must_replace(
    ".card{background:var(--card);border:1px solid var(--card-border);border-radius:var(--radius);padding:24px 20px;margin-bottom:12px;box-shadow:0 4px 12px var(--shadow)}",
    ".card{background:var(--card);border:1px solid var(--card-border);border-radius:var(--radius);padding:24px 20px;margin-bottom:12px;box-shadow:0 6px 20px var(--shadow)}",
    "card",
)
must_replace(
    ".bottom-nav{position:fixed;bottom:0;left:0;right:0;background:var(--card);border-top:1px solid var(--card-border);display:flex;z-index:50;box-shadow:0 -2px 8px var(--shadow)}",
    ".bottom-nav{position:fixed;bottom:0;left:0;right:0;background:var(--card);border-top:1px solid var(--card-border);display:flex;z-index:50;box-shadow:0 -4px 20px var(--shadow);opacity:.98}",
    "bottom-nav",
)
must_replace(
    ".msg.teacher .msg-avatar{background:var(--blue-1);color:#fff}",
    ".msg.teacher .msg-avatar{background:transparent;padding:0;overflow:hidden}",
    "teacher avatar",
)
must_replace(
    ".msg.user .msg-avatar{background:var(--green-1);color:#fff}",
    ".msg.user .msg-avatar{background:transparent;padding:0;overflow:hidden}",
    "user avatar",
)
must_replace(
    ".msg.user .msg-bubble{background:var(--green-1);color:#fff;border-bottom-right-radius:4px}",
    ".msg.user .msg-bubble{background:linear-gradient(180deg,#5a8f69,#4a7c59);color:#fff;border-bottom-right-radius:4px}",
    "user bubble",
)
must_replace(
    ".xp-bar-fill{height:100%;background:linear-gradient(90deg,var(--orange-1),var(--yellow-1));border-radius:99px;transition:width .6s ease}",
    ".xp-bar-fill{height:100%;background:linear-gradient(90deg,var(--bark),var(--moss));border-radius:99px;transition:width .6s ease}",
    "xp bar",
)

# 3) Asset helper
if "const ASSET" not in html:
    inject = """
const ASSET = '/static/assets/icons/';
function icon(name, cls='ui-icon'){
  return `<img class="${cls}" src="${ASSET}${name}.jpg" alt="" draggable="false" loading="lazy">`;
}

"""
    must_replace("const LS_KEY = 'studySystem_v1';", "const LS_KEY = 'studySystem_v1';\n" + inject, "ASSET helper")

# 4) Constants
must_replace(
'''const CATEGORY_ICONS = {
  '技術架構':'🏗️','AI / Agent':'🤖','英文學習':'📝','程式開發':'💻','閱讀筆記':'📖','Side Project':'🔧','哲學':'🤔','其他':'📂'
};
const LEVELS = [
  {min:0,name:'種子',icon:'🌱'},
  {min:50,name:'嫩芽',icon:'🌿'},
  {min:130,name:'小樹',icon:'🌳'},
  {min:250,name:'大樹',icon:'🌲'},
  {min:420,name:'竹林',icon:'🎋'},
  {min:650,name:'森林',icon:'🌴'},
  {min:960,name:'山脈',icon:'⛰️'},
  {min:1360,name:'星辰',icon:'⭐'},
  {min:1860,name:'銀河',icon:'🌌'},
  {min:2500,name:'宇宙',icon:'🌠'},
];
const ACHIEVEMENTS = [
  {id:'firstStep',name:'第一步',desc:'第一次完成學習',icon:'🎉'},
  {id:'weekWarrior',name:'一週達人',desc:'連續 7 天學習',icon:'🔥'},
  {id:'monthlyStar',name:'月之星',desc:'連續 30 天學習',icon:'💪'},
  {id:'centuryChampion',name:'百戰王者',desc:'連續 100 天學習',icon:'👑'},
  {id:'polymath',name:'博學家',desc:'學過 5 種不同類別',icon:'🌈'},
  {id:'honestDiary',name:'誠實日記',desc:'寫過 10 次跳過理由',icon:'📝'},
  {id:'firstHabit',name:'習慣起步',desc:'第一次完成習慣',icon:'🏃'},
  {id:'habitWeek',name:'習慣一週',desc:'連續 7 天完成全部習慣',icon:'🔥'},
  {id:'habitMonth',name:'習慣達人',desc:'連續 30 天完成全部習慣',icon:'💪'},
  {id:'habitVariety',name:'多元習慣',desc:'累計 5 種不同習慣類別',icon:'🌈'},
];''',
'''const CATEGORY_ICONS = {
  '技術架構':'cat-arch','AI / Agent':'cat-ai','英文學習':'cat-english','程式開發':'cat-code','閱讀筆記':'cat-read','Side Project':'cat-side','哲學':'cat-phil','其他':'cat-other'
};
const LEVELS = [
  {min:0,name:'種子',icon:'level-seed'},
  {min:50,name:'嫩芽',icon:'level-sprout'},
  {min:130,name:'小樹',icon:'level-sapling'},
  {min:250,name:'大樹',icon:'level-tree'},
  {min:420,name:'竹林',icon:'level-forest'},
  {min:650,name:'森林',icon:'level-forest'},
  {min:960,name:'山脈',icon:'level-mountain'},
  {min:1360,name:'星辰',icon:'level-star'},
  {min:1860,name:'銀河',icon:'level-galaxy'},
  {min:2500,name:'宇宙',icon:'level-cosmos'},
];
const ACHIEVEMENTS = [
  {id:'firstStep',name:'第一步',desc:'第一次完成學習',icon:'icon-done'},
  {id:'weekWarrior',name:'一週達人',desc:'連續 7 天學習',icon:'streak'},
  {id:'monthlyStar',name:'月之星',desc:'連續 30 天學習',icon:'theme-sun'},
  {id:'centuryChampion',name:'百戰王者',desc:'連續 100 天學習',icon:'badge'},
  {id:'polymath',name:'博學家',desc:'學過 5 種不同類別',icon:'nav-queue'},
  {id:'honestDiary',name:'誠實日記',desc:'寫過 10 次跳過理由',icon:'nav-today'},
  {id:'firstHabit',name:'習慣起步',desc:'第一次完成習慣',icon:'level-sprout'},
  {id:'habitWeek',name:'習慣一週',desc:'連續 7 天完成全部習慣',icon:'streak'},
  {id:'habitMonth',name:'習慣達人',desc:'連續 30 天完成全部習慣',icon:'level-tree'},
  {id:'habitVariety',name:'多元習慣',desc:'累計 5 種不同習慣類別',icon:'level-forest'},
];''',
"constants",
)

# 5) Static chrome
static_pairs = [
(
'''    <div class="logo"><span class="leaf">🌱</span> 每日一學 <span id="buildTag" title="Task 007 bugfix" style="font-size:10px;font-weight:600;color:var(--text-sub);margin-left:6px;vertical-align:middle">v7</span></div>
    <button class="theme-btn" onclick="toggleTheme()" title="切換主題" id="themeBtn">🌙</button>''',
'''    <div class="logo"><span class="leaf"><img class="ui-icon-logo" src="/static/assets/icons/logo.jpg" alt=""></span> 每日一學 <span id="buildTag" title="Forest UI" style="font-size:10px;font-weight:600;color:var(--text-sub);margin-left:6px;vertical-align:middle">v8 · 森林</span></div>
    <button class="theme-btn" onclick="toggleTheme()" title="切換主題" id="themeBtn"><img class="ui-icon-md" src="/static/assets/icons/theme-moon.jpg" alt="theme" id="themeBtnImg"></button>'''
),
(
'''    <div class="status-item"><span class="icon">🔥</span> <span id="streakDisplay">0</span> 天</div>
    <div class="status-item"><span class="icon" id="levelIcon">🌱</span> <span id="levelDisplay">種子</span></div>''',
'''    <div class="status-item"><span class="icon"><img class="ui-icon-md" src="/static/assets/icons/streak.jpg" alt=""></span> <span id="streakDisplay">0</span> 天</div>
    <div class="status-item"><span class="icon"><img class="ui-icon-md" id="levelIcon" src="/static/assets/icons/level-seed.jpg" alt=""></span> <span id="levelDisplay">種子</span></div>'''
),
(
'''    <div class="card-label">📋 今日學習</div>''',
'''    <div class="card-label"><img class="ui-icon-sm" src="/static/assets/icons/nav-today.jpg" alt=""> 今日學習</div>'''
),
(
'''    <div class="rex-emoji">💪</div>
    <div class="rex-quote">「藉口不會讓你變強。」</div>
    <p>已經連續跳過 3 次了，今天要不要認真學一個？五分鐘也好。</p>''',
'''    <div class="rex-emoji"><img class="ui-icon-xl" src="/static/assets/icons/icon-owl.jpg" alt=""></div>
    <div class="rex-quote">「小路是一步一步走出來的。」</div>
    <p>已經連續跳過 3 次了，今天要不要在林間小徑上再走一小段？五分鐘也好。</p>'''
),
('''      <span class="nav-icon">📖</span> 今日''', '''      <span class="nav-icon"><img class="ui-icon-nav" src="/static/assets/icons/nav-today.jpg" alt=""></span> 今日'''),
('''      <span class="nav-icon">📚</span> 佇列''', '''      <span class="nav-icon"><img class="ui-icon-nav" src="/static/assets/icons/nav-queue.jpg" alt=""></span> 佇列'''),
('''      <span class="nav-icon">🎯</span> 願望''', '''      <span class="nav-icon"><img class="ui-icon-nav" src="/static/assets/icons/nav-wish.jpg" alt=""></span> 願望'''),
('''      <span class="nav-icon">🏆</span> 成就''', '''      <span class="nav-icon"><img class="ui-icon-nav" src="/static/assets/icons/nav-achieve.jpg" alt=""></span> 成就'''),
('''      <span class="nav-icon">📊</span> 統計''', '''      <span class="nav-icon"><img class="ui-icon-nav" src="/static/assets/icons/nav-stats.jpg" alt=""></span> 統計'''),
('''    <div class="section-title">📚 學習佇列</div>''', '''    <div class="section-title"><img class="ui-icon-md" src="/static/assets/icons/nav-queue.jpg" alt=""> 學習佇列</div>'''),
('''    <div class="section-title">🎯 願望清單</div>''', '''    <div class="section-title"><img class="ui-icon-md" src="/static/assets/icons/nav-wish.jpg" alt=""> 願望清單</div>'''),
('''    <div class="section-title">🏆 成就徽章</div>''', '''    <div class="section-title"><img class="ui-icon-md" src="/static/assets/icons/nav-achieve.jpg" alt=""> 成就徽章</div>'''),
('''    <div class="section-title">📊 學習統計</div>''', '''    <div class="section-title"><img class="ui-icon-md" src="/static/assets/icons/nav-stats.jpg" alt=""> 學習統計</div>'''),
('''      <div class="card-label">🔄 從 Hermes 課程同步</div>''', '''      <div class="card-label">從 Hermes 課程同步</div>'''),
('''        <div class="big-emoji celebrate" id="celebEmoji">🎉</div>''', '''        <div class="big-emoji celebrate" id="celebEmoji"><img class="ui-icon-xl" src="/static/assets/icons/icon-leaf.jpg" alt=""></div>'''),
('''      <h3>🗑️ 刪除項目</h3>''', '''      <h3>刪除項目</h3>'''),
('''      <h3>😅 今天為什麼沒學？</h3>''', '''      <h3>今天為什麼沒學？</h3>'''),
('''    <div style="font-size:13px;color:var(--text-sub);margin-bottom:12px">🪙 目前錢包：<strong id="wishCoinDisplay">0</strong></div>''',
 '''    <div style="font-size:13px;color:var(--text-sub);margin-bottom:12px;display:flex;align-items:center;gap:6px"><img class="ui-icon-sm" src="/static/assets/icons/icon-coin.jpg" alt=""> 目前錢包：<strong id="wishCoinDisplay">0</strong></div>'''),
('''      <button class="lm-btn" onclick="toggleSyncPanel()">🔄 同步課程</button>''', '''      <button class="lm-btn" onclick="toggleSyncPanel()">同步課程</button>'''),
('''      <button class="lm-btn" onclick="toggleNotePanel()">📝 筆記</button>
      <button class="lm-btn lm-btn-primary" onclick="endLearningSession()">✓ 完成學習</button>''',
 '''      <button class="lm-btn" onclick="toggleNotePanel()">筆記</button>
      <button class="lm-btn lm-btn-primary" onclick="endLearningSession()">完成學習</button>'''),
('''      <h4>📝 知識筆記</h4>''', '''      <h4>知識筆記</h4>'''),
('''      <button class="btn btn-primary btn-small" onclick="saveNote()" style="flex:1">💾 儲存到 Obsidian</button>''',
 '''      <button class="btn btn-primary btn-small" onclick="saveNote()" style="flex:1">儲存到 Obsidian</button>'''),
('''    <button class="lm-send" id="lmSend" onclick="sendMessage()">➤</button>''',
 '''    <button class="lm-send" id="lmSend" onclick="sendMessage()" aria-label="送出">→</button>'''),
]
for i,(a,b) in enumerate(static_pairs):
    must_replace(a,b,f"static-{i}")

# 6) JS logic replacements
must_replace(
    "  document.getElementById('levelIcon').textContent = lvl.icon;",
    "  document.getElementById('levelIcon').src = ASSET + lvl.icon + '.jpg';",
    "levelIcon src",
)
must_replace(
'''function applyTheme(){
  const mode = data.darkMode;
  const theme = mode==='system'?getSystemTheme():mode;
  document.documentElement.setAttribute('data-theme',theme);
  document.getElementById('themeBtn').textContent = theme==='dark'?'☀️':'🌙';
}''',
'''function applyTheme(){
  const mode = data.darkMode;
  const theme = mode==='system'?getSystemTheme():mode;
  document.documentElement.setAttribute('data-theme',theme);
  const img = document.getElementById('themeBtnImg');
  if(img) img.src = ASSET + (theme==='dark' ? 'theme-sun' : 'theme-moon') + '.jpg';
}''',
"applyTheme",
)
must_replace(
'''function spawnConfetti(){
  const emojis = ['🎉','🎊','✨','🌟','💫','⭐'];
  const container = document.getElementById('confettiContainer');
  for(let i=0;i<12;i++){
    const el = document.createElement('div');
    el.className='confetti';
    el.textContent=emojis[Math.floor(Math.random()*emojis.length)];
    el.style.left=(10+Math.random()*80)+'%';
    el.style.top=(20+Math.random()*30)+'%';
    el.style.animationDuration=(.8+Math.random()*1.2)+'s';
    el.style.animationDelay=(Math.random()*.5)+'s';
    el.style.fontSize=(14+Math.random()*14)+'px';
    container.appendChild(el);
    setTimeout(()=>el.remove(),2500);
  }
}''',
'''function spawnConfetti(){
  const leaves = ['icon-leaf','level-sprout','logo','icon-coin'];
  const container = document.getElementById('confettiContainer');
  for(let i=0;i<12;i++){
    const el = document.createElement('img');
    el.className='confetti';
    el.src = ASSET + leaves[Math.floor(Math.random()*leaves.length)] + '.jpg';
    el.alt = '';
    el.style.left=(10+Math.random()*80)+'%';
    el.style.top=(20+Math.random()*30)+'%';
    el.style.animationDuration=(.8+Math.random()*1.2)+'s';
    el.style.animationDelay=(Math.random()*.5)+'s';
    el.style.width=(16+Math.random()*14)+'px';
    el.style.height=el.style.width;
    container.appendChild(el);
    setTimeout(()=>el.remove(),2500);
  }
}''',
"spawnConfetti",
)

# Generic emoji->icon string swaps in templates
swaps = [
    ("const catIcon = CATEGORY_ICONS[item.category] || '📂';", "const catIcon = CATEGORY_ICONS[item.category] || 'cat-other';"),
    ("document.getElementById('celebEmoji').textContent = '🎉';", "document.getElementById('celebEmoji').innerHTML = icon('icon-leaf','ui-icon-xl');"),
    ("document.getElementById('lmTitle').textContent = `🎓 ${item.title}`;", "document.getElementById('lmTitle').textContent = item.title;"),
    ("<div class=\"big-emoji\">🎉</div>", "<div class=\"big-emoji\">${icon('icon-done','ui-icon-xl')}</div>"),
    ("<div class=\"big-emoji\">😌</div>", "<div class=\"big-emoji\">${icon('icon-rest','ui-icon-xl')}</div>"),
    ("<div class=\"big-emoji\">📭</div>", "<div class=\"big-emoji\">${icon('icon-empty','ui-icon-xl')}</div>"),
    ("<div class=\"empty-icon\">📚</div>", "<div class=\"empty-icon\">${icon('icon-empty','ui-icon-xl')}</div>"),
    ("<div class=\"empty-icon\">✅</div>", "<div class=\"empty-icon\">${icon('level-sprout','ui-icon-xl')}</div>"),
    ("<div class=\"empty-icon\">🎯</div>", "<div class=\"empty-icon\">${icon('icon-empty','ui-icon-xl')}</div>"),
    ("container.innerHTML = '<div class=\"queue-empty\"><div class=\"empty-icon\">${icon('icon-empty','ui-icon-xl')}</div>",
     "container.innerHTML = `<div class=\"queue-empty\"><div class=\"empty-icon\">${icon('icon-empty','ui-icon-xl')}</div>"),
    ("${catIcon} ${escapeHtml(item.category||'')}", "${icon(catIcon,'ui-icon-sm')} ${escapeHtml(item.category||'')}"),
    ("<span class=\"qi-icon\">${catIcon}</span>", "<span class=\"qi-icon\">${icon(catIcon,'ui-icon-md')}</span>"),
    ("${unlocked?a.icon:'🔒'}", "${icon(unlocked?a.icon:'icon-locked','ui-icon-lg')}"),
    ("const icon = l.status==='completed'?'✅':'😅';", "const stIcon = l.status==='completed'?'icon-done':'icon-rest';"),
    ("<span class=\"le-status\">${icon}</span>", "<span class=\"le-status\">${icon(stIcon,'ui-icon-sm')}</span>"),
    ("🔥 ${streak}天", "${icon('streak','ui-icon-sm')} ${streak}天"),
    ("<span class=\"qi-icon\">🎁</span>", "<span class=\"qi-icon\">${icon('nav-wish','ui-icon-md')}</span>"),
    ("<span class=\"qi-icon\">✅</span>", "<span class=\"qi-icon\">${icon('icon-done','ui-icon-md')}</span>"),
    ("💰 NT$", "${icon('icon-coin','ui-icon-sm')} NT$"),
    (" · 🔗 有連結", " · 有連結"),
    (" · 📌 ", " · "),
    ("msg-avatar\">👩‍🏫</div>", "msg-avatar\">${icon('avatar-teacher','ui-icon-avatar')}</div>"),
    ("msg-avatar\">🧑</div>", "msg-avatar\">${icon('avatar-user','ui-icon-avatar')}</div>"),
    # convert single-quoted typing html to template if needed later
    ("typingDiv.innerHTML = '<div class=\"msg-avatar\">${icon('avatar-teacher','ui-icon-avatar')}</div><div class=\"msg-bubble\"><div class=\"typing-dots\"><span></span><span></span><span></span></div></div>';",
     "typingDiv.innerHTML = `<div class=\"msg-avatar\">${icon('avatar-teacher','ui-icon-avatar')}</div><div class=\"msg-bubble\"><div class=\"typing-dots\"><span></span><span></span><span></span></div></div>`;"),
    ("div.innerHTML = `<div class=\"msg-avatar\">${icon('avatar-teacher','ui-icon-avatar')}</div><div class=\"msg-bubble\">${formatMessage(content)}</div>`;",
     "div.innerHTML = `<div class=\"msg-avatar\">${icon('avatar-teacher','ui-icon-avatar')}</div><div class=\"msg-bubble\">${formatMessage(content)}</div>`;"),
    ("div.innerHTML = `<div class=\"msg-avatar\">${icon('avatar-user','ui-icon-avatar')}</div><div class=\"msg-bubble\">${escapeHtml(text)}</div>`;",
     "div.innerHTML = `<div class=\"msg-avatar\">${icon('avatar-user','ui-icon-avatar')}</div><div class=\"msg-bubble\">${escapeHtml(text)}</div>`;"),
    ("onclick=\"relearnToday()\">📖 重新學習", "onclick=\"relearnToday()\">重新學習"),
    ("style=\"font-size:11px;padding:4px 8px\">📖 重學", "style=\"font-size:11px;padding:4px 8px\">重學"),
    ("📖 複習模式", "複習模式"),
    ("✅ 已學過", "已學過"),
    ("${isReview ? '✅ 複習完成' : '✅ 完成！'}", "${isReview ? '複習完成' : '完成'}"),
    ("onclick=\"completeToday()\">✅ 完成！", "onclick=\"completeToday()\">完成"),
    ("onclick=\"openLearningMode()\" style=\"background:var(--blue-1);box-shadow:0 4px 0 var(--blue-2)\">🎓 開始學習",
     "onclick=\"openLearningMode()\" style=\"background:linear-gradient(180deg,#6a9a9a,#5b8a8a);box-shadow:0 3px 0 var(--blue-2)\">開始學習"),
    ("onclick=\"openSkip()\">😅 今天不學", "onclick=\"openSkip()\">今天不學"),
    ("onclick=\"rerollTodayItem()\" style=\"font-size:13px\">🔀 換一課", "onclick=\"rerollTodayItem()\" style=\"font-size:13px\">換一課"),
    ("⏱ ${item.estimatedMinutes", "${item.estimatedMinutes"),
    ("🔗 ${escapeHtml(safeLink)}", "${escapeHtml(safeLink)}"),
    ("📌 ${escapeHtml(item.note)}", "${escapeHtml(item.note)}"),
    ("📊 ${course.completed_count}", "${course.completed_count}"),
    ("📥 匯入此課程的下一章", "匯入此課程的下一章"),
    ("showToast(`📥 ${course.course}", "showToast(`${course.course}"),
    ("${doneToday ? '✅ 已完成' : '📌 待完成'}", "${doneToday ? '已完成' : '待完成'}"),
    ("showToast(`🎉 已兌換「${w.title}」！`);", "showToast(`已兌換「${w.title}」`);"),
    ("showToast('🎉 今日習慣全部完成！Bonus +NT$35');", "showToast('今日習慣全部完成！Bonus +NT$35');"),
    ("showToast(`🎉 +NT$${xpEarned}！${lmCurrentItem.title} 學習完成`);", "showToast(`+NT$${xpEarned} · ${lmCurrentItem.title} 學習完成`);"),
    ("showToast(`📚 複習已存檔（今日進度已記錄，不再發 NT$）`);", "showToast(`複習已存檔（今日進度已記錄，不再發 NT$）`);"),
    ("showToast(`💾 對話已存到筆記`, 'success');", "showToast(`對話已存到筆記`, 'success');"),
    ("showToast(`✅ 已儲存到 ${result.path}`);", "showToast(`已儲存到 ${result.path}`);"),
    ("status.textContent = '✅ 已儲存';", "status.textContent = '已儲存';"),
    ("status.textContent = '❌ 儲存失敗';", "status.textContent = '儲存失敗';"),
    ("status.textContent = '❌ 連線錯誤';", "status.textContent = '連線錯誤';"),
    ("showToast('❌ 儲存失敗: '+result.message, 'error');", "showToast('儲存失敗: '+result.message, 'error');"),
    ("showToast('❌ 連線錯誤','error');", "showToast('連線錯誤','error');"),
    ("showToast('⚠️ ", "showToast('"),
    ("showToast(`⚠️ ", "showToast(`"),
    ("addTeacherMsg('body', '⚠️ ", "addTeacherMsg('body', '"),
    ("addTeacherMsg('append', '⚠️ ", "addTeacherMsg('append', '"),
    ("stat-icon\">🔥</div>", "stat-icon\">${icon('streak','ui-icon-lg')}</div>"),
    ("stat-icon\">✅</div>", "stat-icon\">${icon('icon-done','ui-icon-lg')}</div>"),
    ("stat-icon\">😅</div>", "stat-icon\">${icon('icon-rest','ui-icon-lg')}</div>"),
    ("stat-icon\">🌟</div>", "stat-icon\">${icon('icon-coin','ui-icon-lg')}</div>"),
]
for a,b in swaps:
    if a in html:
        html = html.replace(a,b)
    else:
        # only warn for non-trivial
        if len(a) > 20 and not a.startswith("showToast"):
            print("skip/missing swap:", a[:70].replace("\n"," "))

# Fix wishlist empty: ensure template literal if icon() used inside
html = html.replace(
    "container.innerHTML = '<div class=\"queue-empty\"><div class=\"empty-icon\">${icon('icon-empty','ui-icon-xl')}</div><p>還沒有任何願望<br>點下方按鈕新增第一個願望吧！</p></div>';",
    "container.innerHTML = `<div class=\"queue-empty\"><div class=\"empty-icon\">${icon('icon-empty','ui-icon-xl')}</div><p>還沒有任何願望<br>點下方按鈕新增第一個願望吧！</p></div>`;",
)

# Fix typing indicators that still use single-quoted emoji avatars
html = html.replace(
    "typingDiv.innerHTML = '<div class=\"msg-avatar\">👩‍🏫</div><div class=\"msg-bubble\"><div class=\"typing-dots\"><span></span><span></span><span></span></div></div>';",
    "typingDiv.innerHTML = `<div class=\"msg-avatar\">${icon('avatar-teacher','ui-icon-avatar')}</div><div class=\"msg-bubble\"><div class=\"typing-dots\"><span></span><span></span><span></span></div></div>`;",
)
html = html.replace(
    "div.innerHTML = `<div class=\"msg-avatar\">👩‍🏫</div><div class=\"msg-bubble\">${formatMessage(content)}</div>`;",
    "div.innerHTML = `<div class=\"msg-avatar\">${icon('avatar-teacher','ui-icon-avatar')}</div><div class=\"msg-bubble\">${formatMessage(content)}</div>`;",
)
html = html.replace(
    "div.innerHTML = `<div class=\"msg-avatar\">🧑</div><div class=\"msg-bubble\">${escapeHtml(text)}</div>`;",
    "div.innerHTML = `<div class=\"msg-avatar\">${icon('avatar-user','ui-icon-avatar')}</div><div class=\"msg-bubble\">${escapeHtml(text)}</div>`;",
)

# Final emoji strip for leftover common pictographs (not ASCII)
emoji_re = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002702-\U000027B0"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U00002600-\U000026FF"
    "\U0000FE0F"
    "\U0001F900-\U0001F9FF"
    "]+",
    flags=re.UNICODE,
)
before = len(emoji_re.findall(html))
# Protect CSS content '✓' by temporary placeholder? ✓ is U+2713 not in range usually
html2 = emoji_re.sub("", html)
# Clean double spaces created
html2 = re.sub(r"  +", " ", html2)
# Fix empty alt artifacts
after = len(emoji_re.findall(html2))
print(f"emoji remaining before/after strip: {before}/{after}")
html = html2

# Fix broken template if strip removed quotes oddly - check icon-locked still there
assert "icon-locked" in html
assert "ASSET" in html
assert "v8" in html

path.write_text(html, encoding="utf-8")
print("wrote", path, path.stat().st_size)
