import os, time, datetime, pytz, webbrowser, requests, statistics, json, subprocess

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

print("🚀 Starting Data Fetch (Jacob's Stock Dashboard with Eastern Time Filenames & Sync)...")

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
    ret_10d, ret_30d, ret_3mo = 0.0, 0.0, 0.0
    p_10d, p_30d, p_3mo = 0.0, 0.0, 0.0
    vol_ratio = 1.0
    closes = []
    timestamps = []
    formatted_dates = []
    try:
        yf_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=3mo&interval=1d"
        res = safe_api_get(yf_url, retries=2, delay=1, extra_headers=headers)
        result = res.get('chart', {}).get('result', [])
        if result:
            timestamps = result[0].get('timestamp', [])
            indicators = result[0].get('indicators', {})
            quote = indicators.get('quote', [{}])[0]
            closes = [c for c in quote.get('close', []) if c is not None]
            volumes = [v for v in quote.get('volume', []) if v is not None]
            
            if timestamps and closes:
                for ts in timestamps:
                    try:
                        formatted_dates.append(datetime.datetime.fromtimestamp(ts).strftime("%b %d, %Y"))
                    except Exception:
                        formatted_dates.append("N/A")
            
            if len(closes) >= 10:
                p_10d = closes[-11] if len(closes) >= 11 else closes[0]
                ret_10d = ((current_price - p_10d) / p_10d) * 100
            if len(closes) >= 30:
                p_30d = closes[-31] if len(closes) >= 31 else closes[0]
                ret_30d = ((current_price - p_30d) / p_30d) * 100
            if len(closes) > 0:
                p_3mo = closes[0]
                ret_3mo = ((current_price - p_3mo) / p_3mo) * 100
            
            if len(volumes) >= 5:
                today_vol = volumes[-1]
                avg_vol = statistics.mean(volumes[-20:]) if len(volumes) >= 20 else statistics.mean(volumes)
                if avg_vol > 0:
                    vol_ratio = round(today_vol / avg_vol, 1)
    except Exception:
        pass
    return ret_10d, p_10d, ret_30d, p_30d, ret_3mo, vol_ratio, closes, timestamps, formatted_dates

def get_earnings_move_yahoo(symbol, earn_date_str, hour_timing, est_today):
    if not earn_date_str or earn_date_str == 'N/A':
        return 0.0, False
    try:
        earn_date = datetime.datetime.strptime(earn_date_str, "%Y-%m-%d").date()
        if earn_date > est_today:
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

