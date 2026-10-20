#!/usr/bin/env python3
"""配息雷達 靜態網站產生器：讀 data/etf_data.json 輸出到 site/"""
import json, pathlib, datetime as dt, html, shutil
from collections import defaultdict
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "site"; BASE = "https://billy621004-pixel.github.io/peixi-radar/"; P = "/peixi-radar/"
D = json.loads((ROOT / "data/etf_data.json").read_text())
divs = [d for d in D["dividends"] if d["ex_date"]]
today = dt.date.today().isoformat()
e = html.escape
def f(v, fmt="{:.4g}"): return "—" if v is None else fmt.format(v)

def last_buy(ex):
    d = dt.date.fromisoformat(ex) - dt.timedelta(days=1)
    while d.weekday() >= 5: d -= dt.timedelta(days=1)
    return d.isoformat()  # 未扣除國定假日

CSS = """*{box-sizing:border-box}body{margin:0;font-family:-apple-system,"PingFang TC","Noto Sans TC","Microsoft JhengHei",sans-serif;color:#1f2933;background:#f5f7fa;line-height:1.6}
a{color:#0b6bcb;text-decoration:none}header{background:#0f3d63;color:#fff;padding:12px 16px}header a{color:#fff}header nav a{margin-right:14px;font-size:.95em}
.logo{font-size:1.4em;font-weight:700;margin-right:20px}main{max-width:1100px;margin:auto;padding:16px}h1{font-size:1.5em}
.card{background:#fff;border-radius:10px;padding:16px;margin:14px 0;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.tw{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:.92em}th,td{padding:7px 8px;border-bottom:1px solid #e4e7eb;text-align:left;white-space:nowrap}th{background:#eef2f7}
.slot{border:2px dashed #f0a500;background:#fff8e6;padding:14px;border-radius:8px;color:#8a5a00;text-align:center;margin:14px 0}
.tag{display:inline-block;padding:1px 8px;border-radius:10px;font-size:.85em}.ok{background:#e3f6e8;color:#1b7a3a}.open{background:#fde8e8;color:#b42318}
footer{background:#1f2933;color:#cbd2d9;padding:20px 16px;font-size:.88em}footer .disc{max-width:1100px;margin:auto}
input,button{font-size:1em;padding:7px 10px;border:1px solid #cbd2d9;border-radius:6px}button{background:#0f3d63;color:#fff;border:0;cursor:pointer}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:6px}@media(max-width:600px){h1{font-size:1.25em}th,td{padding:6px 5px}}"""

def page(path, title, desc, body):
    url = BASE + (path.strip("/") + "/" if path and not path.endswith(".html") else path)
    doc = f"""<!doctype html><html lang="zh-Hant-TW"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}｜配息雷達</title><meta name="description" content="{e(desc)}"><link rel="canonical" href="{url}">
<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:type" content="website"><meta property="og:url" content="{url}"><meta property="og:locale" content="zh_TW">
<link rel="stylesheet" href="{P}style.css"></head><body>
<header><a class="logo" href="{P}">📡 配息雷達</a><nav><a href="{P}">除息行事曆</a><a href="{P}fill-leaderboard/">填息排行</a><a href="{P}months/">月配息表</a><a href="{P}calculator/">現金流試算</a><a href="{P}etf/">ETF列表</a></nav></header>
<main>{body}
<div class="slot"><!-- SPONSOR_SLOT -->【贊助版位 placeholder】此處預留給贊助商廣告</div>
<div class="card"><h3>📬 訂閱除息提醒（即將推出）</h3><form onsubmit="alert('電子報尚未開放，敬請期待！');return false"><!-- NEWSLETTER_PROVIDER: 尚未串接 -->
<input type="email" placeholder="you@example.com" required> <button>訂閱</button></form><small>目前為預留表單，不會送出或儲存任何資料。</small></div></main>
<footer><div class="disc"><b>非投資建議</b>：本站資料整理自臺灣證券交易所 ETF e添富及櫃買中心公開資料，僅供參考，不構成任何投資建議；實際配息、日期以發行投信公告為準。殖利率為「單次配息 ÷ 除息前收盤價」估算；最後買進日為除息日前一個工作日（未排除國定假日）。<br>資料更新：{e(D['generated_at'])}</div></footer></body></html>"""
    p = OUT / path / "index.html" if not path.endswith(".html") else OUT / path
    p.parent.mkdir(parents=True, exist_ok=True); p.write_text(doc); urls.append(url)

