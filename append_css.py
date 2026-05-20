css = """
/* ── Ghost button */
.ghost-btn, .btn-ghost { display: inline-flex; align-items: center; gap: 5px; padding: 6px 14px; border: 1px solid var(--border); border-radius: var(--r-md); background: transparent; color: var(--text-secondary); font-family: var(--font-sans); font-size: 12px; font-weight: 500; cursor: pointer; transition: all .15s; text-decoration: none; }
.ghost-btn:hover, .btn-ghost:hover { color: var(--text-primary); border-color: var(--accent); }
.ghost-btn.sm, .btn-ghost.sm { padding: 4px 10px; font-size: 11px; }

/* ── Primary button */
.btn-primary { display: inline-flex; align-items: center; gap: 6px; padding: 8px 18px; border: none; border-radius: var(--r-md); background: var(--accent-grad); color: #fff; font-family: var(--font-sans); font-size: 13px; font-weight: 600; cursor: pointer; transition: all .2s; box-shadow: 0 2px 12px rgba(108,99,255,.3); text-decoration: none; }
.btn-primary:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 4px 18px rgba(108,99,255,.5); }
.btn-primary:disabled { opacity: .5; cursor: not-allowed; }
.btn-primary.sm { padding: 5px 12px; font-size: 12px; }

/* ── Page & Utilities */
.page { display: flex; flex-direction: column; min-height: 100vh; }
.page-loading { display: flex; justify-content: center; align-items: center; padding: 60px; }
.page-error { padding: 30px; color: var(--red); text-align: center; }
.empty-state { padding: 40px; text-align: center; color: var(--text-muted); font-size: 14px; }
.back-link { display: inline-block; color: var(--text-secondary); font-size: 13px; text-decoration: none; margin-bottom: 8px; }
.back-link:hover { color: var(--accent-2); }
.muted-text { color: var(--text-muted); font-size: 12px; }

/* ── Navbar */
.navbar { display: flex; align-items: center; gap: 14px; padding: 10px 24px; background: var(--bg-panel); border-bottom: 1px solid var(--border); flex-shrink: 0; }
.nav-logo { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 15px; background: var(--accent-grad); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; text-decoration: none; }
.nav-spacer { flex: 1; }
.nav-link { color: var(--text-secondary); font-size: 13px; text-decoration: none; }
.nav-link:hover { color: var(--text-primary); }
.nav-user { font-size: 13px; color: var(--text-secondary); display: flex; align-items: center; gap: 7px; }
.nav-logout { background: none; border: 1px solid var(--border); border-radius: var(--r-sm); color: var(--text-muted); font-size: 12px; padding: 4px 10px; cursor: pointer; }
.nav-logout:hover { border-color: var(--red); color: var(--red); }
.role-badge { font-size: 9px; font-weight: 700; letter-spacing: .5px; padding: 2px 6px; border-radius: 10px; text-transform: uppercase; }
.role-badge.admin   { background: rgba(108,99,255,.2); color: var(--accent-2); }
.role-badge.student { background: rgba(74,222,128,.1); color: var(--green); }

/* ── Auth page */
.auth-page { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: radial-gradient(ellipse at 60% 20%, #1a1530 0%, var(--bg-base) 60%); }
.auth-card { width: 380px; padding: 36px; background: var(--bg-panel); border: 1px solid var(--border); border-radius: var(--r-lg); box-shadow: 0 20px 60px rgba(0,0,0,.5); }
.auth-logo { display: flex; align-items: center; gap: 10px; font-size: 22px; font-weight: 800; background: var(--accent-grad); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 4px; }
.auth-sub { font-size: 13px; color: var(--text-muted); margin-bottom: 24px; }
.auth-tabs { display: flex; border-bottom: 1px solid var(--border); margin-bottom: 24px; }
.auth-tabs button { flex: 1; padding: 9px; background: none; border: none; border-bottom: 2px solid transparent; color: var(--text-secondary); font-size: 13px; font-weight: 500; cursor: pointer; transition: all .15s; }
.auth-tabs button.active { color: var(--accent-2); border-bottom-color: var(--accent); }
.auth-form { display: flex; flex-direction: column; gap: 14px; }
.auth-form label { display: flex; flex-direction: column; gap: 5px; font-size: 12px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .4px; }
.auth-form input { padding: 9px 12px; background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-sm); color: var(--text-primary); font-size: 14px; outline: none; font-family: var(--font-sans); }
.auth-form input:focus { border-color: var(--accent); }
.auth-err { padding: 8px 12px; background: rgba(248,113,113,.1); border: 1px solid rgba(248,113,113,.25); border-radius: var(--r-sm); color: var(--red); font-size: 12px; }
.auth-err.auth-ok { background: rgba(74,222,128,.1); border-color: rgba(74,222,128,.25); color: var(--green); }

/* ── Contest Lobby */
.lobby-wrap { max-width: 1100px; margin: 0 auto; padding: 32px 24px; }
.lobby-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; }
.lobby-header h1 { font-size: 24px; font-weight: 700; }
.contest-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(310px, 1fr)); gap: 16px; }
.contest-card { background: var(--bg-panel); border: 1px solid var(--border); border-radius: var(--r-lg); padding: 20px; display: flex; flex-direction: column; gap: 10px; transition: border-color .15s; }
.contest-card:hover { border-color: rgba(108,99,255,.4); }
.contest-card.live { border-color: rgba(74,222,128,.3); box-shadow: 0 0 20px rgba(74,222,128,.05); }
.cc-top { display: flex; align-items: center; justify-content: space-between; }
.cc-title { font-size: 16px; font-weight: 700; }
.cc-desc { font-size: 12.5px; color: var(--text-secondary); line-height: 1.6; }
.cc-times { font-size: 11px; color: var(--text-muted); display: flex; flex-direction: column; gap: 2px; }
.cc-problems { font-size: 11px; color: var(--text-muted); }
.cc-actions { display: flex; gap: 8px; margin-top: 4px; }

/* ── Badges & Countdown */
.badge { display: inline-flex; align-items: center; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; letter-spacing: .3px; }
.badge-scheduled { color: var(--yellow); background: rgba(251,191,36,.12); border: 1px solid rgba(251,191,36,.25); }
.badge-live      { color: var(--green);  background: rgba(74,222,128,.12);  border: 1px solid rgba(74,222,128,.25); }
.badge-ended     { color: var(--text-muted); background: var(--bg-surface); border: 1px solid var(--border); }
.countdown { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.cd-label { color: var(--text-muted); font-size: 11px; }
.cd-time { font-family: var(--font-mono); font-weight: 600; color: var(--accent-2); }

/* ── Leaderboard */
.lb-wrap { max-width: 800px; margin: 0 auto; padding: 32px 24px; }
.lb-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 24px; }
.lb-header h1 { font-size: 22px; font-weight: 700; }
.lb-meta { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }
.lb-table-wrap { border-radius: var(--r-lg); overflow: hidden; border: 1px solid var(--border); }
.lb-table { width: 100%; border-collapse: collapse; }
.lb-table thead tr { background: var(--bg-surface); }
.lb-table th { padding: 11px 18px; text-align: left; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .5px; color: var(--text-muted); border-bottom: 1px solid var(--border); }
.lb-table td { padding: 12px 18px; border-bottom: 1px solid rgba(37,42,56,.6); font-size: 13.5px; }
.lb-table tr:last-child td { border-bottom: none; }
.lb-table tr:hover td { background: rgba(108,99,255,.04); }
.lb-table tr.top-rank td { background: rgba(108,99,255,.06); }
.rank-cell { font-family: var(--font-mono); font-size: 15px; }
.username-cell { font-weight: 600; }
.score-cell { font-family: var(--font-mono); font-weight: 700; color: var(--accent-2); }
.cases-cell { font-family: var(--font-mono); color: var(--text-secondary); }
.time-cell { font-size: 12px; color: var(--text-muted); }

/* ── Verdict colors */
.v-ac  { color: var(--green);  background: rgba(74,222,128,.12); }
.v-wa  { color: var(--red);    background: rgba(248,113,113,.12); }
.v-ce  { color: var(--yellow); background: rgba(251,191,36,.12); }
.v-re  { color: var(--orange); background: rgba(251,146,60,.12); }
.v-tle { color: var(--cyan);   background: rgba(34,211,238,.12); }
.verdict-easy   { color: var(--green);  background: rgba(74,222,128,.12); }
.verdict-medium { color: var(--yellow); background: rgba(251,191,36,.12); }
.verdict-hard   { color: var(--red);    background: rgba(248,113,113,.12); }

/* ── Problem statement */
.problem-statement { display: flex; flex-direction: column; gap: 16px; }
.prob-section { display: flex; flex-direction: column; gap: 8px; }
.prob-section h4 { font-size: 12px; text-transform: uppercase; letter-spacing: .6px; color: var(--text-muted); font-weight: 600; }
.example-block { background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-md); padding: 12px 14px; display: flex; flex-direction: column; gap: 5px; font-size: 13px; }
.example-block code { font-family: var(--font-mono); color: var(--accent-2); }
.ex-explain { font-size: 12px; color: var(--text-muted); margin-top: 4px; }
.prob-meta { display: flex; gap: 10px; flex-wrap: wrap; }

/* ── Admin pages */
.admin-wrap { max-width: 960px; margin: 0 auto; padding: 32px 24px; display: flex; flex-direction: column; gap: 24px; }
.admin-header { display: flex; justify-content: space-between; align-items: flex-start; }
.admin-header h1 { font-size: 22px; font-weight: 700; }
.admin-form { background: var(--bg-panel); border: 1px solid var(--border); border-radius: var(--r-lg); padding: 20px; display: flex; flex-direction: column; gap: 16px; }
.admin-form h3 { font-size: 14px; font-weight: 600; }
.form-row { display: flex; gap: 14px; flex-wrap: wrap; }
.form-row label { flex: 1; min-width: 180px; display: flex; flex-direction: column; gap: 6px; font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .4px; }
.form-row input, .form-row select { padding: 9px 12px; background: var(--bg-surface); border: 1px solid var(--border); border-radius: var(--r-sm); color: var(--text-primary); font-size: 13px; outline: none; font-family: var(--font-sans); }
.form-row input:focus, .form-row select:focus { border-color: var(--accent); }
.form-row select { cursor: pointer; }
.gen-loading { display: flex; align-items: center; gap: 14px; color: var(--text-secondary); font-size: 13px; padding: 12px 0; }
.problem-preview { background: var(--bg-surface); border: 1px solid rgba(74,222,128,.25); border-radius: var(--r-md); padding: 16px; animation: fadeIn .3s ease; }
.problems-section { display: flex; flex-direction: column; gap: 12px; }
.problems-section h3 { font-size: 14px; font-weight: 600; }
.problem-row { display: flex; align-items: center; justify-content: space-between; background: var(--bg-panel); border: 1px solid var(--border); border-radius: var(--r-md); padding: 14px 16px; }
.pr-left { display: flex; align-items: center; gap: 12px; }
.pr-letter { width: 28px; height: 28px; border-radius: 50%; background: var(--accent); color: #fff; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; flex-shrink: 0; }
.pr-title { font-size: 14px; font-weight: 600; }
"""

with open(r'd:\Code War\code-executor\frontend\src\index.css', 'a', encoding='utf-8') as f:
    f.write(css)

print("CSS appended successfully")