# Establish Eastern Time (ET)
est_tz = pytz.timezone('US/Eastern')
now_est = datetime.datetime.now(est_tz)
generation_timestamp_str = now_est.strftime("%b %d, %Y at %H:%M:%S %Z")
today_est = now_est.date()
past_week_str = (today_est - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
today_str = today_est.strftime("%Y-%m-%d")
future_str = (today_est + datetime.timedelta(days=120)).strftime("%Y-%m-%d")

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

        return_10d_pct, price_10d, return_30d_pct, price_30d, return_3mo_pct, vol_ratio, closes, timestamps, formatted_dates = get_historical_data_yahoo(symbol, last_price)

        svg_points = ""
        p_max, p_mid, p_min = last_price, last_price, last_price
        d_start, d_mid, d_end = "Start", "Mid", "End"
        is_pos = "false"
        start_y_pct = 50.0
        
        if closes and len(closes) > 1:
            recent_closes = closes
            recent_ts = timestamps if len(timestamps) >= len(recent_closes) else []
            
            if recent_ts:
                try:
                    d_start = datetime.datetime.fromtimestamp(recent_ts[0]).strftime("%b %d")
                    d_mid = datetime.datetime.fromtimestamp(recent_ts[len(recent_ts) // 2]).strftime("%b %d")
                    d_end = datetime.datetime.fromtimestamp(recent_ts[-1]).strftime("%b %d")
                except Exception:
                    pass

            if recent_closes[-1] > recent_closes[0]:
                is_pos = "true"

            min_c = min(recent_closes)
            max_c = max(recent_closes)
            c_range = (max_c - min_c) if max_c != min_c else 1.0
            width, height = 320, 130
            
            start_val = recent_closes[0]
            start_y_pct = ((start_val - min_c) / c_range) * 100

            pts = []
            for i, val in enumerate(recent_closes):
                x = (i / (len(recent_closes) - 1)) * width
                y = height - ((val - min_c) / c_range) * (height - 20) - 10
                pts.append(f"{x:.1f},{y:.1f}")
            svg_points = " ".join(pts)
            p_max = round(max_c, 2)
            p_mid = round((max_c + min_c) / 2, 2)
            p_min = round(min_c, 2)

        stock_item = {
            "ticker": symbol, "name": comp_name, "industry": comp_industry,
            "last": round(last_price, 2), "price": round(last_price, 2), "supp": round(supp, 2),
            "ma50": round(ma50, 2), "ma200": round(ma200, 2), "low52": round(low52, 2),
            "high52": round(high52, 2), "pct": round(pct_range, 1), "mkt_cap": mkt_cap_str,
            "vol_ratio": vol_ratio, "svg_points": svg_points, "p_max": p_max,
            "p_mid": p_mid, "p_min": p_min, "d_start": d_start, "d_mid": d_mid,
            "d_end": d_end, "is_pos": is_pos, "start_y_pct": round(start_y_pct, 1),
            "ret_3mo": round(return_3mo_pct, 2),
            "chart_closes": json.dumps(closes),
            "chart_dates": json.dumps(formatted_dates)
        }

        data_list.append(stock_item)
        master_list.append(stock_item)
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

            earn_move, has_moved = get_earnings_move_yahoo(symbol, earn_date_str, hour_raw, today_est)
            earn_move_badge = f'<span class="return-badge {"badge-pos" if earn_move > 0 else ("badge-neg" if earn_move < 0 else "badge-neutral")}">{f"+{earn_move:.2f}%" if earn_move > 0 else f"{earn_move:.2f}%"}</span>' if has_moved else '<span style="color:var(--text-muted);">-</span>'

            if eps_act is not None or (earn_date_str != 'N/A' and datetime.datetime.strptime(earn_date_str, "%Y-%m-%d").date() < today_est):
                status_class, status_text = "badge-reported", "Reported"
                eps_str = f"${eps_act:.2f}" if eps_act is not None else (f"${eps_est:.2f}" if eps_est is not None else "N/A")
            elif earn_date_str != 'N/A':
                try:
                    earn_date_obj = datetime.datetime.strptime(earn_date_str, "%Y-%m-%d").date()
                    cur_year, cur_month = today_est.year, today_est.month
                    next_month = cur_month + 1 if cur_month < 12 else 1
                    next_year = cur_year if cur_month < 12 else cur_year + 1
                    after_month = next_month + 1 if next_month < 12 else 1
                    after_year = next_year if next_month < 12 else next_year + 1
                    days_away = (earn_date_obj - today_est).days
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
                "ticker": symbol, "name": comp_name, "industry": comp_industry, "date": earn_date_str, "eps_est": eps_str, "timing": timing,
                "status_class": status_class, "status_text": status_text, "price": round(last_price, 2), "earn_move": earn_move_badge,
                "pct": round(pct_range, 1), "vol_ratio": vol_ratio, "svg_points": svg_points, "p_max": p_max, "p_mid": p_mid, "p_min": p_min,
                "d_start": d_start, "d_mid": d_mid, "d_end": d_end, "is_pos": is_pos, "start_y_pct": round(start_y_pct, 1), "ret_3mo": round(return_3mo_pct, 2),
                "chart_closes": json.dumps(closes), "chart_dates": json.dumps(formatted_dates)
            })
        else:
            earnings_list.append({
                "ticker": symbol, "name": comp_name, "industry": comp_industry, "date": "TBD / Next Qtr", "eps_est": "N/A", "timing": "TBD",
                "status_class": "badge-unconfirmed", "status_text": "Unconfirmed Est.", "price": round(last_price, 2), "earn_move": '<span style="color:var(--text-muted);">-</span>',
                "pct": round(pct_range, 1), "vol_ratio": vol_ratio, "svg_points": svg_points, "p_max": p_max, "p_mid": p_mid, "p_min": p_min,
                "d_start": d_start, "d_mid": d_mid, "d_end": d_end, "is_pos": is_pos, "start_y_pct": round(start_y_pct, 1), "ret_3mo": round(return_3mo_pct, 2),
                "chart_closes": json.dumps(closes), "chart_dates": json.dumps(formatted_dates)
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

        if abs(daily_return_pct) >= 3.0 or abs(return_10d_pct) >= 5.0 or abs(return_30d_pct) >= 8.0 or vol_ratio >= 1.5:
            movers_list.append({
                "ticker": symbol, "price": round(last_price, 2), "daily_return": round(daily_return_pct, 2),
                "return_10d": round(return_10d_pct, 2), "price_10d": round(price_10d, 2),
                "return_30d": round(return_30d_pct, 2), "price_30d": round(price_30d, 2),
                "vol_ratio": vol_ratio, "name": comp_name, "industry": comp_industry,
                "pct": round(pct_range, 1), "svg_points": svg_points,
                "p_max": p_max, "p_mid": p_mid, "p_min": p_min,
                "d_start": d_start, "d_mid": d_mid, "d_end": d_end, "is_pos": is_pos,
                "start_y_pct": round(start_y_pct, 1), "ret_3mo": round(return_3mo_pct, 2),
                "chart_closes": json.dumps(closes),
                "chart_dates": json.dumps(formatted_dates)
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
        
        if pct_val <= 40.0:
            factor = pct_val / 40.0
            r_col = int(22 + (34 - 22) * factor)
            g_col = int(160 + (197 - 160) * factor)
            b_col = int(90 + (94 - 90) * factor)
        elif pct_val <= 60.0:
            factor = (pct_val - 40.0) / 20.0
            r_col = int(230 + (250 - 230) * factor)
            g_col = int(180 + (204 - 180) * factor)
            b_col = int(20 + (21 - 20) * factor)
        else:
            factor = (pct_val - 60.0) / 40.0
            r_col = int(250 + (239 - 250) * factor)
            g_col = int(204 + (68 - 204) * factor)
            b_col = int(21 + (68 - 21) * factor)
        
        closes_json = item['chart_closes'].replace('"', '&quot;')
        dates_json = item['chart_dates'].replace('"', '&quot;')
        popup_args = f"'{item['ticker']}', '{item['name']}', '{item['industry']}', '{item['price']}', '{item['pct']}', '{item['vol_ratio']}', '{item['svg_points']}', '{item['p_max']}', '{item['p_mid']}', '{item['p_min']}', '{item['d_start']}', '{item['d_mid']}', '{item['d_end']}', {item['is_pos']}, {item['start_y_pct']}, {item['ret_3mo']}, '{closes_json}', '{dates_json}'"
        
        rows += f"""<tr class="watchlist-row">
            <td class="col-ticker clickable-cell" onclick="showSidePopup(event, {popup_args})"><span class="ticker-popup-link"><strong>${item['ticker']}</strong></span></td>
            <td class="col-bar clickable-cell" onclick="showSidePopup(event, {popup_args})"><div class="range-bar-container"><div class="grid-line-33"></div><div class="grid-line-66"></div>
            <div class="marker-orange" style="left:{p_supp}%;" title="{item['ticker']} Support: ${item['supp']:,.2f}"></div>
            <div class="marker-yellow" style="left:{p_ma50}%;" title="{item['ticker']} 50d MA: ${item['ma50']:,.2f}"></div>
            <div class="marker-red" style="left:{p_ma200}%;" title="{item['ticker']} 200d MA: ${item['ma200']:,.2f}"></div>
            <div class="marker-cyan" style="left:{p_last}%;" title="{item['ticker']} Price: ${item['last']:,.2f}"></div></div></td>
            <td class="col-low52 clickable-cell" onclick="showSidePopup(event, {popup_args})">${item['low52']:,.2f}</td>
            <td class="col-price clickable-cell" onclick="showSidePopup(event, {popup_args})">${item['last']:,.2f}</td>
            <td class="col-high52 clickable-cell" onclick="showSidePopup(event, {popup_args})">${item['high52']:,.2f}</td>
            <td class="col-mini-gauge clickable-cell" onclick="showSidePopup(event, {popup_args})" style="background-color: rgba({r_col}, {g_col}, {b_col}, 0.85); color: #fff; font-weight: bold;"><span class="gauge-number">{item['pct']}%</span></td>
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
        closes_json = item['chart_closes'].replace('"', '&quot;')
        dates_json = item['chart_dates'].replace('"', '&quot;')
        popup_args = f"'{item['ticker']}', '{item['name']}', '{item['industry']}', '{item['price']}', '{item['pct']}', '{item['vol_ratio']}', '{item['svg_points']}', '{item['p_max']}', '{item['p_mid']}', '{item['p_min']}', '{item['d_start']}', '{item['d_mid']}', '{item['d_end']}', {item['is_pos']}, {item['start_y_pct']}, {item['ret_3mo']}, '{closes_json}', '{dates_json}'"
        
        rows += f"""<tr class="earnings-row">
            <td class="col-earn-ticker clickable-cell" onclick="showSidePopup(event, {popup_args})"><span class="ticker-popup-link"><strong>${item['ticker']}</strong></span></td>
            <td class="col-earn-price price-col clickable-cell" onclick="showSidePopup(event, {popup_args})"><strong>${item['price']:,.2f}</strong></td>
            <td class="col-earn-date clickable-cell" onclick="showSidePopup(event, {popup_args})"><span class="month-pill {m_class}">{m_label}</span> {item['date']}</td>
            <td class="col-earn-status clickable-cell" onclick="showSidePopup(event, {popup_args})"><span class="{item['status_class']}">{item['status_text']}</span></td>
            <td class="col-earn-eps clickable-cell" onclick="showSidePopup(event, {popup_args})"><strong style="color:var(--accent-yellow);">{item['eps_est']}</strong></td>
            <td class="col-earn-move clickable-cell" onclick="showSidePopup(event, {popup_args})">{item['earn_move']}</td>
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
        vol_badge = f'<span class="vol-badge" title="Volume is {item["vol_ratio"]}x normal volume">⚡{item["vol_ratio"]}x Vol</span>' if item['vol_ratio'] >= 1.5 else f'<span style="color:var(--text-muted); font-size:0.65rem;">{item["vol_ratio"]}x Vol</span>'
        closes_json = item['chart_closes'].replace('"', '&quot;')
        dates_json = item['chart_dates'].replace('"', '&quot;')
        popup_args = f"'{item['ticker']}', '{item['name']}', '{item['industry']}', '{item['price']}', '{item['pct']}', '{item['vol_ratio']}', '{item['svg_points']}', '{item['p_max']}', '{item['p_mid']}', '{item['p_min']}', '{item['d_start']}', '{item['d_mid']}', '{item['d_end']}', {item['is_pos']}, {item['start_y_pct']}, {item['ret_3mo']}, '{closes_json}', '{dates_json}'"
        
        rows += f"""<tr class="movers-row">
            <td class="col-movers-ticker clickable-cell" onclick="showSidePopup(event, {popup_args})"><strong>${item['ticker']}</strong> {vol_badge}</td>
            <td class="col-movers-score clickable-cell" onclick="showSidePopup(event, {popup_args})"><span style="color:var(--accent-cyan); font-weight:bold;">{item['composite_score']:+.2f}</span></td>
            <td class="col-movers-combined clickable-cell" onclick="showSidePopup(event, {popup_args})"><div class="combined-cell">{get_return_badge_html(item['daily_return'], 2.0)}<span class="price-col">${item['price']:,.2f}</span></div></td>
            <td class="col-movers-combined clickable-cell" onclick="showSidePopup(event, {popup_args})"><div class="combined-cell">{get_return_badge_html(item['return_10d'], 5.0)}<span class="price-col">${item['price_10d']:,.2f}</span></div></td>
            <td class="col-movers-combined clickable-cell" onclick="showSidePopup(event, {popup_args})"><div class="combined-cell">{get_return_badge_html(item['return_30d'], 10.0)}<span class="price-col">${item['price_30d']:,.2f}</span></div></td>
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
        closes_json = item['chart_closes'].replace('"', '&quot;')
        dates_json = item['chart_dates'].replace('"', '&quot;')
        popup_args = f"'{item['ticker']}', '{item['name']}', '{item['industry']}', '{item['price']}', '{item['pct']}', '{item['vol_ratio']}', '{item['svg_points']}', '{item['p_max']}', '{item['p_mid']}', '{item['p_min']}', '{item['d_start']}', '{item['d_mid']}', '{item['d_end']}', {item['is_pos']}, {item['start_y_pct']}, {item['ret_3mo']}, '{closes_json}', '{dates_json}'"
        
        rows += f"""
        <tr class="master-row">
            <td class="col-master-ticker clickable-cell" onclick="showSidePopup(event, {popup_args})"><span class="ticker-popup-link"><strong>${item['ticker']}</strong></span></td>
            <td class="col-master-name clickable-cell" onclick="showSidePopup(event, {popup_args})">{item['name']}</td>
            <td class="col-master-industry clickable-cell" onclick="showSidePopup(event, {popup_args})"><span class="badge-confirmed">{item['industry']}</span></td>
            <td class="col-master-price price-col clickable-cell" onclick="showSidePopup(event, {popup_args})"><strong>${item['price']:,.2f}</strong></td>
            <td class="col-master-cap price-col clickable-cell" onclick="showSidePopup(event, {popup_args})">{item['mkt_cap']}</td>
            <td class="col-master-gauge clickable-cell" onclick="showSidePopup(event, {popup_args})" style="color:var(--accent-cyan);font-weight:bold;"><span class="gauge-number">{item['pct']}%</span></td>
        </tr>"""
    return rows

table_header_html = """<thead><tr class="watchlist-row"><th class="col-ticker">Ticker</th><th class="col-bar" style="text-align:center;">Range Bar (33% & 66% Grids)<div class="axis-labels"><span>0%</span><span style="color:#a78bfa;">33%</span><span style="color:#a78bfa;">66%</span><span>100%</span></div></th><th class="col-low52" style="text-align:right;">52W Low</th><th class="col-price" style="text-align:right;">Price</th><th class="col-high52" style="text-align:right;">52W High</th><th class="col-mini-gauge" style="text-align:center;">52W Pos</th></tr></thead>"""
earnings_header_html = """<thead><tr class="earnings-row"><th class="col-earn-ticker">Ticker</th><th class="col-earn-price" style="text-align:right;">Price</th><th class="col-earn-date">Date</th><th class="col-earn-status">Status</th><th class="col-earn-eps">EPS</th><th class="col-earn-move">Earnings Move ⚡</th></tr></thead>"""
movers_header_html = """<thead><tr class="movers-row"><th class="col-movers-ticker">Ticker & Vol</th><th class="col-movers-score">Score ↓</th><th class="col-movers-combined">1D Return / Price</th><th class="col-movers-combined">10D Return / Price</th><th class="col-movers-combined">30D Return / Price</th></tr></thead>"""
news_header_html = """<thead><tr class="news-row"><th class="col-news-ticker">Ticker</th><th class="col-news-headline">Latest Article Headline</th><th class="col-news-source">Source</th><th class="col-news-date">Published</th></tr></thead>"""
master_header_html = """<thead><tr class="master-row"><th class="col-master-ticker">Ticker</th><th class="col-master-name">Company Name</th><th class="col-master-industry">Industry</th><th class="col-master-price" style="text-align:right;">Price</th><th class="col-master-cap" style="text-align:right;">Market Cap</th><th class="col-master-gauge" style="text-align:center;">52W Pos</th></tr></thead>"""

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
table{{width:100%;border-collapse:collapse;text-align:left;table-layout:fixed;}}
th{{background-color:#281545;padding:4px 6px;color:var(--text-muted);font-weight:600;border-bottom:1px solid var(--border-color);font-size:0.72rem;overflow:hidden;text-overflow:ellipsis;}}
td{{padding:4px 6px;border-bottom:1px solid var(--border-color);vertical-align:middle;white-space:nowrap;font-size:0.72rem;overflow:hidden;text-overflow:ellipsis;}}
tr:nth-child(even){{background-color:var(--bg-row-alt);}}

.clickable-cell {{ cursor: pointer; }}
.clickable-cell:hover {{ background-color: rgba(56, 189, 248, 0.15); }}

.watchlist-row{{display:table;width:100%;table-layout:fixed;}}
.col-ticker{{width:70px;}}
.col-bar{{width:auto;}}
.col-low52{{width:85px;text-align:right;}}
.col-price{{width:85px;text-align:right;}}
.col-high52{{width:85px;text-align:right;}}
.col-mini-gauge{{width:75px;text-align:center;}}

.movers-row{{display:table;width:100%;table-layout:fixed;}}
.col-movers-ticker{{width:85px;}}
.col-movers-score{{width:55px;}}
.col-movers-combined{{width:135px;}}
.combined-cell{{display:flex;justify-content:space-between;align-items:center;width:100%;}}

.earnings-row{{display:table;width:100%;table-layout:fixed;}}
.col-earn-ticker{{width:65px;}}
.col-earn-price{{width:75px;text-align:right;}}
.col-earn-date{{width:125px;}}
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
.col-master-name{{width:150px;overflow:hidden;text-overflow:ellipsis;}}
.col-master-industry{{width:150px;overflow:hidden;text-overflow:ellipsis;}}
.col-master-price{{width:85px;text-align:right;}}
.col-master-cap{{width:95px;text-align:right;}}
.col-master-gauge{{width:75px;text-align:center;}}

/* Floating Side Popup Card CSS */
#sideSparklinePopup {{
    display: none;
    position: absolute;
    width: 390px;
    background: var(--bg-card);
    border: 1px solid var(--accent-cyan);
    border-radius: 8px;
    padding: 12px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.6);
    z-index: 9999;
}}

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

html_content = f"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Jacob's Stock Dashboard - {today_est.strftime('%b %d, %Y')}</title><style>{condensed_css}</style></head>
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
    <div class="grid-column">
        <div class="section-title">⚡ Technical Watchlist (Grid 1)</div>
        <table>{table_header_html}<tbody>{build_watchlist_rows(data_left)}</tbody></table>
    </div>
    <div class="grid-column">
        <div class="section-title">⚡ Technical Watchlist (Grid 2)</div>
        <table>{table_header_html}<tbody>{build_watchlist_rows(data_right)}</tbody></table>
    </div>
</div>

<div class="dual-grid-wrapper">
    <div class="grid-column">
        <div class="section-title">🚀 Significant Movers & Volume Spikes</div>
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
        <div class="section-title">📋 Tracked Tickers (Click Any Cell for Sparkline)</div>
        <table>{master_header_html}<tbody>{build_master_rows(master_by_ticker)}</tbody></table>
    </div>
    <div class="grid-column">
        <div class="section-title">🏭 Tracked Tickers (Sorted by Industry)</div>
        <table>{master_header_html}<tbody>{build_master_rows(master_by_industry)}</tbody></table>
    </div>
</div>

</div>

<div id="sideSparklinePopup" onclick="event.stopPropagation()">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
        <span id="popTicker" style="color: var(--accent-cyan); font-weight: bold; font-size: 0.9rem;"></span>
        <span style="cursor: pointer; font-size: 1rem; color: var(--text-muted);" onclick="closeSidePopup()">&times;</span>
    </div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
        <div id="popInfo" style="font-size: 0.7rem; line-height: 1.3;"></div>
        <div id="popReturnBanner" style="font-size: 0.72rem; font-weight: bold; padding: 2px 8px; border-radius: 4px;"></div>
    </div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
        <div id="popHoverTip" style="font-size: 0.68rem; color: var(--accent-yellow); font-family: monospace; font-weight: bold; background: rgba(250,204,21,0.1); padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(250,204,21,0.3);">Hover chart for price</div>
    </div>
    <div style="display: flex; align-items: center; gap: 8px;">
        <div style="display: flex; flex-direction: column;">
            <svg id="popSvg" viewBox="0 0 320 130" width="320" height="130" style="background:var(--bg-dark); border-radius:6px; border:1px solid var(--border-color); cursor: crosshair;">
                <line x1="0" y1="32.5" x2="320" y2="32.5" stroke="rgba(255,255,255,0.12)" stroke-dasharray="2,2"/>
                <line x1="0" y1="65" x2="320" y2="65" stroke="rgba(255,255,255,0.12)" stroke-dasharray="2,2"/>
                <line x1="0" y1="97.5" x2="320" y2="97.5" stroke="rgba(255,255,255,0.12)" stroke-dasharray="2,2"/>
                <line x1="106.6" y1="0" x2="106.6" y2="130" stroke="rgba(255,255,255,0.12)" stroke-dasharray="2,2"/>
                <line x1="213.3" y1="0" x2="213.3" y2="130" stroke="rgba(255,255,255,0.12)" stroke-dasharray="2,2"/>
                <line id="popBaseLine" x1="0" y1="65" x2="320" y2="65" stroke="rgba(255,255,255,0.5)" stroke-dasharray="3,3" stroke-width="1.2"/>
                <polyline id="popPolyline" fill="none" stroke-width="2" points=""/>
                <line id="hoverLine" x1="0" y1="0" x2="0" y2="130" stroke="var(--accent-cyan)" stroke-width="1" stroke-dasharray="1,1" style="display: none;"/>
                <circle id="hoverDot" cx="0" cy="0" r="4" fill="var(--accent-cyan)" stroke="#fff" stroke-width="1" style="display: none;"/>
            </svg>
            <div style="display: flex; justify-content: space-between; font-size: 0.62rem; color: var(--text-muted); font-weight: 600; margin-top: 3px; padding: 0 2px;">
                <span id="labelStart"></span>
                <span id="labelMidDate"></span>
                <span id="labelEnd"></span>
            </div>
        </div>
        <div style="display: flex; flex-direction: column; justify-content: space-between; height: 130px; font-size: 0.65rem; font-family: monospace; color: var(--text-muted); font-weight: bold; margin-bottom: 14px;">
            <span id="labelMax"></span>
            <span id="labelMid"></span>
            <span id="labelMin"></span>
        </div>
    </div>
    <div style="margin-top: 6px; text-align: center;">
        <a id="popYahooLink" href="#" target="_blank" style="color:var(--accent-cyan); text-decoration:underline; font-size:0.68rem; font-weight:bold;">Yahoo Finance ↗</a>
    </div>
</div>

<script>
let currentCloses = [];
let currentDates = [];
let currentMin = 0;
let currentMax = 0;

function showSidePopup(event, ticker, name, industry, price, pct, vol, svgPoints, pMax, pMid, pMin, dStart, dMid, dEnd, isPos, startYPct, ret3mo, closesInput, datesInput) {{
    event.stopPropagation();
    const popup = document.getElementById('sideSparklinePopup');
    
    try {{
        currentCloses = typeof closesInput === 'string' ? JSON.parse(closesInput) : closesInput;
        currentDates = typeof datesInput === 'string' ? JSON.parse(datesInput) : datesInput;
    }} catch (e) {{
        currentCloses = [];
        currentDates = [];
    }}
    
    currentMin = parseFloat(pMin);
    currentMax = parseFloat(pMax);
    
    document.getElementById('popTicker').innerText = '$' + ticker + ' (' + name + ')';
    document.getElementById('popInfo').innerHTML = 'Ind: <b>' + industry + '</b><br>Price: <b>$' + price + '</b> | 52W: <b>' + pct + '%</b>';
    document.getElementById('popHoverTip').innerText = 'Hover chart for price';
    
    const banner = document.getElementById('popReturnBanner');
    const retNum = parseFloat(ret3mo);
    const retStr = (retNum > 0 ? '+' : '') + retNum.toFixed(2) + '% 3M';
    banner.innerText = retStr;
    if (retNum > 0) {{
        banner.style.backgroundColor = 'rgba(74,222,128,0.2)';
        banner.style.color = '#22c55e';
        banner.style.border = '1px solid rgba(74,222,128,0.4)';
    }} else if (retNum < 0) {{
        banner.style.backgroundColor = 'rgba(248,113,113,0.2)';
        banner.style.color = '#ef4444';
        banner.style.border = '1px solid rgba(248,113,113,0.4)';
    }} else {{
        banner.style.backgroundColor = 'rgba(100,116,139,0.2)';
        banner.style.color = '#94a3b8';
        banner.style.border = '1px solid rgba(100,116,139,0.4)';
    }}
    
    const chartHeight = 130;
    const lineY = chartHeight - (parseFloat(startYPct) / 100) * chartHeight;
    const baseLine = document.getElementById('popBaseLine');
    baseLine.setAttribute('y1', lineY);
    baseLine.setAttribute('y2', lineY);

    const polyline = document.getElementById('popPolyline');
    polyline.setAttribute('points', svgPoints);
    polyline.setAttribute('stroke', isPos ? '#22c55e' : '#ef4444');

    document.getElementById('labelMax').innerText = '$' + pMax;
    document.getElementById('labelMid').innerText = '$' + pMid;
    document.getElementById('labelMin').innerText = '$' + pMin;
    document.getElementById('labelStart').innerText = dStart;
    document.getElementById('labelMidDate').innerText = dMid;
    document.getElementById('labelEnd').innerText = dEnd;
    document.getElementById('popYahooLink').href = 'https://finance.yahoo.com/quote/' + ticker;
    
    popup.style.display = 'block';
    
    const cellRect = event.currentTarget.getBoundingClientRect();
    const popupWidth = popup.offsetWidth || 390;
    
    let leftPos = window.scrollX + cellRect.right + 12;
    if (leftPos + popupWidth > window.innerWidth + window.scrollX) {{
        leftPos = window.scrollX + cellRect.left - popupWidth - 12;
        if (leftPos < window.scrollX) {{
            leftPos = window.scrollX + 12;
        }}
    }}
    
    popup.style.top = (window.scrollY + cellRect.top) + 'px';
    popup.style.left = leftPos + 'px';
}}

// SVG Hover Event Handlers for Proportional Chart
document.addEventListener("DOMContentLoaded", function() {{
    const svg = document.getElementById('popSvg');
    const hoverLine = document.getElementById('hoverLine');
    const hoverDot = document.getElementById('hoverDot');
    const hoverTip = document.getElementById('popHoverTip');

    if (svg) {{
        svg.addEventListener('mousemove', function(e) {{
            if (!currentCloses || currentCloses.length === 0) return;
            const rect = svg.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const svgWidth = 320;
            const svgHeight = 130;

            let xPct = Math.max(0, Math.min(1, mouseX / svgWidth));
            let index = Math.round(xPct * (currentCloses.length - 1));
            
            if (index < 0) index = 0;
            if (index >= currentCloses.length) index = currentCloses.length - 1;

            const val = currentCloses[index];
            const dateStr = currentDates[index] || 'Recent';

            const xCoord = (index / (currentCloses.length - 1)) * svgWidth;
            const cRange = (currentMax !== currentMin) ? (currentMax - currentMin) : 1.0;
            const yCoord = svgHeight - ((val - currentMin) / cRange) * (svgHeight - 20) - 10;

            hoverLine.setAttribute('x1', xCoord);
            hoverLine.setAttribute('x2', xCoord);
            hoverLine.style.display = 'block';

            hoverDot.setAttribute('cx', xCoord);
            hoverDot.setAttribute('cy', yCoord);
            hoverDot.style.display = 'block';

            hoverTip.innerText = dateStr + ' : $' + val.toFixed(2);
        }});

        svg.addEventListener('mouseleave', function() {{
            hoverLine.style.display = 'none';
            hoverDot.style.display = 'none';
            hoverTip.innerText = 'Hover chart for price';
        }});
    }}
}});

function closeSidePopup() {{
    document.getElementById('sideSparklinePopup').style.display = 'none';
}}

window.addEventListener('click', function(e) {{
    const popup = document.getElementById('sideSparklinePopup');
    if (!popup.contains(e.target)) {{
        popup.style.display = 'none';
    }}
}});
</script>

</body></html>"""

# Generate filename based strictly on Eastern Time (ET) date format (e.g. JacobsStockDashboard.2026.08.10.html)
date_filename_str = today_est.strftime("%Y.%m.%d")
output_filename = f"JacobsStockDashboard.{date_filename_str}.html"
output_path = os.path.join(os.getcwd(), output_filename)

with open(output_path, "w", encoding="utf-8") as f:
    f.write(html_content)

# Update index.html for live GitHub Pages root access
index_output_path = os.path.join(os.getcwd(), "index.html")
with open(index_output_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"\n🌐 Dashboard successfully generated and saved as: {output_filename}")

# Auto-commit and push permanent daily archives to GitHub
try:
    print("\n🔄 Syncing and pushing archives to GitHub...")
    subprocess.run(["git", "add", output_path], check=True)
    subprocess.run(["git", "add", index_output_path], check=True)
    subprocess.run(["git", "add", __file__], check=True)
    commit_message = f"Add daily archived stock dashboard for {today_est.strftime('%b %d, %Y')} (ET)"
    subprocess.run(["git", "commit", "-m", commit_message], check=True)
    subprocess.run(["git", "push", "origin", "main"], check=True)
    print("🚀 Successfully pushed files and archives to GitHub!")
except Exception as e:
    print(f"⚠️ Git auto-push skipped or failed: {e}")

webbrowser.open(f"file://{os.path.abspath(output_path)}")
print("\n🎉 ALL TASKS COMPLETE: Eastern Time filename applied, archived, and pushed successfully!")