AFF = '<div class="slot"><!-- BROKER_AFFILIATE_SLOT -->【券商合作版位 placeholder】例：開戶優惠／定期定額推薦連結</div>'
def fill_cell(d):
    fl = d.get("fill")
    if not fl or d["ex_date"] > today: return "未除息"
    if fl["status"] == "filled": return f'<span class="tag ok">已填息 {fl["days"]} 天</span>'
    if fl["status"] == "open": return f'<span class="tag open">未填息（{fl["days_so_far"]}天）</span>'
    return "無價格資料"
def row(d, code=True):
    c = f'<td><a href="{P}etf/{e(d["code"])}/">{e(d["code"])}</a></td><td>{e(d["name"])}</td>' if code else ""
    return f'<tr>{c}<td>{last_buy(d["ex_date"])}</td><td>{d["ex_date"]}</td><td>{d["pay_date"] or "—"}</td><td>{f(d["amount"])}</td><td>{f(d["yield_pct"],"{:.2f}%")}</td><td>{fill_cell(d)}</td></tr>'
HEAD = "<tr><th>代號</th><th>名稱</th><th>最後買進日</th><th>除息日</th><th>發放日</th><th>配息(元)</th><th>單次殖利率</th><th>填息</th></tr>"
def table(rows, code=True): 
    h = HEAD if code else HEAD.replace("<th>代號</th><th>名稱</th>", "")
    return f'<div class="tw"><table><thead>{h}</thead><tbody>{"".join(row(d,code) for d in rows)}</tbody></table></div>'

urls = []
if OUT.exists(): shutil.rmtree(OUT)
OUT.mkdir(); (OUT / "style.css").write_text(CSS)
by_code = defaultdict(list)
for d in divs: by_code[d["code"]].append(d)
names = {c: v[0]["name"] for c, v in by_code.items()}

# 首頁
up = sorted([d for d in divs if d["ex_date"] >= today], key=lambda d: (d["ex_date"], d["code"]))
recent = sorted([d for d in divs if d["ex_date"] < today], key=lambda d: d["ex_date"], reverse=True)[:30]
page("", "台灣ETF除息行事曆・配息・填息追蹤", "即將除息的台灣ETF：最後買進日、除息日、發放日、配息金額、殖利率與填息天數一次看。",
     f'<h1>即將除息的台灣 ETF</h1><p>共 {len(up)} 筆即將除息（今天 {today} 起）。配息金額空白表示投信尚未公告。</p><div class="card">{table(up)}</div>{AFF}<div class="card"><h2>最近已除息</h2>{table(recent)}</div>')

# ETF 頁
for c, ds in by_code.items():
    ds = sorted(ds, key=lambda d: d["ex_date"], reverse=True)
    filled = [d["fill"]["days"] for d in ds if d.get("fill") and d["fill"]["status"] == "filled"]
    avg = f"{sum(filled)/len(filled):.1f}" if filled else "—"
    tot = sum(d["amount"] or 0 for d in ds if d["ex_date"][:4] == today[:4])
    lc = D["latest_close"].get(c)
    page(f"etf/{c}", f"{c} {names[c]} 除息日・配息・填息天數", f"{c} {names[c]} 歷次除息日、配息金額、殖利率與填息天數紀錄。",
         f'<h1>{c} {e(names[c])} 除息日・配息・填息天數</h1><div class="card">最新收盤：{f(lc["close"]) if lc else "—"}（{lc["date"] if lc else "無資料"}）｜平均填息天數：{avg} 天（{len(filled)} 次已填息）｜{today[:4]}年累計配息：{tot:.4g} 元</div>{AFF}<div class="card">{table(ds, False)}</div>')
page("etf", "台灣ETF配息列表", "所有有配息紀錄的台灣ETF。", '<h1>ETF 列表</h1><div class="card grid">' + "".join(f'<a href="{P}etf/{c}/">{c}<br><small>{e(names[c])}</small></a>' for c in sorted(by_code)) + "</div>")

# 月份頁
by_m = defaultdict(list)
for d in divs: by_m[d["ex_date"][:7]].append(d)
for m, ds in by_m.items():
    y, mo = m.split("-")
    page(f"months/{m}", f"{y}年{int(mo)}月ETF配息表", f"{y}年{int(mo)}月台灣ETF除息日、配息金額與殖利率一覽。",
         f'<h1>{y}年{int(mo)}月ETF配息表</h1><p>共 {len(ds)} 檔次除息。</p><div class="card">{table(sorted(ds,key=lambda d:(d["ex_date"],d["code"])))}</div>')
