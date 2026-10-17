"""3단계: GitHub 서버에서 각 데이터 사이트에 접속되는지 확인하는 테스트."""
import io, json, os, zipfile, datetime as dt
import requests

result = {"checked_at": dt.datetime.utcnow().isoformat() + "Z"}

def run(name, fn):
    try:
        result[name] = {"ok": True, "info": fn()}
    except Exception as e:
            msg = str(e).replace(os.environ.get("DART_API_KEY", "") or "\0", "***")
           result[name] = {"ok": False, "error": f"{type(e).__name__}: {msg[:200]}"}
    print(name, result[name])

# 1) 한국거래소 (pykrx): 전 종목 시총 + 삼성전자 투자자별 수급
def krx():
    from pykrx import stock
    d = stock.get_nearest_business_day_in_a_week()
    cap = stock.get_market_cap(d, market="ALL")
    start = (dt.datetime.strptime(d, "%Y%m%d") - dt.timedelta(days=14)).strftime("%Y%m%d")
    flow = stock.get_market_trading_value_by_date(start, d, "005930")
    return {"date": d, "stocks": len(cap), "flow_rows": len(flow), "flow_cols": list(flow.columns)[:6]}

# 2) OpenDART: 기업코드 목록 + 삼성전자 2025 사업보고서 재무
def dart():
    key = os.environ.get("DART_API_KEY", "")
    if not key:
        raise RuntimeError("DART_API_KEY secret not found")
    r = requests.get("https://opendart.fss.or.kr/api/corpCode.xml", params={"crtfc_key": key}, timeout=60)
    z = zipfile.ZipFile(io.BytesIO(r.content))
    n = z.read(z.namelist()[0]).count(b"<list>")
    f = requests.get("https://opendart.fss.or.kr/api/fnlttSinglAcnt.json",
                     params={"crtfc_key": key, "corp_code": "00126380", "bsns_year": "2025", "reprt_code": "11011"},
                     timeout=30).json()
    return {"corp_count": n, "fin_status": f.get("status"), "fin_rows": len(f.get("list", []))}

# 3) 네이버 금융 (대체 경로)
def naver():
    r = requests.get("https://finance.naver.com/item/sise.naver?code=005930",
                     headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    return {"status": r.status_code, "bytes": len(r.content)}

# 4) 야후 파이낸스 (대체 경로, 해외 시장용)
def yahoo():
    import yfinance as yf
    h = yf.Ticker("005930.KS").history(period="1mo")
    return {"rows": len(h)}

for name, fn in [("krx", krx), ("dart", dart), ("naver", naver), ("yahoo", yahoo)]:
    run(name, fn)

os.makedirs("data", exist_ok=True)
with open("data/access_check.json", "w", encoding="utf-8") as fp:
    json.dump(result, fp, ensure_ascii=False, indent=2)
