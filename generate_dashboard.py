import os, time, datetime, webbrowser, requests, statistics, json, subprocess, shutil
from zoneinfo import ZoneInfo

# ==========================================
# 🔑 FINNHUB API KEY & CUSTOM INDUSTRY MAPPINGS
# ==========================================
API_KEY = os.getenv("FINNHUB_API_KEY", "d9rihopr01qoo7o4k3igd9rihopr01qoo7o4k3j0")

CUSTOM_INDUSTRY_MAP = {
    "REGN": "Biotech And Healthcare", "ISRG": "Biotech And Healthcare", "LLY": "Biotech And Healthcare", "VRTX": "Biotech And Healthcare",
    "JPM": "Financial Services", "V": "Financial Services", "BLK": "Financial Services", "COIN": "Financial Services", "GS": "Financial Services",
    "BE": "Engineering And Chips", "ETN": "Engineering And Chips", "GEV": "Engineering And Chips", "GLW": "Engineering And Chips", "CAT": "Engineering And Chips", "ANET": "Engineering And Chips", "VRT": "Engineering And Chips", "MRVL": "Engineering And Chips",
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

print("🚀 Starting Data Fetch (Jacob's Stock Dashboard - Within 5% Peak Green Rule Applied)...")

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
    ret_10d, p_10d = 0.0, 0.0
    ret_30d, p_30d = 0.0, 0.0
    ret_3m, p_3m = 0.0, 0.0
    ret_6mo, p_6mo = 0.0, 0.0
    vol_ratio = 1.0
    closes = []
    timestamps = []
    formatted_dates = []
    try:
        yf_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=6mo&interval=1d"
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
            
            if closes and current_price and closes[-1] != current_price:
                closes.append(current_price)
                timestamps.append(int(time.time()))
                formatted_dates.append(datetime.datetime.now(ZoneInfo("America/New_York")).strftime("%b %d, %Y"))

            if len(closes) >= 10:
                p_10d = closes[-11] if len(closes) >= 11 else closes[0]
                ret_10d = ((current_price - p_10d) / p_10d) * 100
            elif len(closes) > 0:
                p_10d = closes[0]
                ret_10d = ((current_price - p_10d) / p_10d) * 100

            if len(closes) >= 21:
                p_30d = closes[-21]
                ret_30d = ((current_price - p_30d) / p_30d) * 100
            elif len(closes) > 0:
                p_30d = closes[0]
                ret_30d = ((current_price - p_30d) / p_30d) * 100

            if len(closes) >= 63:
                p_3m = closes[-63]
                ret_3m = ((current_price - p_3m) / p_3m) * 100
            elif len(closes) > 0:
                p_3m = closes[0]
                ret_3m = ((current_price - p_3m) / p_3m) * 100

            if len(closes) > 0:
                p_6mo = closes[0]
                ret_6mo = ((current_price - p_6mo) / p_6mo) * 100
            
            if len(volumes) >= 5:
                today_vol = volumes[-1]
                avg_vol = statistics.mean(volumes[-20:]) if len(volumes) >= 20 else statistics.mean(volumes)
                if avg_vol > 0:
                    vol_ratio = round(today_vol / avg_vol, 1)
    except Exception:
        pass
    return ret_10d, p_10d, ret_30d, p_30d, ret_3m, p_3m, ret_6mo, vol_ratio, closes, timestamps, formatted_dates

def get_earnings_move_yahoo(symbol, earn_date_str, hour_timing, est_today):
    if not earn_date_str or earn_date_str == 'N/A':
        return 0.0, False
    try:
        earn_date = datetime.datetime.strptime(earn_date_str, "%Y-%m-%d").date()
        if earn_date > est_today:
            return 0.0, False
        yf_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=6mo&interval=1d"
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

now = datetime.datetime.now(ZoneInfo("America/New_York"))
generation_timestamp_str = now.strftime("%b %d, %Y at %H:%M:%S %Z")
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

        return_10d_pct, price_10d, return_30d_pct, price_30d, return_3m_pct, price_3m, return_6mo_pct, vol_ratio, closes, timestamps, formatted_dates = get_historical_data_yahoo(symbol, last_price)

        svg_points = ""
        ma30_svg_points = ""
        p_max, p_mid, p_min = last_price, last_price, last_price
        d_start, d_mid, d_end = "Start", "Mid", "End"
        is_pos = "false"
        start_y_pct = 50.0
        importance_notes = []
        month_end_x_coords = []
        ret_peak_curr_pct = 0.0
        
        if closes and len(closes) > 1:
            recent_closes = closes
            recent_ts = timestamps if len(timestamps) >= len(recent_closes) else []
            
            ma30_values = []
            window = 30
            for i in range(len(recent_closes)):
                if i < window - 1:
                    subset = recent_closes[:i+1]
                else:
                    subset = recent_closes[i - window + 1 : i + 1]
                ma30_values.append(statistics.mean(subset))

            width, height = 320, 110
            min_c = min(recent_closes)
            max_c = max(recent_closes)
            min_idx = recent_closes.index(min_c)
            max_idx = recent_closes.index(max_c)
            
            if max_c > 0:
                ret_peak_curr_pct = ((last_price - max_c) / max_c) * 100.0

            if recent_ts:
                try:
                    d_start = datetime.datetime.fromtimestamp(recent_ts[0]).strftime("%b %d")
                    d_mid = datetime.datetime.fromtimestamp(recent_ts[len(recent_ts) // 2]).strftime("%b %d")
                    d_end = datetime.datetime.fromtimestamp(recent_ts[-1]).strftime("%b %d")
                    
                    prev_month = None
                    for idx_t, ts in enumerate(recent_ts):
                        dt = datetime.datetime.fromtimestamp(ts)
                        curr_month = dt.month
                        if prev_month is not None and curr_month != prev_month:
                            x_pos = (idx_t / (len(recent_closes) - 1)) * width
                            month_end_x_coords.append(round(x_pos, 1))
                        prev_month = curr_month
                except Exception:
                    pass

            if recent_closes[-1] > recent_closes[0]:
                is_pos = "true"

            if recent_ts and len(recent_ts) > min_idx and len(recent_ts) > max_idx:
                low_date = datetime.datetime.fromtimestamp(recent_ts[min_idx]).strftime("%b %d")
                high_date = datetime.datetime.fromtimestamp(recent_ts[max_idx]).strftime("%b %d")
                importance_notes.append(f"📉 Trough: ${min_c:,.2f} ({low_date})")
                importance_notes.append(f"📈 Peak: ${max_c:,.2f} ({high_date})")
            
            c_range = (max_c - min_c) if max_c != min_c else 1.0
            start_val = recent_closes[0]
            start_y_pct = ((start_val - min_c) / c_range) * 100

            pts = []
            ma_pts = []
            for i, val in enumerate(recent_closes):
                x = (i / (len(recent_closes) - 1)) * width
                y = height - ((val - min_c) / c_range) * (height - 20) - 10
                pts.append(f"{x:.1f},{y:.1f}")
                
                ma_val = ma30_values[i]
                y_ma = height - ((ma_val - min_c) / c_range) * (height - 20) - 10
                ma_pts.append(f"{x:.1f},{y_ma:.1f}")

            svg_points = " ".join(pts)
            ma30_svg_points = " ".join(ma_pts)
            p_max = round(max_c, 2)
            p_mid = round((max_c + min_c) / 2, 2)
            p_min = round(min_c, 2)
            
            importance_notes.append(f"⚡ Peak->Curr: {ret_peak_curr_pct:+.2f}%")
            importance_notes.append(f"⚡ 6M: {return_6mo_pct:+.2f}%")

        stock_item = {
            "ticker": symbol, "name": comp_name, "industry": comp_industry,
            "last": round(last_price, 2), "price": round(last_price, 2), "supp": round(supp, 2),
            "ma50": round(ma50, 2), "ma200": round(ma200, 2), "low52": round(low52, 2),
            "high52": round(high52, 2), "pct": round(pct_range, 1), "mkt_cap": mkt_cap_str,
            "vol_ratio": vol_ratio, "svg_points": svg_points, "ma30_svg_points": ma30_svg_points, "p_max": p_max,
            "p_mid": p_mid, "p_min": p_min, "d_start": d_start, "d_mid": d_mid,
            "d_end": d_end, "is_pos": is_pos, "start_y_pct": round(start_y_pct, 1),
            "ret_1m": round(return_30d_pct, 2),
            "ret_3m": round(return_3m_pct, 2),
            "ret_6mo": round(return_6mo_pct, 2),
            "ret_peak_curr": round(ret_peak_curr_pct, 2),
            "importance_notes": " | ".join(importance_notes),
            "month_ends": json.dumps(month_end_x_coords),
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

            earn_move, has_moved = get_earnings_move_yahoo(symbol, earn_date_str, hour_raw, today)
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
                "ticker": symbol, "name": comp_name, "industry": comp_industry, "date": earn_date_str, "eps_est": eps_str, "timing": timing,
                "status_class": status_class, "status_text": status_text, "price": round(last_price, 2), "earn_move": earn_move_badge,
                "pct": round(pct_range, 1), "vol_ratio": vol_ratio, "svg_points": svg_points, "ma30_svg_points": ma30_svg_points, "p_max": p_max, "p_mid": p_mid, "p_min": p_min,
                "d_start": d_start, "d_mid": d_mid, "d_end": d_end, "is_pos": is_pos, "start_y_pct": round(start_y_pct, 1), 
                "ret_1m": round(return_30d_pct, 2),
                "ret_3m": round(return_3m_pct, 2),
                "ret_6mo": round(return_6mo_pct, 2),
                "ret_peak_curr": round(ret_peak_curr_pct, 2), "importance_notes": " | ".join(importance_notes), "month_ends": json.dumps(month_end_x_coords),
                "chart_closes": json.dumps(closes), "chart_dates": json.dumps(formatted_dates)
            })
        else:
            earnings_list.append({
                "ticker": symbol, "name": comp_name, "industry": comp_industry, "date": "TBD / Next Qtr", "eps_est": "N/A", "timing": "TBD",
                "status_class": "badge-unconfirmed", "status_text": "Unconfirmed Est.", "price": round(last_price, 2), "earn_move": '<span style="color:var(--text-muted);">-</span>',
                "pct": round(pct_range, 1), "vol_ratio": vol_ratio, "svg_points": svg_points, "ma30_svg_points": ma30_svg_points, "p_max": p_max, "p_mid": p_mid, "p_min": p_min,
                "d_start": d_start, "d_mid": d_mid, "d_end": d_end, "is_pos": is_pos, "start_y_pct": round(start_y_pct, 1), 
                "ret_1m": round(return_30d_pct, 2),
                "ret_3m": round(return_3m_pct, 2),
                "ret_6mo": round(return_6mo_pct, 2),
                "ret_peak_curr": round(ret_peak_curr_pct, 2), "importance_notes": " | ".join(importance_notes), "month_ends": json.dumps(month_end_x_coords),
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
                "pct": round(pct_range, 1), "svg_points": svg_points, "ma30_svg_points": ma30_svg_points,
                "p_max": p_max, "p_mid": p_mid, "p_min": p_min,
                "d_start": d_start, "d_mid": d_mid, "d_end": d_end, "is_pos": is_pos,
                "start_y_pct": round(start_y_pct, 1), 
                "ret_1m": round(return_30d_pct, 2),
                "ret_3m": round(return_3m_pct, 2),
                "ret_6mo": round(return_6mo_pct, 2),
                "ret_peak_curr": round(ret_peak_curr_pct, 2),
                "importance_notes": " | ".join(importance_notes), "month_ends": json.dumps(month_end_x_coords),
                "chart_closes": json.dumps(closes),
                "chart_dates": json.dumps(formatted_dates)
            })

        print(f"[{idx}/{len(tickers)}] ✅ Loaded {symbol}: ${last_price:.2f} [{comp_industry}]")
    except Exception as e:
        print(f"Error processing {symbol}: {e}")

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
        month_json = item['month_ends'].replace('"', '&quot;')
        clean_name = item['name'].replace("'", "\\'")
        clean_notes = item['importance_notes'].replace("'", "\\'")
        popup_args = f"'{item['ticker']}', '{clean_name}', '{item['industry']}', '{item['price']}', '{item['pct']}', '{item['vol_ratio']}', '{item['svg_points']}', '{item['ma30_svg_points']}', '{item['p_max']}', '{item['p_mid']}', '{item['p_min']}', '{item['d_start']}', '{item['d_mid']}', '{item['d_end']}', {item['is_pos']}, {item['start_y_pct']}, {item['ret_1m']}, {item['ret_3m']}, {item['ret_6mo']}, {item['ret_peak_curr']}, '{closes_json}', '{dates_json}', '{clean_notes}', '{month_json}'"
        
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
        month_json = item['month_ends'].replace('"', '&quot;')
        clean_name = item['name'].replace("'", "\\'")
        clean_notes = item['importance_notes'].replace("'", "\\'")
        popup_args = f"'{item['ticker']}', '{clean_name}', '{item['industry']}', '{item['price']}', '{item['pct']}', '{item['vol_ratio']}', '{item['svg_points']}', '{item['ma30_svg_points']}', '{item['p_max']}', '{item['p_mid']}', '{item['p_min']}', '{item['d_start']}', '{item['d_mid']}', '{item['d_end']}', {item['is_pos']}, {item['start_y_pct']}, {item['ret_1m']}, {item['ret_3m']}, {item['ret_6mo']}, {item['ret_peak_curr']}, '{closes_json}', '{dates_json}', '{clean_notes}', '{month_json}'"
        
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
        month_json = item['month_ends'].replace('"', '&quot;')
        clean_name = item['name'].replace("'", "\\'")
        clean_notes = item['importance_notes'].replace("'", "\\'")
        popup_args = f"'{item['ticker']}', '{clean_name}', '{item['industry']}', '{item['price']}', '{item['pct']}', '{item['vol_ratio']}', '{item['svg_points']}', '{item['ma30_svg_points']}', '{item['p_max']}', '{item['p_mid']}', '{item['p_min']}', '{item['d_start']}', '{item['d_mid']}', '{item['d_end']}', {item['is_pos']}, {item['start_y_pct']}, {item['ret_1m']}, {item['ret_3m']}, {item['ret_6mo']}, {item['ret_peak_curr']}, '{closes_json}', '{dates_json}', '{clean_notes}', '{month_json}'"
        
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
        month_json = item['month_ends'].replace('"', '&quot;')
        clean_name = item['name'].replace("'", "\\'")
        clean_notes = item['importance_notes'].replace("'", "\\'")
        popup_args = f"'{item['ticker']}', '{clean_name}', '{item['industry']}', '{item['price']}', '{item['pct']}', '{item['vol_ratio']}', '{item['svg_points']}', '{item['ma30_svg_points']}', '{item['p_max']}', '{item['p_mid']}', '{item['p_min']}', '{item['d_start']}', '{item['d_mid']}', '{item['d_end']}', {item['is_pos']}, {item['start_y_pct']}, {item['ret_1m']}, {item['ret_3m']}, {item['ret_6mo']}, {item['ret_peak_curr']}, '{closes_json}', '{dates_json}', '{clean_notes}', '{month_json}'"
        
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

def get_header_bg_color(val, min_val, max_val):
    # Within 5% of peak (>= -5.0% drawdown) -> Bright Green
    if val >= -5.0:
        return "background: rgba(34, 197, 94, 0.85); border: 1px solid rgba(34, 197, 94, 1.0);"
    
    # Handle single-item groups or groups where all stocks are below -5% and identical
    if min_val >= -5.0 or min_val == max_val:
        return "background: rgba(249, 115, 22, 0.85); border: 1px solid rgba(249, 115, 22, 1.0);"

    # Drawdown scale for values below -5.0%
    neg_min = min_val  # Worst drawdown (Dark Red)
    neg_max = min(-5.0, max_val)  # Ceiling (-5.0% threshold)
    
    factor = max(0.0, min(1.0, (val - neg_min) / (neg_max - neg_min)))
    
    # Interpolate from Dark Red (#991b1b -> 153, 27, 27) to Warm Orange (#f97316 -> 249, 115, 22)
    r = int(153 + (249 - 153) * factor)
    g = int(27 + (115 - 27) * factor)
    b = int(27 + (22 - 27) * factor)
    
    return f"background: rgba({r}, {g}, {b},
