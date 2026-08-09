import os, time, datetime, webbrowser, requests, statistics

# ==========================================
# 🔑 FINNHUB API KEY & CUSTOM INDUSTRY MAPPINGS
# ==========================================
API_KEY = "d9rihopr01qoo7o4k3igd9rihopr01qoo7o4k3j0"

CUSTOM_INDUSTRY_MAP = {
    "REGN": "Biotech And Healthcare", "ISRG": "Biotech And Healthcare", "LLY": "Biotech And Healthcare", "VRTX": "Biotech And Healthcare",
    "JPM": "Financial Services", "V": "Financial Services", "BLK": "Financial Services", "COIN": "Financial Services", "GS": "Financial Services",
    "BE": "Engineering And Chips", "ETN": "Engineering And Chips", "GEV": "Engineering And Chips", "GLW": "Engineering And Chips", "CAT": "Engineering And Chips", "ANET": "Engineering And Chips", "VRT": "Engineering And Chips",
    "TSM": "Semiconductors",
    "AAPL": "Big Guys", "AMZN": "Big Guys", "MSFT": "Big Guys", "GOOGL": "Big Guys",
    "COST": "Consumer", "SPOT": "Consumer", "NFLX": "Consumer"
}

tickers = [
    "AAPL", "AMZN", "ANET", "AVGO", "AXON", "BA", "BE", "BLK", "CAT", "COIN",
    "COST", "CRWD", "DDOG", "ETN", "GEV", "GLW", "GOOGL", "GS", "ISRG", "JPM",
    "LLY", "MRVL", "MSFT", "MU", "NFLX", "NVDA", "PLTR", "REGN", "SNOW", "SPOT",
    "TSM", "V", "VRT", "VRTX"
]

print("🚀 Starting Data Fetch (Jacob's Stock Dashboard)...")

session = requests.Session()
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def safe_api_get(url, retries=3, delay=2, extra_headers=None):
    for _ in range(retries):
        try:
            res = session.get(url, headers=extra_headers or {})
            if res.status_code == 200:
                data = res.json()
                if isinstance(data, dict) and data.get('error'):
                    time.sleep(delay)
                    continue
                return data
            elif res.status_code in (429, 403):
                time.sleep(delay)
            else:
                time.sleep(1)
        except Exception:
            time.sleep(1)
    return {}

def get_historical_data_yahoo(symbol, current_price):
    ret_10d, ret_30d = 0.0, 0.0
    p_10d, p_30d = 0.0, 0.0
    try:
        yf_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=3mo&interval=1d"
        res = safe_api_get(yf_url, retries=2, delay=1, extra_headers=headers)
        result = res.get('chart', {}).get('result', [])
        if result:
            quote = result[0].get('indicators', {}).get('quote', [{}])[0]
            closes = [c for c in quote.get('close', []) if c is not None]
            if len(closes) >= 10:
                p_10d = closes[-11] if len(closes) >= 11 else closes[0]
                ret_10d = ((current_price - p_10d) / p_10d) * 100
            if len(closes) >= 30:
                p_30d = closes[-31] if len(closes) >= 31 else closes[0]
                ret_30d = ((current_price - p_30d) / p_30d) * 100
    except Exception:
        pass
    return ret_10d, p_10d, ret_30d, p_30d

def get_earnings_move_yahoo(symbol, earn_date_str, hour_timing):
    if not earn_date_str or earn_date_str == 'N/A':
        return 0.0, False
    try:
        earn_date = datetime.datetime.strptime(earn_date_str, "%Y-%m-%d").date()
        if earn_date > datetime.date.today():
            return 0.0, False
        yf_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=3mo&interval=1d"
        res = safe_api_get(yf_url, retries=2, delay=1, extra_headers=headers)
        result = res.get('chart', {}).get('result', [])
        if result:
            timestamps = result[0].get('timestamp', [])
            quote = result[0].get('indicators', {}).get('quote', [{}])[0]
            closes = quote.get('close', [])
            target_ts = int(time.mktime(earn_date.timetuple()))
            closest_idx = min(range(len(timestamps)), key=lambda i: abs(timestamps[i] - target_ts))
            if 0 < closest_idx < len(closes) - 1:
                p_before = closes[closest_idx] if hour_timing == "AMC" else closes[closest_idx - 1]
                p_after = closes[closest_idx + 1] if hour_timing == "AMC" else closes[closest_idx]
                if p_before and p_after:
                    return round(((p_after - p_before) / p_before) * 100, 2), True
    except Exception:
        pass
    return 0.0, False

data_list, earnings_list, movers_list, master_list, news_list = [], [], [], [], []

