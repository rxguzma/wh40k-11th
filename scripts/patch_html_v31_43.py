from pathlib import Path
import re

src=Path('versions/WH40k_11th_V31.42.html')
out=Path('WH40k_11th.html')
text=src.read_text(encoding='utf-8')

def r(old,new,label):
    global text
    n=text.count(old)
    if n!=1: raise SystemExit(f'{label}: expected 1 match, found {n}')
    text=text.replace(old,new,1)

r('<title>WH40k 11th V31.42</title>','<title>WH40k 11th V31.43</title>','title')
r('The current baseline is WH40k_11th_V31.42;','The current baseline is WH40k_11th_V31.43;','baseline')
r('const APP_VERSION = "31.42";','const APP_VERSION = "31.43";','APP_VERSION')
r("version: 'V31.42',","version: 'V31.43',",'quality version')

css='''
    /* V31.43 alternate View: Np1.37 rows 2-6 only; no drafting grid. */
    body.np-view-screen-active .app-sticky-header{display:none}
    .np-view-screen{width:100%;min-height:100vh;min-height:100dvh;background:#0f1115;overflow-x:hidden}
    .np-view-header-grid{display:grid;grid-template-columns:repeat(16,26px);grid-template-rows:repeat(5,26px);width:416px;margin:0 auto;background:#0f1115;color:#f1f3f4;isolation:isolate}
    .np-view-header-shell{grid-column:1/span 16;grid-row:1/span 4;z-index:1;border:1px solid #2c313a;border-radius:12px;background:#171a21}
    .np-view-roster-name{grid-column:2/span 7;grid-row:1;z-index:2;display:flex;align-items:center;min-width:0;color:#f1f3f4;font:900 20px/1 Roboto,Arial,sans-serif;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .np-view-detachments{grid-column:2/span 9;grid-row:2;z-index:2;display:flex;align-items:center;min-width:0;color:#9aa0a6;font:700 14px/1 Roboto,Arial,sans-serif;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
    .np-view-summary{grid-column:2/span 9;grid-row:3;z-index:2;display:flex;align-items:center;gap:6px;min-width:0;font:700 12px/1 Roboto,Arial,sans-serif;white-space:nowrap;overflow:hidden}.np-view-summary-disposition{color:#80d6a3}.np-view-summary-rest{color:#9aa0a6}
    .np-view-nav-button,.np-view-phase-button{width:calc(100% - 2px);height:24px;padding:0 10px;border:1px solid #48515f;border-radius:6px;background:#2b313b;color:#f1f3f4;font-family:Roboto,Arial,sans-serif;font-size:12px;font-weight:700;line-height:1;display:inline-flex;align-items:center;justify-content:center;white-space:nowrap}
    .np-view-nav-button{z-index:3;width:50px;height:50px;align-self:center;justify-self:center}.np-view-nav-button.active{background:#1f5b35;border-color:#2e7d49}.np-view-nav-view{grid-column:11/span 2;grid-row:1/span 2}.np-view-nav-edit{grid-column:13/span 2;grid-row:1/span 2}.np-view-nav-cards{grid-column:15/span 2;grid-row:1/span 2}
    .np-view-phase-buttons{grid-column:2/span 15;grid-row:5;z-index:2;display:grid;grid-template-columns:repeat(5,78px);align-items:center;justify-items:center}
'''
r('</style>\n</head>',css+'\n</style>\n</head>','alternate View CSS')