page("months", "每月ETF配息表", "依月份瀏覽台灣ETF除息。", "<h1>每月 ETF 配息表</h1><div class='card grid'>" + "".join(f'<a href="{P}months/{m}/">{m[:4]}年{int(m[5:])}月</a>' for m in sorted(by_m, reverse=True)) + "</div>")

# 填息排行
fl = [d for d in divs if d.get("fill") and d["fill"]["status"] == "filled"]
agg = defaultdict(list)
for d in fl: agg[d["code"]].append(d["fill"]["days"])
rk = sorted(agg.items(), key=lambda kv: (sum(kv[1])/len(kv[1]), -len(kv[1])))
rows = "".join(f'<tr><td>{i}</td><td><a href="{P}etf/{c}/">{c}</a></td><td>{e(names[c])}</td><td>{sum(v)/len(v):.1f}</td><td>{len(v)}</td><td>{max(v)}</td></tr>' for i, (c, v) in enumerate(rk, 1))
opn = sorted([d for d in divs if d.get("fill") and d["fill"]["status"] == "open"], key=lambda d: -d["fill"]["days_so_far"])
page("fill-leaderboard", "ETF填息天數排行榜", "台灣ETF平均填息天數排行：哪些ETF填息最快？",
     f'<h1>ETF 填息天數排行榜</h1><p>以資料期間內「已填息」場次計算平均交易日數（除息當天即填息=1天）。</p><div class="card tw"><table><thead><tr><th>#</th><th>代號</th><th>名稱</th><th>平均填息天數</th><th>已填息次數</th><th>最長</th></tr></thead><tbody>{rows}</tbody></table></div><div class="card"><h2>尚未填息</h2>{table(opn)}</div>')

# 計算機
calc = {c: [[d["ex_date"], d["pay_date"], d["amount"]] for d in v if d["amount"]] for c, v in by_code.items()}
(OUT / "calc-data.json").write_text(json.dumps({"names": names, "divs": calc}, ensure_ascii=False))
page("calculator", "ETF存股每月現金流試算", "輸入持有ETF與張數，依最近12個月配息紀錄估算每月領多少。", """<h1>我的持股 → 每月現金流試算</h1>
<div class="card"><p>輸入代號與持有股數（1張=1000股），以「最近 12 個月實際配息」依發放月份估算。過去配息不代表未來。</p>
<div id="rows"></div><button onclick="add()">＋ 新增一檔</button> <button onclick="calc()">計算</button><div id="out" class="tw"></div></div>
<script>
let DB;fetch('../calc-data.json').then(r=>r.json()).then(j=>{DB=j;const s=JSON.parse(localStorage.getItem('h')||'[["00919",1000],["0056",1000]]');s.forEach(x=>add(...x));});
function add(c='',n=1000){const d=document.createElement('div');d.innerHTML=`<input class=c placeholder="代號" value="${c}" size=7> <input class=n type=number value="${n}" style="width:110px"> 股 <a href="#" onclick="this.parentNode.remove();return false">刪除</a>`;d.style.margin='6px 0';rows.appendChild(d);}
function calc(){const cut=new Date();cut.setFullYear(cut.getFullYear()-1);const cs=cut.toISOString().slice(0,10);const m=Array(12).fill(0);let h=[],html='';
document.querySelectorAll('#rows>div').forEach(d=>{const c=d.querySelector('.c').value.trim().toUpperCase(),n=+d.querySelector('.n').value;if(!c)return;h.push([c,n]);
(DB.divs[c]||[]).filter(x=>x[0]>=cs).forEach(x=>{const mo=+((x[1]||x[0]).slice(5,7))-1;m[mo]+=x[2]*n;});if(!DB.divs[c])html+=`<p>⚠ 找不到 ${c} 的配息資料</p>`;});
localStorage.setItem('h',JSON.stringify(h));const t=m.reduce((a,b)=>a+b,0);
out.innerHTML=html+'<table><tr><th>月份</th><th>預估現金流(元)</th></tr>'+m.map((v,i)=>`<tr><td>${i+1}月</td><td>${Math.round(v).toLocaleString()}</td></tr>`).join('')+`<tr><th>全年</th><th>${Math.round(t).toLocaleString()}（月均 ${Math.round(t/12).toLocaleString()}）</th></tr></table><small>未扣除二代健保補充保費、所得稅與匯費。</small>`;}
</script>""")

# sitemap / robots
(OUT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + "".join(f"<url><loc>{u}</loc><lastmod>{today}</lastmod></url>" for u in urls) + "</urlset>")
(OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {BASE}sitemap.xml\n")
print("pages", len(urls))
