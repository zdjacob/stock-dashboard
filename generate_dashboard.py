def build_industry_grouped_grid(items):
    industry_dict = {}
    for item in items:
        ind = item['industry']
        if ind not in industry_dict:
            industry_dict[ind] = []
        industry_dict[ind].append(item)
    
    sections_html = ""
    for ind, stock_items in sorted(industry_dict.items()):
        group_slug = "".join([c for c in ind if c.isalnum()])
        
        group_peak_rets = [s['ret_peak_curr'] for s in stock_items]
        min_ret = min(group_peak_rets)
        max_ret = max(group_peak_rets)

        cards_html = ""
        for item in stock_items:
            closes_json = item['chart_closes'].replace('"', '&quot;')
            dates_json = item['chart_dates'].replace('"', '&quot;')
            
            r1m_class = "badge-pos" if item['ret_1m'] > 0 else ("badge-neg" if item['ret_1m'] < 0 else "badge-neutral")
            r3m_class = "badge-pos" if item['ret_3m'] > 0 else ("badge-neg" if item['ret_3m'] < 0 else "badge-neutral")
            r6m_class = "badge-pos" if item['ret_6mo'] > 0 else ("badge-neg" if item['ret_6mo'] < 0 else "badge-neutral")
            rpeak_class = "badge-pos" if item['ret_peak_curr'] > 0 else ("badge-neg" if item['ret_peak_curr'] < 0 else "badge-neutral")
            
            # Bright Green if within 5% of peak (>= -5.0%), Orange-to-Red gradient if > 5% drawdown
            header_style = get_header_bg_color(item['ret_peak_curr'], min_ret, max_ret)

            month_lines_svg = ""
            try:
                m_list = json.loads(item['month_ends'])
                for mx in m_list:
                    month_lines_svg += f'<line x1="{mx}" y1="0" x2="{mx}" y2="110" stroke="rgba(255,255,255,0.18)" stroke-dasharray="2,3"/>'
            except Exception:
                pass

            cards_html += f"""
            <div class="bottom-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px; font-family:monospace; font-size:0.75rem; {header_style} padding:3px 6px; border-radius:4px;">
                    <span style="color:#ffffff; font-weight:bold; text-shadow:0px 1px 2px rgba(0,0,0,0.8);">${item['ticker']}</span>
                    <span class="card-hover-display" style="color:#f8fafc; font-weight:bold; font-size:0.65rem; text-shadow:0px 1px 2px rgba(0,0,0,0.8);">Hover chart</span>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:3px;">
                    <span style="font-size:0.65rem; color:var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="{item['name']}">{item['name']}</span>
                    <div style="display:flex; gap:2px; flex-wrap:nowrap;">
                        <span class="return-badge {r1m_class}" style="font-size:0.55rem; padding:1px 3px;" title="1 Month Return">{item['ret_1m']:+.1f}% 1M</span>
                        <span class="return-badge {r3m_class}" style="font-size:0.55rem; padding:1px 3px;" title="3 Month Return">{item['ret_3m']:+.1f}% 3M</span>
                        <span class="return-badge {r6m_class}" style="font-size:0.55rem; padding:1px 3px;" title="6 Month Return">{item['ret_6mo']:+.1f}% 6M</span>
                        <span class="return-badge {rpeak_class}" style="font-size:0.55rem; padding:1px 3px;" title="6M Highest Price to Current Return">{item['ret_peak_curr']:+.1f}% Peak</span>
                    </div>
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; font-family:monospace; font-size:0.7rem; margin-bottom:3px;">
                    <span>Price: <strong>${item['price']:,.2f}</strong></span>
                    <span style="color:var(--accent-yellow);">52W Pos: <strong>{item['pct']}%</strong></span>
                </div>
                <div class="inline-chart-wrap" style="position:relative; width:100%; height:110px; background:var(--bg-dark); border-radius:4px; border:1px solid var(--border-color); overflow:hidden;">
                    <svg class="inline-svg sync-group-{group_slug}" data-closes="{closes_json}" data-dates="{dates_json}" data-min="{item['p_min']}" data-max="{item['p_max']}" viewBox="0 0 320 110" width="100%" height="100%" preserveAspectRatio="none" style="display:block; cursor: crosshair; touch-action: none;">
                        <line x1="0" y1="27.5" x2="320" y2="27.5" stroke="rgba(255,255,255,0.12)" stroke-dasharray="2,2"/>
                        <line x1="0" y1="55.0" x2="320" y2="55.0" stroke="rgba(255,255,255,0.18)" stroke-dasharray="2,2"/>
                        <line x1="0" y1="82.5" x2="320" y2="82.5" stroke="rgba(255,255,255,0.12)" stroke-dasharray="2,2"/>
                        {month_lines_svg}
                        <polyline fill="none" stroke="rgba(250, 204, 21, 0.65)" stroke-width="1.5" stroke-dasharray="3,2" points="{item['ma30_svg_points']}"/>
                        <polyline fill="none" stroke="{'#22c55e' if item['is_pos'] == 'true' else '#ef4444'}" stroke-width="2" points="{item['svg_points']}"/>
                        <line class="inline-line-x" x1="0" y1="0" x2="0" y2="110" stroke="var(--accent-cyan)" stroke-width="1" stroke-dasharray="1,1" style="display: none;"/>
                        <line class="inline-line-y" x1="0" y1="0" x2="320" y2="0" stroke="var(--accent-cyan)" stroke-width="1" stroke-dasharray="1,1" style="display: none;"/>
                        <circle class="inline-dot" cx="0" cy="0" r="3.5" fill="var(--accent-cyan)" stroke="#fff" stroke-width="1" style="display: none;"/>
                    </svg>
                </div>
                <div style="font-size:0.6rem; color:var(--text-muted); margin-top:3px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" title="{item['importance_notes']}">
                    {item['importance_notes']}
                </div>
            </div>
            """
        
        sections_html += f"""
        <div style="margin-bottom: 14px;">
            <div style="font-size: 0.9rem; color: var(--accent-cyan); font-weight: bold; margin-bottom: 6px; border-bottom: 1px solid var(--border-color); padding-bottom: 3px;">🏭 {ind} (Synchronized Group)</div>
            <div class="four-column-grid">{cards_html}</div>
        </div>
        """
    return sections_html
