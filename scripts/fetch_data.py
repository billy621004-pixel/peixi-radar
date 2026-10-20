#!/usr/bin/env python3
"""配息雷達 資料抓取：TWSE ETF e添富配息清單 + TWSE/TPEx 每日收盤價。不捏造資料，失敗會記錄在 sources_log。"""
import json, re, time, html, datetime as dt, pathlib, urllib.request, urllib.parse, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"; CACHE = DATA / "cache"
UA = {"User-Agent": "Mozilla/5.0 (peixi-radar MVP)"}
START_YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2025
log = []

def get(url, data=None, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=UA)
            return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
        except Exception as e:
            err = e; time.sleep(5 * (i + 1))
    raise err

def roc(s):
    m = re.match(r"(\d+)年(\d+)月(\d+)日", s.strip())
    return dt.date(int(m[1]) + 1911, int(m[2]), int(m[3])).isoformat() if m else None

def num(s):
    try: return float(str(s).replace(",", "").strip())
    except: return None

def fetch_dividends():
    today = dt.date.today()
    url = f"https://www.twse.com.tw/zh/ETFortune/dividendList?stkNo=&startDate={START_YEAR}&endDate={today.year}"
    try:
        page = get(url)
    except Exception as e:
        log.append({"source": url, "ok": False, "error": str(e)}); return []
    rows = []
    for tr in re.findall(r"<tr onclick[^>]*>(.*?)</tr>", page, re.S):
        tds = re.findall(r"<td>(.*?)</td>", tr, re.S)
        cells = [html.unescape(re.sub(r"<[^>]+>", "", t)).strip() for t in tds]
        if len(cells) < 6: continue
        code, name, ex, rec, pay, amt = cells[:6]
        rows.append({"code": code, "name": name, "ex_date": roc(ex), "record_date": roc(rec),
                     "pay_date": roc(pay), "amount": num(amt), "year_roc": cells[-1]})
    log.append({"source": url, "ok": True, "rows": len(rows)})
    return rows

def trading_days(start, end):
    d = start
    while d <= end:
        if d.weekday() < 5: yield d
        d += dt.timedelta(days=1)

def fetch_prices(start, end):
    prices = {}  # code -> {date: close}
    fails = {"twse": [], "tpex": []}
    for d in trading_days(start, end):
        ds = d.strftime("%Y%m%d")
        # TWSE ETF 每日收盤行情
        f = CACHE / "twse" / f"{ds}.json"
        if not f.exists():
            try:
                j = json.loads(get(f"https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={ds}&type=0099P&response=json"))
                f.write_text(json.dumps(j, ensure_ascii=False)); time.sleep(2.5)
            except Exception as e:
                fails["twse"].append(ds); continue
        j = json.loads(f.read_text())
        for t in j.get("tables", []):
            if "fields" in t and "收盤價" in t["fields"]:
                ci = t["fields"].index("收盤價")
                for r in t["data"]:
                    c = num(r[ci])
                    if c: prices.setdefault(r[0].strip(), {})[d.isoformat()] = c
        # TPEx 上櫃每日收盤行情
        f = CACHE / "tpex" / f"{ds}.json"
        if not f.exists():
            try:
                q = urllib.parse.quote(d.strftime("%Y/%m/%d"), safe="")
                j = json.loads(get(f"https://www.tpex.org.tw/www/zh-tw/afterTrading/otc?date={q}&type=EW&response=json"))
                f.write_text(json.dumps(j, ensure_ascii=False)); time.sleep(1.5)
            except Exception as e:
                fails["tpex"].append(ds); continue
        j = json.loads(f.read_text())
        for t in j.get("tables", []):
            for r in t.get("data", []):
                code = str(r[0]).strip()
                if re.match(r"^00\d{2,4}[A-Z]?$", code):
                    c = num(r[2])
                    if c: prices.setdefault(code, {})[d.isoformat()] = c
    for k, v in fails.items():
        log.append({"source": f"{k} daily close", "ok": not v, "failed_dates": v[:50], "failed_count": len(v)})
    return prices

def fill_days(div, px):
    """填息天數 = 除息日起第幾個交易日收盤價 >= 除息前一交易日收盤價（除息日當天填息=1）。"""
    ex = div["ex_date"]
    if not px or not ex: return None
    dates = sorted(px)
    before = [d for d in dates if d < ex]; after = [d for d in dates if d >= ex]
    if not before or not after: return {"status": "no_price"}
    pre = px[before[-1]]
    if before[-1] < (dt.date.fromisoformat(ex) - dt.timedelta(days=10)).isoformat():
        return {"status": "no_price"}
    for i, d in enumerate(after, 1):
        if px[d] >= pre:
            return {"status": "filled", "pre_close": pre, "days": i, "filled_date": d}
    return {"status": "open", "pre_close": pre, "days_so_far": len(after), "last_close": px[after[-1]]}

def main():
    today = dt.date.today()
    divs = fetch_dividends()
    prices = fetch_prices(dt.date(START_YEAR, 1, 1) - dt.timedelta(days=14), today)
    for d in divs:
        px = prices.get(d["code"], {})
        d["fill"] = fill_days(d, px) if d["ex_date"] and d["ex_date"] <= today.isoformat() else None
        pre = (d.get("fill") or {}).get("pre_close")
        if not pre and px:
            past = [k for k in sorted(px) if k < (d["ex_date"] or "9")]
            pre = px[past[-1]] if past else None
        d["ref_close"] = pre
        d["yield_pct"] = round(d["amount"] / pre * 100, 2) if d["amount"] and pre else None
    latest = {c: (max(p), p[max(p)]) for c, p in prices.items() if p}
    out = {"generated_at": dt.datetime.now().isoformat(timespec="seconds"), "dividends": divs,
           "latest_close": {c: {"date": a, "close": b} for c, (a, b) in latest.items()}, "sources_log": log}
    (DATA / "etf_data.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(json.dumps(log, ensure_ascii=False)[:2000]); print("dividends", len(divs))

if __name__ == "__main__": main()
