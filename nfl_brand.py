"""Self-contained brand assets for NFL HTML; no external asset requests."""

BRAND_CSS = """
/* Pops' Edge brand: shared by the workspace and portable bet sheets. */
:root{--navy:#0B2341;--green:#18A85B;--green-text:#087440;--ink:#20334a;--muted:#637489;--line:#dce4ec;--soft:#f4f7fa;--mint:#eaf7ef}
body{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:var(--ink);background:#fff;-webkit-font-smoothing:antialiased}
h1{color:var(--navy)}
.toolbar{background:var(--soft);border-color:var(--line)}
.toolbar label{color:var(--ink)}
select,.toolbar select{color:var(--navy);border-color:#cbd7e2;border-radius:7px;background:#fff}
.toolbar input[type=checkbox]{accent-color:var(--green-text)}
button:focus-visible,input:focus-visible,select:focus-visible,.toolbar select:focus-visible{outline:3px solid var(--green-text);outline-offset:3px}
#count,small,.guide,.intro,#inbox,#status{color:var(--muted)}
.scroll{border-color:var(--line);box-shadow:0 4px 16px #0b234108}
.betsheet th{background:var(--navy)}
.betsheet th:hover{background:#163b61}
.betsheet th button{font-weight:650}
.betsheet td{border-color:#e6edf2}
.betsheet tbody:nth-of-type(even) .quote{background:#fbfcfd}
.betsheet tr.quote:hover{background:#f0f7f4}
.gap{background:#f0f8f3}
.positive,.wager b{color:var(--green-text)}
.negative{color:#a13c38}
.contract{background:var(--mint);color:#175b3b;border-color:#cfe8d8;border-radius:5px}
.expand{border-color:#cbd7e2;color:var(--navy)}
.expand:hover{background:var(--soft)}
.detail td{background:var(--soft);color:#42566e}
.guide summary,.guide a{color:var(--navy)}
body.workspace{background:var(--soft);margin:24px 28px}
.brand-header{display:flex;align-items:center;gap:14px;margin:0 0 25px;min-height:52px}
.brand-mark{width:66px;height:48px;flex:none}
.brand-header h1{display:flex;align-items:center;gap:17px;flex-wrap:wrap;margin:0;padding:0;border:0;font-size:30px;font-weight:800;letter-spacing:-1.1px;line-height:1.2}
.title-sport{border-left:1px solid #ccd7e1;padding-left:17px;color:var(--muted);font-size:19px;font-weight:550;letter-spacing:0}
.version{margin-left:auto;flex:none;color:var(--green-text);background:var(--mint);border-color:#cee7d7;font-weight:650;font-size:12px;padding:5px 9px}
.tabs{border-color:var(--line);padding-left:12px;gap:7px}
.tab{background:#eaf0f5;color:#53677e;border-color:var(--line);font-weight:650}
.tab[aria-selected=true]{color:var(--navy);background:white;border-bottom-color:white;box-shadow:inset 0 3px var(--green)}
.tab:hover{background:#f8fbfd}
.panel{border-color:var(--line);box-shadow:0 7px 24px #0b234106}
#generate{background:var(--navy);border-color:var(--navy);font-weight:650}
#generate:hover:not(:disabled){background:#164267}
.progress-card{border-color:var(--line)}
.progress-card[data-state=complete] .status-icon{background:var(--green)}
.progress-card[data-state=running] .status-icon{border-top-color:var(--green)}
#statusTitle{color:var(--navy)}
@media(max-width:650px){body.workspace{margin:14px}.brand-header{gap:10px;margin-bottom:18px}.brand-mark{width:49px;height:38px}.brand-header h1{font-size:24px;gap:9px}.title-sport{font-size:15px;padding-left:9px}.version{font-size:10px;padding:4px 6px}.tab{padding:12px 14px}}
"""

# Vector adaptation of the supplied brand-sheet monogram, not the original master.
BRAND_MARK = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 110 76" class="brand-mark" aria-hidden="true" focusable="false"><g transform="translate(16 6) skewX(-12)"><path fill="#0B2341" fill-rule="evenodd" d="M0 0h35c17 0 24 8 24 21S49 43 33 43H18v21H0zm18 14v15h15c6 0 9-3 9-8s-3-7-9-7z"/><path fill="#18A85B" d="M61 0h35v14H61zM59 25h32v14H59zM52 50h35v14H52z"/></g></svg>'''