now = datetime.datetime.now()
generation_timestamp_str = now.strftime("%b %d, %Y at %H:%M:%S")
today = now.date()
past_week_str = (today - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
today_str = today.strftime("%Y-%m-%d")
future_str = (today + datetime.timedelta(days=120)).strftime("%Y-%m-%d")

for idx, symbol in enumerate(tickers, 1):
    try:
        quote_url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={API_KEY}"
        quote_res = safe_api_get(quote_url, delay=2)
        last_price = quote_res.get('c', 0) if isinstance(quote_res, dict) else 0
        daily_return_pct = quote_res.get('dp', 0) if isinstance(quote_res, dict) else 0

        if not last_price:
            continue
        time.sleep(0.2)

        profile_url = f"https://finnhub.io/api/v1/stock/profile2?symbol={symbol}&token={API_KEY}"
        profile_res = safe_api_get(profile_url, delay=2)
        comp_name = profile_res.get('name', symbol) if isinstance(profile_res, dict) else symbol
        default_ind = profile_res.get('finnhubIndustry', 'General Financial') if isinstance(profile_res, dict) else 'General Financial'
        comp_industry = CUSTOM_INDUSTRY_MAP.get(symbol, default_ind).title()
        mkt_cap = profile_res.get('marketCapitalization', 0) if isinstance(profile_res, dict) else 0
        mkt_cap_str = f"${mkt_cap:,.0f}M" if mkt_cap else "N/A"
        time.sleep(0.2)

        metric_url = f"https://finnhub.io/api/v1/stock/metric?symbol={symbol}&metric=all&token={API_KEY}"
        metric_res = safe_api_get(metric_url, delay=2)
        metrics = metric_res.get('metric', {}) if isinstance(metric_res, dict) else {}

        raw_low52 = metrics.get('52WeekLow')
        raw_high52 = metrics.get('52WeekHigh')
        raw_ma50 = metrics.get('50DayMovingAverage')
        raw_ma200 = metrics.get('200DayMovingAverage')

        scale_factor = 1.0
        if raw_high52 and raw_high52 > 0:
            ratio = raw_high52 / last_price
            if ratio > 3.0 or ratio < 0.33:
                scale_factor = last_price / ((raw_high52 + (raw_low52 or raw_high52)) / 2)

        low52 = (raw_low52 * scale_factor) if raw_low52 else (last_price * 0.70)
        high52 = (raw_high52 * scale_factor) if raw_high52 else (last_price * 1.25)
        ma50 = (raw_ma50 * scale_factor) if raw_ma50 else (last_price * 0.95)
        ma200 = (raw_ma200 * scale_factor) if raw_ma200 else (last_price * 0.88)
        supp = ma50 * 0.98

        pct_range = max(0, min(100, ((last_price - low52) / (high52 - low52)) * 100)) if high52 > low52 else 50

        data_list.append({
            "ticker": symbol, "last": round(last_price, 2), "supp": round(supp, 2),
            "ma50": round(ma50, 2), "ma200": round(ma200, 2), "low52": round(low52, 2),
            "high52": round(high52, 2), "pct": round(pct_range, 1)
        })

        master_list.append({
            "ticker": symbol, "name": comp_name, "industry": comp_industry,
            "price": round(last_price, 2), "mkt_cap": mkt_cap_str, "pct": round(pct_range, 1)
        })
        time.sleep(0.2)

        earn_url = f"https://finnhub.io/api/v1/calendar/earnings?from={past_week_str}&to={future_str}&symbol={symbol}&token={API_KEY}"
        earn_res = safe_api_get(earn_url, delay=2)
        earn_cal = earn_res.get('earningsCalendar', []) if isinstance(earn_res, dict) else []

        if earn_cal:
            earn_cal.sort(key=lambda x: x.get('date', '9999-99-99'))
            next_earn = next((e for e in earn_cal if e.get('date', '') >= past_week_str), earn_cal[0])
            earn_date_str = next_earn.get('date', 'N/A')
            eps_est, eps_act = next_earn.get('epsEstimate'), next_earn.get('epsActual')
            hour_raw = next_earn.get('hour', '').upper()
            timing = "Before Open" if hour_raw == "BMO" else ("After Close" if hour_raw == "AMC" else "TBD")

            earn_move, has_moved = get_earnings_move_yahoo(symbol, earn_date_str, hour_raw)
            earn_move_badge = f'<span class="return-badge {"badge-pos" if earn_move > 0 else ("badge-neg" if earn_move < 0 else "badge-neutral")}">{f"+{earn_move:.2f}%" if earn_move > 0 else f"{earn_move:.2f}%"}</span>' if has_moved else '<span style="color:var(--text-muted);">-</span>'

            if eps_act is not None or (earn_date_str != 'N/A' and datetime.datetime.strptime(earn_date_str, "%Y-%m-%d").date() < today):
                status_class, status_text = "badge-reported", "Reported"
                eps_str = f"${eps_act:.2f}" if eps_act is not None else (f"${eps_est:.2f}" if eps_est is not None else "N/A")
            elif earn_date_str != 'N/A':
                try:
                    earn_date_obj = datetime.datetime.strptime(earn_date_str, "%Y-%m-%d").date()
                    cur_year, cur_month = today.year, today.month
                    next_month = cur_month + 1 if cur_month < 12 else 1
                    next_year = cur_year if cur_month < 12 else cur_year + 1
                    after_month = next_month + 1 if next_month < 12 else 1
                    after_year = next_year if next_month < 12 else next_year + 1
                    days_away = (earn_date_obj - today).days
                    if days_away < 0:
                        status_class, status_text = "badge-reported", "Reported"
                    elif earn_date_obj.year == next_year and earn_date_obj.month == next_month:
                        status_class, status_text = "badge-next-month", "Next Month"
                    elif earn_date_obj.year == after_year and earn_date_obj.month == after_month:
                        status_class, status_text = "badge-month-after", "Month After"
                    elif 0 <= days_away <= 30:
                        status_class, status_text = "badge-upcoming", f"Upcoming ({days_away}d)"
                    else:
                        status_class, status_text = "badge-unconfirmed", "Unconfirmed Est."
                except Exception:
                    status_class, status_text = "badge-unconfirmed", "Unconfirmed Est."
                eps_str = f"${eps_est:.2f}" if eps_est is not None else "N/A"
            else:
                status_class, status_text, eps_str = "badge-unconfirmed", "Unconfirmed Est.", "N/A"

            earnings_list.append({
                "ticker": symbol, "date": earn_date_str, "eps_est": eps_str, "timing": timing,
                "status_class": status_class, "status_text": status_text, "price": round(last_price, 2), "earn_move": earn_move_badge
            })
        else:
            earnings_list.append({
                "ticker": symbol, "date": "TBD / Next Qtr", "eps_est": "N/A", "timing": "TBD",
                "status_class": "badge-unconfirmed", "status_text": "Unconfirmed Est.", "price": round(last_price, 2), "earn_move": '<span style="color:var(--text-muted);">-</span>'
            })
        time.sleep(0.2)

        news_url = f"https://finnhub.io/api/v1/company-news?symbol={symbol}&from={past_week_str}&to={today_str}&token={API_KEY}"
        news_res = safe_api_get(news_url, delay=2)
        if isinstance(news_res, list) and len(news_res) > 0:
            top_item = news_res[0]
            dt_stamp = top_item.get('datetime', 0)
            date_formatted = datetime.datetime.fromtimestamp(dt_stamp).strftime("%b %d, %H:%M") if dt_stamp else "Recent"
            news_list.append({
                "ticker": symbol, "headline": top_item.get('headline', 'No Headline'),
                "source": top_item.get('source', 'News'), "url": top_item.get('url', '#'), "date": date_formatted
            })
        time.sleep(0.2)

        return_10d_pct, price_10d, return_30d_pct, price_30d = get_historical_data_yahoo(symbol, last_price)
        if abs(daily_return_pct) >= 3.0 or abs(return_10d_pct) >= 5.0 or abs(return_30d_pct) >= 8.0:
            movers_list.append({
                "ticker": symbol, "price": round(last_price, 2), "daily_return": round(daily_return_pct, 2),
                "return_10d": round(return_10d_pct, 2), "price_10d": round(price_10d, 2),
                "return_30d": round(return_30d_pct, 2), "price_30d": round(price_30d, 2)
            })

        print(f"[{idx}/{len(tickers)}] ✅ Loaded {symbol}: ${last_price:.2f} [{comp_industry}]")
    except Exception as e:
        print(f"Error processing {symbol}: {e}")

# ==========================================
# 🧮 MARKET HOTNESS SPEED DIAL CALCULATION
# ==========================================
total_tracked = len(data_list)
above_50_count = sum(1 for item in data_list if item['pct'] > 50.0)
hotness_pct = (above_50_count / total_tracked * 100) if total_tracked > 0 else 0
needle_rotation = -90 + (hotness_pct / 100.0) * 180

if hotness_pct >= 70:
    hotness_status = "🔥 Overheated / Bullish"
elif hotness_pct >= 50:
    hotness_status = "⚡ Strong Momentum"
elif hotness_pct >= 30:
    hotness_status = "⚖️ Neutral / Balanced"
else:
    hotness_status = "❄️ Oversold / Bearish"

if movers_list:
    r1d_vals = [m['daily_return'] for m in movers_list]
    r10d_vals = [m['return_10d'] for m in movers_list]
    r30d_vals = [m['return_30d'] for m in movers_list]

    mean_1d, std_1d = statistics.mean(r1d_vals), (statistics.stdev(r1d_vals) if len(r1d_vals) > 1 and statistics.stdev(r1d_vals) > 0 else 1.0)
    mean_10d, std_10d = statistics.mean(r10d_vals), (statistics.stdev(r10d_vals) if len(r10d_vals) > 1 and statistics.stdev(r10d_vals) > 0 else 1.0)
    mean_30d, std_30d = statistics.mean(r30d_vals), (statistics.stdev(r30d_vals) if len(r30d_vals) > 1 and statistics.stdev(r30d_vals) > 0 else 1.0)

    for m in movers_list:
        z_1d = (m['daily_return'] - mean_1d) / std_1d
        z_10d = (m['return_10d'] - mean_10d) / std_10d
        z_30d = (m['return_30d'] - mean_30d) / std_30d
        m['composite_score'] = round((0.50 * z_1d) + (0.30 * z_10d) + (0.20 * z_30d), 3)

    movers_list.sort(key=lambda x: x['composite_score'], reverse=True)

data_list.sort(key=lambda x: x['pct'], reverse=True)
mid_idx = (len(data_list) + 1) // 2
data_left, data_right = data_list[:mid_idx], data_list[mid_idx:]

earnings_list.sort(key=lambda x: x['date'] if x['date'] != "TBD / Next Qtr" else "9999-99-99")
master_by_ticker = sorted(master_list, key=lambda x: x['ticker'])
master_by_industry = sorted(master_list, key=lambda x: (x['industry'], x['ticker']))

def build_watchlist_rows(items):
    rows = ""
    for item in items:
        calc_pct = lambda val: max(0, min(100, ((val - item['low52']) / (item['high52'] - item['low52'])) * 100)) if item['high52'] > item['low52'] else 50
        p_last, p_supp, p_ma50, p_ma200 = calc_pct(item['last']), calc_pct(item['supp']), calc_pct(item['ma50']), calc_pct(item['ma200'])
        
        pct_val = max(0.0, min(100.0, item['pct']))
        r_col = int(34 + (239 - 34) * (pct_val / 100.0))
        g_col = int(197 + (68 - 197) * (pct_val / 100.0))
        b_col = int(94 + (68 - 94) * (pct_val / 100.0))
        
        rows += f"""<tr class="watchlist-row">
            <td class="col-ticker"><strong>${item['ticker']}</strong></td>
            <td class="col-bar"><div class="range-bar-container"><div class="grid-line-33"></div><div class="grid-line-66"></div>
            <div class="marker-orange" style="left:{p_supp}%;" title="{item['ticker']} Support: ${item['supp']:,.2f}"></div>
            <div class="marker-yellow" style="left:{p_ma50}%;" title="{item['ticker']} 50d MA: ${item['ma50']:,.2f}"></div>
            <div class="marker-red" style="left:{p_ma200}%;" title="{item['ticker']} 200d MA: ${item['ma200']:,.2f}"></div>
            <div class="marker-cyan" style="left:{p_last}%;" title="{item['ticker']} Price: ${item['last']:,.2f}"></div></div></td>
            <td class="col-low52">${item['low52']:,.2f}</td><td class="col-price">${item['last']:,.2f}</td><td class="col-high52">${item['high52']:,.2f}</td>
            <td class="col-mini-gauge" style="background-color: rgba({r_col}, {g_col}, {b_col}, 0.85); color: #fff; font-weight: bold;"><span class="gauge-number">{item['pct']}%</span></td>
        </tr>"""
    return rows

def get_month_info(date_str):
    if not date_str or date_str == "TBD / Next Qtr" or len(date_str) < 7:
        return "m-shade-tbd", "TBD"
    month_names = {
        "01": ("m-shade-1", "JAN"), "02": ("m-shade-2", "FEB"), "03": ("m-shade-3", "MAR"),
        "04": ("m-shade-4", "APR"), "05": ("m-shade-1", "MAY"), "06": ("m-shade-2", "JUN"),
        "07": ("m-shade-3", "JUL"), "08": ("m-shade-1", "AUG"), "09": ("m-shade-2", "SEP"),
        "10": ("m-shade-3", "OCT"), "11": ("m-shade-4", "NOV"), "12": ("m-shade-1", "DEC")
    }
    return month_names.get(date_str[5:7], ("m-shade-tbd", "TBD"))

def build_earnings_rows(items):
    rows = ""
    for item in items:
        m_class, m_label = get_month_info(item['date'])
        rows += f"""<tr class="earnings-row">
            <td class="col-earn-ticker"><strong>${item['ticker']}</strong></td>
            <td class="col-earn-price price-col"><strong>${item['price']:,.2f}</strong></td>
            <td class="col-earn-date"><span class="month-pill {m_class}">{m_label}</span> {item['date']}</td>
            <td class="col-earn-status"><span class="{item['status_class']}">{item['status_text']}</span></td>
            <td class="col-earn-eps"><strong style="color:var(--accent-yellow);">{item['eps_est']}</strong></td>
            <td class="col-earn-move">{item['earn_move']}</td>
        </tr>"""
    return rows

def get_return_badge_html(val, min_threshold=0.0):
    val_str = f"+{val:.2f}%" if val > 0 else f"{val:.2f}%"
    if abs(val) <= min_threshold:
        return f'<span class="return-badge badge-neutral">{val_str}</span>'
    cls = "badge-strong-pos" if val >= 10.0 else ("badge-pos" if val > 0 else ("badge-strong-neg" if val <= -10.0 else "badge-neg"))
    return f'<span class="return-badge {cls}">{val_str}</span>'

def build_movers_rows(items):
    if not items:
        return """<tr><td colspan="5" style="text-align:center; color:var(--text-muted); padding:10px;">No significant movers detected.</td></tr>"""
    rows = ""
    for item in items:
        rows += f"""<tr class="movers-row">
            <td class="col-movers-ticker"><strong>${item['ticker']}</strong></td>
            <td class="col-movers-score"><span style="color:var(--accent-cyan); font-weight:bold;">{item['composite_score']:+.2f}</span></td>
            <td class="col-movers-combined"><div class="combined-cell">{get_return_badge_html(item['daily_return'], 2.0)}<span class="price-col">${item['price']:,.2f}</span></div></td>
            <td class="col-movers-combined"><div class="combined-cell">{get_return_badge_html(item['return_10d'], 5.0)}<span class="price-col">${item['price_10d']:,.2f}</span></div></td>
            <td class="col-movers-combined"><div class="combined-cell">{get_return_badge_html(item['return_30d'], 10.0)}<span class="price-col">${item['price_30d']:,.2f}</span></div></td>
        </tr>"""
    return rows

def build_news_rows(items):
    if not items:
        return """<tr><td colspan="4" style="text-align:center; color:var(--text-muted); padding:10px;">No recent company news found.</td></tr>"""
    rows = ""
    for item in items:
        rows += f"""<tr class="news-row">
            <td class="col-news-ticker"><strong>${item['ticker']}</strong></td>
            <td class="col-news-headline"><a href="{item['url']}" target="_blank" class="news-link">{item['headline']}</a></td>
            <td class="col-news-source"><span class="badge-confirmed">{item['source']}</span></td>
            <td class="col-news-date" style="color:var(--text-muted); font-size:0.65rem;">{item['date']}</td>
        </tr>"""
    return rows

def build_master_rows(items):
    rows = ""
    for item in items:
        rows += f"""<tr class="master-row">
            <td class="col-master-ticker"><strong>${item['ticker']}</strong></td>
            <td class="col-master-name">{item['name']}</td>
            <td class="col-master-industry"><span class="badge-confirmed">{item['industry']}</span></td>
            <td class="col-master-price price-col"><strong>${item['price']:,.2f}</strong></td>
            <td class="col-master-cap price-col">{item['mkt_cap']}</td>
            <td class="col-master-gauge"><span style="color:var(--accent-cyan);font-weight:bold;">{item['pct']}%</span></td>
        </tr>"""
    return rows

table_header_html = """<thead><tr class="watchlist-row"><th class="col-ticker">Ticker</th><th class="col-bar" style="text-align:center;">Range Bar (33% & 66% Grids)<div class="axis-labels"><span>0%</span><span style="color:#a78bfa;">33%</span><span style="color:#a78bfa;">66%</span><span>100%</span></div></th><th class="col-low52" style="text-align:right;">52W Low</th><th class="col-price" style="text-align:right;">Price</th><th class="col-high52" style="text-align:right;">52W High</th><th class="col-mini-gauge" style="text-align:center;">52W Pos</th></tr></thead>"""
earnings_header_html = """<thead><tr class="earnings-row"><th class="col-earn-ticker">Ticker</th><th class="col-earn-price" style="text-align:right;">Price</th><th class="col-earn-date">Date</th><th class="col-earn-status">Status</th><th class="col-earn-eps">EPS</th><th class="col-earn-move">Earnings Move ⚡</th></tr></thead>"""
movers_header_html = """<thead><tr class="movers-row"><th class="col-movers-ticker">Ticker</th><th class="col-movers-score">Score ↓</th><th class="col-movers-combined">1D Return / Price</th><th class="col-movers-combined">10D Return / Price</th><th class="col-movers-combined">30D Return / Price</th></tr></thead>"""
news_header_html = """<thead><tr class="news-row"><th class="col-news-ticker">Ticker</th><th class="col-news-headline">Latest Article Headline</th><th class="col-news-source">Source</th><th class="col-news-date">Published</th></tr></thead>"""
master_header_html = """<thead><tr class="master-row"><th class="col-master-ticker">Ticker</th><th class="col-master-name">Company Name</th><th class="col-master-industry">Industry</th><th class="col-master-price" style="text-align:right;">Price</th><th class="col-master-cap" style="text-align:right;">Market Cap</th><th class="col-master-gauge" style="text-align:center;">52W Pos</th></tr></thead>"""

# Changed from f"""...""" to standard multiline string """...""" so Python doesn't confuse CSS curly braces for f-string placeholders
condensed_css = f"""
:root{{--bg-dark:#130924;--bg-card:#21123b;--bg-row-alt:#190d30;--text-main:#f8fafc;--text-muted:#a78bfa;--accent-cyan:#38bdf8;--accent-orange:#fb923c;--accent-yellow:#facc15;--accent-red:#ef4444;--accent-green:#22c55e;--border-color:#3b2063;--channel-bar:#582f91;}}
*{{box-sizing:border-box;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;}}
body{{background-color:var(--bg-dark);color:var(--text-main);padding:8px 6px;font-size:0.72rem;line-height:1.15;}}
.container{{width:99.5%;max-width:1920px;margin:0 auto;}}
header{{padding-bottom:6px;border-bottom:1px solid var(--border-color);margin-bottom:8px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;}}
h1{{font-size:1.2rem;color:var(--accent-cyan);}}
.header-meta{{display:flex;gap:16px;align-items:center;flex-wrap:wrap;}}
.timestamp-banner{{background-color:rgba(56,189,248,0.1);color:var(--accent-cyan);border:1px solid rgba(56,189,248,0.25);padding:4px 10px;border-radius:4px;font-size:0.68rem;font-weight:600;display:inline-block;}}

.speed-dial-card{{background-color:var(--bg-card);border:1px solid var(--border-color);border-radius:6px;padding:6px 12px;display:flex;align-items:center;gap:12px;}}
.speed-dial-container{{position:relative;width:60px;height:30px;overflow:hidden;}}
.speed-dial-arc{{position:absolute;top:0;left:0;width:60px;height:60px;border-radius:50%;background:conic-gradient(from 270deg at 50% 50%, #22c55e 0deg, #facc15 90deg, #ef4444 180deg);clip-path:polygon(0 0, 100% 0, 100% 50%, 0 50%);}}
.speed-dial-needle{{position:absolute;bottom:0;left:29px;width:2px;height:26px;background-color:#fff;transform-origin:bottom center;transform:rotate({needle_rotation}deg);transition:transform 0.5s ease;z-index:3;}}
.speed-dial-pin{{position:absolute;bottom:-2px;left:26px;width:8px;height:8px;background-color:var(--accent-cyan);border-radius:50%;border:1px solid #fff;z-index:4;}}
.speed-dial-info{{display:flex;flex-direction:column;font-size:0.68rem;font-weight:bold;}}

.legend-bar{{background-color:var(--bg-card);padding:5px 12px;border-radius:6px;border:1px solid var(--border-color);display:flex;gap:12px;align-items:center;margin-bottom:8px;font-size:0.72rem;}}
.legend-item{{display:flex;align-items:center;gap:4px;font-weight:500;}}
.dot-cyan{{width:7px;height:7px;background-color:var(--accent-cyan);border-radius:50%;display:inline-block;}}
.bar-orange{{width:3px;height:9px;background-color:var(--accent-orange);display:inline-block;}}
.diamond-yellow{{width:6px;height:6px;background-color:var(--accent-yellow);transform:rotate(45deg);display:inline-block;}}
.square-red{{width:6px;height:6px;background-color:var(--accent-red);display:inline-block;}}
.line-grid{{width:1px;height:10px;border-right:1px dashed var(--text-muted);display:inline-block;margin:0 1px;}}
.dual-grid-wrapper{{display:flex;gap:10px;align-items:flex-start;margin-bottom:10px;}}
.grid-column{{flex:1;background-color:var(--bg-card);border-radius:6px;border:1px solid var(--border-color);padding:3px;overflow-x:auto;}}
table{{width:100%;border-collapse:collapse;text-align:left;}}
th{{background-color:#281545;padding:4px 6px;color:var(--text-muted);font-weight:600;border-bottom:1px solid var(--border-color);font-size:0.72rem;}}
td{{padding:4px 6px;border-bottom:1px solid var(--border-color);vertical-align:middle;white-space:nowrap;font-size:0.72rem;overflow:hidden;text-overflow:ellipsis;}}
tr:nth-child(even){{background-color:var(--bg-row-alt);}}
tr:hover{{background-color:rgba(167,139,250,0.12);}}

.watchlist-row{{display:table;width:100%;table-layout:fixed;}}
.col-ticker{{width:70px;}}
.col-bar{{width:auto;}}
.col-low52{{width:85px;text-align:right;}}
.col-price{{width:85px;text-align:right;}}
.col-high52{{width:85px;text-align:right;}}
.col-mini-gauge{{width:75px;text-align:center;}}

.movers-row{{display:table;width:100%;table-layout:fixed;}}
.col-movers-ticker{{width:65px;}}
.col-movers-score{{width:65px;}}
.col-movers-combined{{width:135px;}}
.combined-cell{{display:flex;justify-content:space-between;align-items:center;width:100%;}}

.earnings-row{{display:table;width:100%;table-layout:fixed;}}
.col-earn-ticker{{width:60px;}}
.col-earn-price{{width:70px;text-align:right;}}
.col-earn-date{{width:130px;}}
.col-earn-status{{width:100px;}}
.col-earn-eps{{width:55px;}}
.col-earn-move{{width:auto;}}

.news-row{{display:table;width:100%;table-layout:fixed;}}
.col-news-ticker{{width:65px;}}
.col-news-headline{{width:auto;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.col-news-source{{width:100px;}}
.col-news-date{{width:90px;}}
.news-link{{color:var(--text-main);text-decoration:none;font-weight:500;}}
.news-link:hover{{color:var(--accent-cyan);text-decoration:underline;}}

.master-row{{display:table;width:100%;table-layout:fixed;}}
.col-master-ticker{{width:65px;}}
.col-master-name{{width:160px;overflow:hidden;text-overflow:ellipsis;}}
.col-master-industry{{width:150px;overflow:hidden;text-overflow:ellipsis;}}
.col-master-price{{width:85px;text-align:right;}}
.col-master-cap{{width:95px;text-align:right;}}
.col-master-gauge{{width:75px;text-align:center;}}

.range-bar-container{{position:relative;width:100%;height:5px;background-color:var(--channel-bar);border-radius:3px;margin:2px 0;overflow:visible;}}
.grid-line-33{{position:absolute;top:-3px;bottom:-3px;left:33.33%;border-left:1px dashed rgba(255,255,255,0.35);z-index:1;pointer-events:none;}}
.grid-line-66{{position:absolute;top:-3px;bottom:-3px;left:66.66%;border-left:1px dashed rgba(255,255,255,0.35);z-index:1;pointer-events:none;}}
.marker-cyan{{position:absolute;top:-2px;width:9px;height:9px;background-color:var(--accent-cyan);border-radius:50%;border:1px solid #fff;transform:translateX(-50%);z-index:4;cursor:pointer;}}
.marker-orange{{position:absolute;top:-2.5px;width:2.5px;height:10px;background-color:var(--accent-orange);transform:translateX(-50%);z-index:2;cursor:pointer;}}
.marker-yellow{{position:absolute;top:-1px;width:7px;height:7px;background-color:var(--accent-yellow);transform:rotate(45deg);z-index:3;cursor:pointer;border:1px solid #000;}}
.marker-red{{position:absolute;top:-1px;width:7px;height:7px;background-color:var(--accent-red);transform:translateX(-50%);z-index:3;cursor:pointer;border:1px solid #fff;}}

.gauge-number{{font-size:0.72rem;font-weight:bold;}}
.axis-labels{{display:flex;justify-content:space-between;color:var(--text-muted);font-size:0.62rem;margin-top:1px;font-weight:600;}}
.section-title{{font-size:1.05rem;color:var(--accent-yellow);margin-bottom:6px;display:flex;align-items:center;gap:6px;font-weight:bold;}}
.badge-reported{{background-color:rgba(74,222,128,0.2);color:var(--accent-green);padding:1px 4px;border-radius:3px;font-weight:bold;font-size:0.68rem;}}
.badge-confirmed{{background-color:rgba(56,189,248,0.2);color:var(--accent-cyan);padding:1px 4px;border-radius:3px;font-weight:bold;font-size:0.68rem;}}
.badge-unconfirmed{{background-color:rgba(251,146,60,0.2);color:var(--accent-orange);padding:1px 4px;border-radius:3px;font-weight:bold;font-size:0.68rem;}}
.badge-next-month{{background-color:rgba(250,204,21,0.25);color:#facc15;border:1px solid rgba(250,204,21,0.5);padding:1px 5px;border-radius:3px;font-weight:bold;font-size:0.68rem;}}
.badge-month-after{{background-color:rgba(74,222,128,0.25);color:#4ade80;border:1px solid rgba(74,222,128,0.5);padding:1px 5px;border-radius:3px;font-weight:bold;font-size:0.68rem;}}
.badge-upcoming{{background-color:rgba(244,63,94,0.25);color:#fb7185;border:1px solid rgba(244,63,94,0.5);padding:1px 5px;border-radius:3px;font-weight:bold;font-size:0.68rem;}}
.return-badge{{padding:1px 4px;border-radius:3px;font-size:0.68rem;font-weight:600;display:inline-block;min-width:58px;text-align:center;}}
.badge-pos{{background-color:rgba(74,222,128,0.18);color:var(--accent-green);border:1px solid rgba(74,222,128,0.3);}}
.badge-strong-pos{{background-color:rgba(74,222,128,0.35);color:#22c55e;border:1px solid #4ade80;font-weight:bold;}}
.badge-neg{{background-color:rgba(248,113,113,0.18);color:var(--accent-red);border:1px solid rgba(248,113,113,0.3);}}
.badge-strong-neg{{background-color:rgba(248,113,113,0.35);color:#ef4444;border:1px solid #f87171;font-weight:bold;}}
.badge-neutral{{background:transparent;color:var(--text-main);border:1px solid transparent;font-weight:normal;}}
.price-col{{color:var(--text-muted);font-size:0.68rem;font-weight:500;font-family:monospace;text-align:right;}}
.month-pill{{display:inline-block;padding:1px 4px;border-radius:3px;font-size:0.62rem;font-weight:bold;margin-right:3px;text-transform:uppercase;}}
.month-pill.m-shade-1{{background-color:rgba(56,189,248,0.25);color:#38bdf8;border:1px solid rgba(56,189,248,0.4);}}
.month-pill.m-shade-2{{background-color:rgba(167,139,250,0.25);color:#a78bfa;border:1px solid rgba(167,139,250,0.4);}}
.month-pill.m-shade-3{{background-color:rgba(250,204,21,0.25);color:#facc15;border:1px solid rgba(250,204,21,0.4);}}
.month-pill.m-shade-4{{background-color:rgba(251,146,60,0.25);color:#fb923c;border:1px solid rgba(251,146,60,0.4);}}
.month-pill.m-shade-tbd{{background-color:rgba(100,116,139,0.25);color:#94a3b8;border:1px solid rgba(100,116,139,0.4);}}
"""

mid_news = (len(news_list) + 1) // 2
news_left, news_right = news_list[:mid_news], news_list[mid_news:]

html_content = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Jacob's Stock Dashboard</title><style>{condensed_css}</style></head>
<body><div class="container"><header>
    <div><h1>📊 Jacob's Technical Watchlist & Market Dashboard</h1></div>
    <div class="header-meta">
        <div class="timestamp-banner">⏱️ {generation_timestamp_str}</div>
        <div class="speed-dial-card">
            <div class="speed-dial-container">
                <div class="speed-dial-arc"></div>
                <div class="speed-dial-needle" style="transform: rotate({needle_rotation}deg);"></div>
                <div class="speed-dial-pin"></div>
            </div>
            <div class="speed-dial-info">
                <span>🌡️ Market Hotness</span>
                <span style="color:var(--accent-cyan);">{hotness_pct:.1f}% ({above_50_count}/{total_tracked})</span>
                <span style="font-size:0.62rem;color:var(--text-muted);">{hotness_status}</span>
            </div>
        </div>
    </div>
</header>
<div class="legend-bar"><span style="color:var(--text-muted);font-weight:600;">Indicator Key:</span><div class="legend-item"><span class="dot-cyan"></span> Live Price</div><div class="legend-item"><span class="bar-orange"></span> Support Level</div><div class="legend-item"><span class="diamond-yellow"></span> 50-Day Moving Avg</div><div class="legend-item"><span class="square-red"></span> 200-Day Moving Avg</div><div class="legend-item"><span class="line-grid"></span> 33% / 66% Range Dividers</div></div>

<div class="dual-grid-wrapper">
    <div class="grid-column"><table>{table_header_html}<tbody>{build_watchlist_rows(data_left)}</tbody></table></div>
    <div class="grid-column"><table>{table_header_html}<tbody>{build_watchlist_rows(data_right)}</tbody></table></div>
</div>

<div class="dual-grid-wrapper">
    <div class="grid-column">
        <div class="section-title">🚀 Significant Movers (Ranked by Multi-Timeframe Score)</div>
        <table>{movers_header_html}<tbody>{build_movers_rows(movers_list)}</tbody></table>
    </div>
    <div class="grid-column">
        <div class="section-title">📅 Quarterly Results Schedule</div>
        <table>{earnings_header_html}<tbody>{build_earnings_rows(earnings_list)}</tbody></table>
    </div>
</div>

<div class="dual-grid-wrapper">
    <div class="grid-column">
        <div class="section-title">📰 Critical Company News (Grid 1)</div>
        <table>{news_header_html}<tbody>{build_news_rows(news_left)}</tbody></table>
    </div>
    <div class="grid-column">
        <div class="section-title">📰 Critical Company News (Grid 2)</div>
        <table>{news_header_html}<tbody>{build_news_rows(news_right)}</tbody></table>
    </div>
</div>

<div class="dual-grid-wrapper" style="margin-top:6px;">
    <div class="grid-column">
        <div class="section-title">📋 Tracked Tickers (Sorted by Ticker)</div>
        <table>{master_header_html}<tbody>{build_master_rows(master_by_ticker)}</tbody></table>
    </div>
    <div class="grid-column">
        <div class="section-title">🏭 Tracked Tickers (Sorted by Industry)</div>
        <table>{master_header_html}<tbody>{build_master_rows(master_by_industry)}</tbody></table>
    </div>
</div>

</div></body></html>"""

date_filename_str = today.strftime("%Y.%m.%d")
output_filename = f"JacobsStockDashboard.{date_filename_str}.html"
output_path = os.path.join(os.getcwd(), output_filename)

with open(output_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"\n🌐 Dashboard successfully generated and saved to: {output_filename}")
print(f"⏱️ Timestamp included: {generation_timestamp_str}")
webbrowser.open(f"file://{os.path.abspath(output_path)}")

# 🔔 Completion Message
print("\n🎉 ALL TASKS COMPLETE: Jacob's Stock Dashboard generated, saved, and browser launched successfully!")