marker='''  <div id="rosterScreen" class="screen active">\n    <div class="table-card" id="rosterTable"></div>\n  </div>\n\n\n  <div id="cardsScreen" class="screen">'''
screen='''  <div id="rosterScreen" class="screen active">\n    <div class="table-card" id="rosterTable"></div>\n  </div>\n\n  <div id="newPageScreen" class="screen np-view-screen" aria-label="Alternate View page">\n    <div class="np-view-header-grid">\n      <div class="np-view-header-shell"></div>\n      <div class="np-view-roster-name">Winning ORKS</div>\n      <div class="np-view-detachments">Bully Boyz - Da Big Hunt - Wreckas</div>\n      <div class="np-view-summary"><span class="np-view-summary-disposition">Priority Assets</span><span class="np-view-summary-rest">- 1995 pts - 10 VPs</span></div>\n      <button type="button" class="np-view-nav-button np-view-nav-view active" onclick="UI.selectAppMode('view')">VIEW</button>\n      <button type="button" class="np-view-nav-button np-view-nav-edit" onclick="UI.selectAppMode('edit')">EDIT</button>\n      <button type="button" class="np-view-nav-button np-view-nav-cards" onclick="UI.selectAppMode('cards')">CARDS</button>\n      <div class="np-view-phase-buttons"><button type="button" class="np-view-phase-button">COMMAND</button><button type="button" class="np-view-phase-button">MOVE</button><button type="button" class="np-view-phase-button">SHOOT</button><button type="button" class="np-view-phase-button">CHARGE</button><button type="button" class="np-view-phase-button">FIGHT</button></div>\n    </div>\n  </div>\n\n\n  <div id="cardsScreen" class="screen">'''
r(marker,screen,'alternate View screen')

r('''      newPageScreen.classList.add("active");\n      activeAppScreen = "newpage";''','''      newPageScreen.classList.add("active");\n      document.body.classList.add("np-view-screen-active");\n      activeAppScreen = "newpage";''','body class on')
r('''      if (newPageScreen) newPageScreen.classList.remove("active");\n      if (rosterScreen) rosterScreen.classList.add("active");''','''      if (newPageScreen) newPageScreen.classList.remove("active");\n      document.body.classList.remove("np-view-screen-active");\n      if (rosterScreen) rosterScreen.classList.add("active");''','body class off')

r('''      if (activeAppScreen === "newpage") hideNewPageScreen();\n\n      if (target === "cards") {''','''      if (target === "view" && activeAppScreen === "newpage") {\n        hideNewPageScreen();\n        return;\n      }\n\n      if (activeAppScreen === "newpage") hideNewPageScreen();\n\n      if (target === "cards") {''','View return from alternate')
r('''      if (target === "view") {\n        if (activeAppScreen === "cards") showArmyScreen({ commitCardsState: true });\n        else if (appEditMode) setEditMode(false);\n        else updateEditModeToggle();\n      }''','''      if (target === "view") {\n        if (activeAppScreen === "cards") showArmyScreen({ commitCardsState: true });\n        else if (appEditMode) setEditMode(false);\n        else showNewPageScreen();\n      }''','View second press')

note='''  <!--\n    CHANGE NOTE - WH40k_11th_V31.43\n    Scope: Move the approved Np1.37 header mock into the real HTML as a second View surface, transferring only drafting-grid rows 2-6 and omitting all grid lines/coordinates. Canonical View remains the first View state; pressing View again opens the transferred surface, whose View control returns to canonical View. Edit and Cards controls continue to route to their existing screens. Phase controls are visual-only in this initial transfer.\n    Risk areas: View title navigation and the new alternate View header surface only. Existing roster rendering, Edit, Cards, data, persistence, and combat behavior are unchanged.\n  -->\n\n'''
mark='  <!--\n    CHANGE NOTE - WH40k_11th_V31.42\n'
if mark not in text: raise SystemExit('release note marker missing')
text=text.replace(mark,note+mark,1)
text,n=re.subn(r'\n  <!--\n    CHANGE NOTE - WH40k_11th_V31\.34\n.*?\n  -->\n','\n',text,count=1,flags=re.S)
if n!=1: raise SystemExit(f'old note removal: expected 1, found {n}')

for check in ['<title>WH40k 11th V31.43</title>','const APP_VERSION = "31.43";',"version: 'V31.43',",'id="newPageScreen" class="screen np-view-screen"','np-view-screen-active','else showNewPageScreen();']:
    if check not in text: raise SystemExit('missing acceptance check: '+check)
out.write_text(text,encoding='utf-8')
print('Built V31.43 alternate View rows 2-6')
