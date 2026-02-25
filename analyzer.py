"""
FlySafair Price Analyzer
Reads the flights.db database and generates interactive HTML reports showing:
1. Optimal booking window (1-28+ days before flight)
2. Best day of week to fly
3. Best hour of day to book
4. Best day of week to book
5. Price trends per route
6. Price heatmap
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from db_manager import get_all_data
from datetime import datetime
import os

REPORT_FILES = [
    "report_booking_window.html",
    "report_day_fly.html",
    "report_hour_book.html",
    "report_day_book.html",
    "report_routes.html",
    "report_heatmap.html",
    "report_booking_by_route.html",
    "report_price_shifts.html",
]


def ensure_placeholder_reports(output_dir):
    """Create placeholder HTML for any reports that don't exist yet."""
    placeholder = """<!DOCTYPE html><html><head><style>
        body { background: #1a1a2e; color: #888; font-family: Inter, sans-serif;
               display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .msg { text-align: center; }
        .msg h3 { color: #4fc3f7; margin-bottom: 0.5rem; }
    </style></head><body><div class="msg">
        <h3>&#9203; Collecting Data...</h3>
        <p>This chart will appear after more scrape cycles run.</p>
    </div></body></html>"""
    for fname in REPORT_FILES:
        path = os.path.join(output_dir, fname)
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                f.write(placeholder)


def inject_active_button_script(html_path):
    """Injects JS to override Plotly's default active updatemenu button color to pink."""
    with open(html_path, "a", encoding="utf-8") as f:
        f.write("""
<script>
setInterval(function() {
    document.querySelectorAll('g.updatemenu-button').forEach(function(btn) {
        var rect = btn.querySelector('rect');
        var text = btn.querySelector('text');
        if (rect) {
            var fill = rect.style.fill || rect.getAttribute('fill') || '';
            // Inactive is our dark bgcolor rgb(36, 36, 62), active is light assigned by Plotly
            if (fill && fill.includes('rgb(36, 36, 62)')) {
                // Do nothing, it is inactive
            } else {
                // Must be the active button, make it pink
                rect.style.fill = '#e91e8c';
                rect.setAttribute('fill', '#e91e8c');
                if (text) {
                    text.style.fill = '#ffffff';
                    text.setAttribute('fill', '#ffffff');
                }
            }
        }
    });
}, 50);
</script>
""")


def run_analysis():
    output_dir = os.path.dirname(os.path.abspath(__file__))
    ensure_placeholder_reports(output_dir)

    df = get_all_data()

    if df.empty:
        print("No data available in the database yet. Run the scraper first.")
        return

    # Convert columns
    df['flight_date'] = pd.to_datetime(df['flight_date'], errors='coerce')
    df['scrape_datetime'] = pd.to_datetime(df['scrape_datetime'], errors='coerce')
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df = df.dropna(subset=['flight_date', 'price'])

    # Derived columns
    df['day_of_week_fly'] = df['flight_date'].dt.day_name()
    df['day_of_week_fly_num'] = df['flight_date'].dt.dayofweek
    df['day_of_week_book'] = df['scrape_datetime'].dt.day_name()
    df['day_of_week_book_num'] = df['scrape_datetime'].dt.dayofweek
    df['hour_of_day_book'] = df['scrape_datetime'].dt.hour
    df['weeks_ahead'] = df['days_before_flight'] // 7

    output_dir = os.path.dirname(os.path.abspath(__file__))

    # ===== REPORT 1: Booking Window (Days Before Flight) =====
    print("\n" + "=" * 50)
    print("ANALYSIS: Optimal Booking Window")
    print("=" * 50)

    avg_by_days = df.groupby('days_before_flight')['price'].agg(['mean', 'min', 'count']).reset_index()
    avg_by_days.columns = ['days_before', 'avg_price', 'min_price', 'count']
    avg_by_days = avg_by_days.sort_values('days_before')

    if not avg_by_days.empty:
        best = avg_by_days.loc[avg_by_days['avg_price'].idxmin()]
        print(f"  -> Cheapest avg: {int(best['days_before'])} days before flight (R{best['avg_price']:.2f})")

        routes = ['All Routes'] + sorted(df['route'].unique().tolist())
        traces = []
        for i, route in enumerate(routes):
            route_df = df if route == 'All Routes' else df[df['route'] == route]
            route_avg = route_df.groupby('days_before_flight')['price'].agg(['mean', 'min', 'count']).reset_index()
            route_avg.columns = ['days_before', 'avg_price', 'min_price', 'count']
            route_avg = route_avg.sort_values('days_before')
            
            trace = go.Bar(
                x=route_avg['days_before'],
                y=route_avg['avg_price'],
                name=route,
                marker_color=route_avg['avg_price'].apply(
                    lambda p: '#4caf50' if p <= route_avg['avg_price'].quantile(0.25) else
                              '#ff9800' if p <= route_avg['avg_price'].quantile(0.75) else '#f44336'
                ).tolist(),
                visible=(i == 0)
            )
            traces.append(trace)
            
        fig1 = go.Figure(data=traces)
        buttons = []
        for i, route in enumerate(routes):
            visibility = [False] * len(routes)
            visibility[i] = True
            buttons.append(
                dict(label=route, method="update", args=[{"visible": visibility}, {"title_text": f"Average Price by Days Before Flight: {route}"}])
            )

        fig1.update_layout(
            title='Average Price by Days Before Flight: All Routes',
            xaxis_title='Days Before Flight',
            yaxis_title='Average Price (ZAR)',
            xaxis=dict(dtick=1),
            template="plotly_dark",
            font=dict(family="Inter, sans-serif"),
            updatemenus=[dict(
                type="buttons", direction="right", active=0, x=0.5, y=1.15, 
                xanchor="center", yanchor="top", buttons=buttons, 
                bgcolor="#24243e", bordercolor="#4fc3f7", font=dict(color="#e0e0e0", size=13)
            )]
        )
        html_path = os.path.join(output_dir, "report_booking_window.html")
        fig1.write_html(html_path)
        inject_active_button_script(html_path)
        print("  Saved -> report_booking_window.html")

    # ===== REPORT 2: Day of Week to FLY =====
    print("\n" + "=" * 50)
    print("ANALYSIS: Cheapest Day of Week to FLY")
    print("=" * 50)

    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    avg_fly = df.groupby(['day_of_week_fly', 'day_of_week_fly_num'])['price'].mean().reset_index()
    avg_fly = avg_fly.sort_values('day_of_week_fly_num')

    if not avg_fly.empty:
        best_fly = avg_fly.loc[avg_fly['price'].idxmin()]
        print(f"  -> Cheapest day to fly: {best_fly['day_of_week_fly']} (R{best_fly['price']:.2f})")

        routes = ['All Routes'] + sorted(df['route'].unique().tolist())
        traces = []
        for i, route in enumerate(routes):
            route_df = df if route == 'All Routes' else df[df['route'] == route]
            route_avg = route_df.groupby(['day_of_week_fly', 'day_of_week_fly_num'])['price'].mean().reset_index()
            route_avg = route_avg.sort_values('day_of_week_fly_num')
            
            trace = go.Bar(
                x=route_avg['day_of_week_fly'],
                y=route_avg['price'],
                name=route,
                marker=dict(
                    color=route_avg['price'], 
                    colorscale='RdYlGn_r', 
                    colorbar=dict(title='Avg Price (ZAR)') if i == 0 else None
                ),
                visible=(i == 0)
            )
            traces.append(trace)
            
        fig2 = go.Figure(data=traces)
        buttons = []
        for i, route in enumerate(routes):
            visibility = [False] * len(routes)
            visibility[i] = True
            buttons.append(
                dict(label=route, method="update", args=[{"visible": visibility}, {"title_text": f"Average Price by Day of Week (Flying): {route}"}])
            )

        fig2.update_layout(
            title='Average Price by Day of Week (Flying): All Routes',
            xaxis_title='Day of Week',
            yaxis_title='Avg Price (ZAR)',
            template="plotly_dark",
            font=dict(family="Inter, sans-serif"),
            updatemenus=[dict(
                type="buttons", direction="right", active=0, x=0.5, y=1.15, 
                xanchor="center", yanchor="top", buttons=buttons, 
                bgcolor="#24243e", bordercolor="#4fc3f7", font=dict(color="#e0e0e0", size=13)
            )]
        )
        html_path = os.path.join(output_dir, "report_day_fly.html")
        fig2.write_html(html_path)
        inject_active_button_script(html_path)
        print("  Saved -> report_day_fly.html")

    # ===== REPORT 3: Hour of Day to BOOK =====
    print("\n" + "=" * 50)
    print("ANALYSIS: Cheapest Hour of Day to BOOK")
    print("=" * 50)

    avg_hour = df.groupby('hour_of_day_book')['price'].mean().reset_index()
    avg_hour = avg_hour.sort_values('hour_of_day_book')

    if not avg_hour.empty and len(avg_hour) > 1:
        best_hour = avg_hour.loc[avg_hour['price'].idxmin()]
        print(f"  -> Cheapest hour to book: {int(best_hour['hour_of_day_book']):02d}:00 (R{best_hour['price']:.2f})")

        routes = ['All Routes'] + sorted(df['route'].unique().tolist())
        traces = []
        for i, route in enumerate(routes):
            route_df = df if route == 'All Routes' else df[df['route'] == route]
            route_avg = route_df.groupby('hour_of_day_book')['price'].mean().reset_index()
            route_avg = route_avg.sort_values('hour_of_day_book')
            
            trace = go.Bar(
                x=route_avg['hour_of_day_book'],
                y=route_avg['price'],
                name=route,
                marker=dict(
                    color=route_avg['price'], 
                    colorscale='RdYlGn_r', 
                    colorbar=dict(title='Avg Price (ZAR)') if i == 0 else None
                ),
                visible=(i == 0)
            )
            traces.append(trace)
            
        fig3 = go.Figure(data=traces)
        buttons = []
        for i, route in enumerate(routes):
            visibility = [False] * len(routes)
            visibility[i] = True
            buttons.append(
                dict(label=route, method="update", args=[{"visible": visibility}, {"title_text": f"Average Price by Hour of Day (When You Check): {route}"}])
            )

        fig3.update_layout(
            title='Average Price by Hour of Day (When You Check): All Routes',
            xaxis_title='Hour of Day',
            yaxis_title='Avg Price (ZAR)',
            template="plotly_dark",
            font=dict(family="Inter, sans-serif"),
            xaxis=dict(dtick=1),
            updatemenus=[dict(
                type="buttons", direction="right", active=0, x=0.5, y=1.15, 
                xanchor="center", yanchor="top", buttons=buttons, 
                bgcolor="#24243e", bordercolor="#4fc3f7", font=dict(color="#e0e0e0", size=13)
            )]
        )
        html_path = os.path.join(output_dir, "report_hour_book.html")
        fig3.write_html(html_path)
        inject_active_button_script(html_path)
        print("  Saved -> report_hour_book.html")
    else:
        print("  -> Need more hourly data (keep running scraper!)")

    # ===== REPORT 4: Day of Week to BOOK =====
    print("\n" + "=" * 50)
    print("ANALYSIS: Cheapest Day of Week to BOOK")
    print("=" * 50)

    avg_book = df.groupby(['day_of_week_book', 'day_of_week_book_num'])['price'].mean().reset_index()
    avg_book = avg_book.sort_values('day_of_week_book_num')

    if not avg_book.empty and len(avg_book) > 1:
        best_book = avg_book.loc[avg_book['price'].idxmin()]
        print(f"  -> Cheapest day to book: {best_book['day_of_week_book']} (R{best_book['price']:.2f})")

        routes = ['All Routes'] + sorted(df['route'].unique().tolist())
        traces = []
        for i, route in enumerate(routes):
            route_df = df if route == 'All Routes' else df[df['route'] == route]
            route_avg = route_df.groupby(['day_of_week_book', 'day_of_week_book_num'])['price'].mean().reset_index()
            route_avg = route_avg.sort_values('day_of_week_book_num')
            
            trace = go.Bar(
                x=route_avg['day_of_week_book'],
                y=route_avg['price'],
                name=route,
                marker=dict(
                    color=route_avg['price'], 
                    colorscale='RdYlGn_r', 
                    colorbar=dict(title='Avg Price (ZAR)') if i == 0 else None
                ),
                visible=(i == 0)
            )
            traces.append(trace)
            
        fig4 = go.Figure(data=traces)
        buttons = []
        for i, route in enumerate(routes):
            visibility = [False] * len(routes)
            visibility[i] = True
            buttons.append(
                dict(label=route, method="update", args=[{"visible": visibility}, {"title_text": f"Average Price by Day of Week (When You Book): {route}"}])
            )

        fig4.update_layout(
            title='Average Price by Day of Week (When You Book): All Routes',
            xaxis_title='Day of Week',
            yaxis_title='Avg Price (ZAR)',
            template="plotly_dark",
            font=dict(family="Inter, sans-serif"),
            updatemenus=[dict(
                type="buttons", direction="right", active=0, x=0.5, y=1.15, 
                xanchor="center", yanchor="top", buttons=buttons, 
                bgcolor="#24243e", bordercolor="#4fc3f7", font=dict(color="#e0e0e0", size=13)
            )]
        )
        html_path = os.path.join(output_dir, "report_day_book.html")
        fig4.write_html(html_path)
        inject_active_button_script(html_path)
        print("  Saved -> report_day_book.html")
    else:
        print("  -> Need more daily data (keep running scraper!)")

    # ===== REPORT 5: Price by Route =====
    print("\n" + "=" * 50)
    print("ANALYSIS: Price by Route")
    print("=" * 50)

    route_stats = df.groupby('route')['price'].agg(['mean', 'min', 'max', 'count']).reset_index()
    route_stats.columns = ['Route', 'Average Price', 'Min Price', 'Max Price', 'Data Points']
    print(route_stats.to_string(index=False))

    fig5 = px.box(df, x='route', y='price',
                  title='Price Distribution by Route',
                  labels={'route': 'Route', 'price': 'Price (ZAR)'},
                  color='route')
    fig5.update_layout(template="plotly_dark", font=dict(family="Inter, sans-serif"))
    fig5.write_html(os.path.join(output_dir, "report_routes.html"))
    print("  Saved -> report_routes.html")

    # ===== REPORT 6: Heatmap (Day of Week vs Booking Period) =====
    print("\n" + "=" * 50)
    print("ANALYSIS: Price Heatmap")
    print("=" * 50)

    # Group days_before_flight into meaningful booking periods
    period_bins = [
        (0, 7, "This week"),
        (8, 14, "1-2 weeks"),
        (15, 21, "2-3 weeks"),
        (22, 30, "3-4 weeks"),
        (31, 60, "1-2 months"),
        (61, 90, "2-3 months"),
        (91, 120, "3-4 months"),
        (121, 999, "4+ months"),
    ]

    def get_period(days):
        for lo, hi, label in period_bins:
            if lo <= days <= hi:
                return label
        return "4+ months"

    period_order = [p[2] for p in period_bins]
    df['booking_period'] = df['days_before_flight'].apply(get_period)
    df['booking_period'] = pd.Categorical(df['booking_period'], categories=period_order, ordered=True)

    # Prepare datasets for 'All Routes' and each individual route
    routes = ['All Routes'] + sorted(df['route'].unique().tolist())
    traces = []
    
    for i, route in enumerate(routes):
        if route == 'All Routes':
            route_df = df
        else:
            route_df = df[df['route'] == route]
            
        heatmap_data = route_df.groupby(['day_of_week_fly', 'day_of_week_fly_num', 'booking_period'])['price'].mean().reset_index()
        heatmap_data = heatmap_data.sort_values('day_of_week_fly_num')
        
        heatmap_pivot = heatmap_data.pivot(index='day_of_week_fly', columns='booking_period', values='price')
        
        # Ensure all columns exist even if no data, to keep the grid aligned
        for col in period_order:
            if col not in heatmap_pivot.columns:
                heatmap_pivot[col] = pd.NA
                
        # Reorder rows by day of week
        heatmap_pivot = heatmap_pivot.reindex(day_order)
        # Reorder columns
        heatmap_pivot = heatmap_pivot.reindex(columns=period_order)
        
        z_values = heatmap_pivot.values
        text_values = [[f'R{v:,.0f}' if pd.notna(v) else '' for v in row] for row in z_values]
        
        trace = go.Heatmap(
            z=z_values,
            x=period_order,
            y=day_order,
            colorscale='RdYlGn_r',
            text=text_values,
            texttemplate='%{text}',
            textfont=dict(size=11, color='white'),
            hovertemplate='Day: %{y}<br>Window: %{x}<br>Avg Price: R%{z:,.0f}<extra></extra>',
            colorbar=dict(title='Avg Price (ZAR)'),
            name=route,
            visible=(i == 0) # Only the first trace (All Routes) is visible by default
        )
        traces.append(trace)

    if len(traces) > 0:
        fig6 = go.Figure(data=traces)
        
        # Create buttons for the dropdown/filter
        buttons = []
        for i, route in enumerate(routes):
            # Create a boolean list where only the i-th trace is True
            visibility = [False] * len(routes)
            visibility[i] = True
            
            buttons.append(
                dict(
                    label=route,
                    method="update",
                    args=[{"visible": visibility},
                          {"title_text": f"When to Fly & How Far in Advance to Book: {route}"}]
                )
            )
            
        fig6.update_layout(
            title='When to Fly & How Far in Advance to Book: All Routes',
            xaxis_title='How Far in Advance You Book',
            yaxis_title='Day of Week You Fly',
            template="plotly_dark",
            font=dict(family="Inter, sans-serif"),
            yaxis=dict(autorange='reversed'),
            updatemenus=[
                dict(
                    type="buttons",
                    direction="right",
                    active=0,
                    x=0.5,
                    y=1.15,
                    xanchor="center",
                    yanchor="top",
                    buttons=buttons,
                    bgcolor="#24243e",
                    bordercolor="#4fc3f7",
                    font=dict(color="#e0e0e0", size=13)
                )
            ]
        )
        html_path = os.path.join(output_dir, "report_heatmap.html")
        fig6.write_html(html_path)
        
        # Inject custom JS to force the active button to be pink
        with open(html_path, "a", encoding="utf-8") as f:
            f.write("""
<script>
setInterval(function() {
    document.querySelectorAll('g.updatemenu-button').forEach(function(btn) {
        var rect = btn.querySelector('rect');
        var text = btn.querySelector('text');
        if (rect) {
            var fill = rect.style.fill || rect.getAttribute('fill') || '';
            // Inactive is our dark bgcolor rgb(36, 36, 62), active is light assigned by Plotly
            if (fill && fill.includes('rgb(36, 36, 62)')) {
                // Do nothing, it is inactive
            } else {
                // Must be the active button, make it pink
                rect.style.fill = '#e91e8c';
                rect.setAttribute('fill', '#e91e8c');
                if (text) {
                    text.style.fill = '#ffffff';
                    text.setAttribute('fill', '#ffffff');
                }
            }
        }
    });
}, 50);
</script>
""")
        print("  Saved -> report_heatmap.html")

    # ===== REPORT 7: Booking Window by Route =====
    print("\n" + "=" * 50)
    print("ANALYSIS: Booking Window per Route")
    print("=" * 50)

    fig7 = px.line(df.groupby(['route', 'days_before_flight'])['price'].mean().reset_index(),
                   x='days_before_flight', y='price', color='route',
                   title='Average Price vs Days Before Flight (by Route)',
                   labels={'days_before_flight': 'Days Before Flight', 'price': 'Avg Price (ZAR)'})
    fig7.update_layout(template="plotly_dark", font=dict(family="Inter, sans-serif"))
    fig7.write_html(os.path.join(output_dir, "report_booking_by_route.html"))
    print("  Saved -> report_booking_by_route.html")

    # ===== MASTER DASHBOARD =====
    analyze_price_shifts(output_dir)
    generate_dashboard(df, route_stats, output_dir)

def analyze_price_shifts(output_dir):
    """
    Identifies flights that have shifted in price since they first appeared in the database.
    Calculates when the shift started occurring and generates a report.
    """
    from db_manager import get_flight_details_data
    df = get_flight_details_data()
    
    if df.empty:
        return
        
    df['flight_date'] = pd.to_datetime(df['flight_date'], errors='coerce')
    df['scrape_datetime'] = pd.to_datetime(df['scrape_datetime'], errors='coerce')
    df['price'] = pd.to_numeric(df['price'], errors='coerce')
    df = df.dropna(subset=['flight_date', 'price', 'flight_number'])
    
    # Sort chronologically so we can track the earliest price vs latest prices
    df = df.sort_values(by=['route', 'flight_date', 'flight_number', 'scrape_datetime'])
    
    results = []
    
    # Group by specific flight (route + date + flight number)
    for name, group in df.groupby(['route', 'flight_date', 'flight_number']):
        prices = group['price'].values
        if len(prices) <= 1:
            continue
            
        initial_price = prices[0]
        # Find the first row where the price deviated from the initial price
        shifted_rows = group[group['price'] != initial_price]
        
        if not shifted_rows.empty:
            first_shift_row = shifted_rows.iloc[0]
            latest_row = group.iloc[-1]
            
            latest_price = latest_row['price']
            price_diff = latest_price - initial_price
            
            if price_diff != 0:
                results.append({
                    'route': name[0],
                    'flight_date': name[1],
                    'flight_number': name[2],
                    'departure_time': group['departure_time'].iloc[0],
                    'initial_price': initial_price,
                    'latest_price': latest_price,
                    'price_diff': price_diff,
                    'days_before_shift': first_shift_row['days_before_flight'],
                    'shift_direction': 'Up' if price_diff > 0 else 'Down'
                })
                
    if not results:
        print("  -> No price shifts detected across individual flights.")
        return
        
    shifts_df = pd.DataFrame(results)
    
    print("\n" + "=" * 50)
    print("ANALYSIS: Price Shifts & Trends")
    print("=" * 50)
    
    # --- Generate Report 8: Price Shifts ---
    shifts_df['Shift Amount'] = shifts_df['price_diff'].apply(lambda x: f"R{x:+.0f}")
    shifts_df['Flight'] = shifts_df['flight_date'].dt.strftime('%Y-%m-%d') + " " + shifts_df['flight_number']
    
    # Filter out minor shifts (e.g. less than R50) to focus on signal vs noise
    significant_shifts = shifts_df[shifts_df['price_diff'].abs() >= 50].copy()
    
    if significant_shifts.empty:
        significant_shifts = shifts_df # Fallback if no big shifts
        
    # Scatter plot: Days Before Flight vs Price Diff
    fig8 = px.scatter(
        significant_shifts, 
        x='days_before_shift', 
        y='price_diff',
        color='route',
        size=significant_shifts['price_diff'].abs(),
        hover_name='Flight',
        hover_data={'days_before_shift': True, 'initial_price': True, 'latest_price': True, 'price_diff': True, 'route': False},
        labels={
            'days_before_shift': 'Days Before Flight When Shift Started',
            'price_diff': 'Price Change (ZAR)'
        },
        title='When Do Flights Change Price?'
    )
    
    # Add a horizontal line at 0
    fig8.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="No Change")
    
    fig8.update_layout(
        template="plotly_dark", 
        font=dict(family="Inter, sans-serif"),
        xaxis=dict(autorange='reversed') # Reverse X axis so closer to flight is on the right
    )
    
    fig8.write_html(os.path.join(output_dir, "report_price_shifts.html"))
    print("  Saved -> report_price_shifts.html")
    
    # --- Print Aggregate Trends ---
    trend_summary = shifts_df.groupby(['route', 'shift_direction']).agg({
        'price_diff': ['count', 'mean'],
        'days_before_shift': 'median' # Median is better to avoid extreme outliers
    }).round(1)
    
    print("Average Price Shift Trends:")
    print(trend_summary)
    
    # Export summary to a JSON file so the dashboard can read it easily
    import json
    trend_dict = {}
    for route in shifts_df['route'].unique():
        route_df = shifts_df[shifts_df['route'] == route]
        up_df = route_df[route_df['shift_direction'] == 'Up']
        down_df = route_df[route_df['shift_direction'] == 'Down']
        
        trend_dict[route] = {
            'total_shifts': len(route_df),
            'up_count': len(up_df),
            'down_count': len(down_df),
            'avg_days_before_up': float(up_df['days_before_shift'].median()) if not up_df.empty else None,
            'avg_days_before_down': float(down_df['days_before_shift'].median()) if not down_df.empty else None,
        }
        
    with open(os.path.join(output_dir, "price_trends.json"), "w") as f:
        json.dump(trend_dict, f)

    # Export full shifts details for route detail modal
    detail_dict = {}
    for route in shifts_df['route'].unique():
        route_df = shifts_df[shifts_df['route'] == route].sort_values(by=['days_before_shift'], ascending=False)
        detail_dict[route] = []
        for _, row in route_df.iterrows():
            detail_dict[route].append({
                "flight": row['Flight'],
                "flight_date": row['flight_date'].strftime('%Y-%m-%d'),
                "flight_number": row['flight_number'],
                "initial_price": float(row['initial_price']),
                "latest_price": float(row['latest_price']),
                "price_diff": float(row['price_diff']),
                "days_before": int(row['days_before_shift']),
                "direction": row['shift_direction']
            })

    with open(os.path.join(output_dir, "shifts_data_full.json"), "w") as f:
        json.dump(detail_dict, f)
        
    # Export summary by flight number
    flight_summary = {}
    for route in shifts_df['route'].unique():
        route_df = shifts_df[shifts_df['route'] == route]
        flight_summary[route] = []
        
        # Group by flight number
        for fnum, fgroup in route_df.groupby('flight_number'):
            up_group = fgroup[fgroup['shift_direction'] == 'Up']
            down_group = fgroup[fgroup['shift_direction'] == 'Down']
            
            summary = {
                "flight_number": fnum,
                "departure_time": fgroup['departure_time'].iloc[0] if not fgroup['departure_time'].empty else "Unknown",
                "total_shifts": len(fgroup),
                "up_count": len(up_group),
                "down_count": len(down_group),
                "avg_price_diff": float(fgroup['price_diff'].mean()),
                "avg_days_before": float(fgroup['days_before_shift'].mean())
            }
            flight_summary[route].append(summary)

    with open(os.path.join(output_dir, "flight_summary.json"), "w") as f:
        json.dump(flight_summary, f)

def generate_dashboard(df, route_stats, output_dir):
    """Generate a single-page HTML dashboard with all insights."""
    avg_price = df['price'].mean()
    min_price = df['price'].min()
    max_price = df['price'].max()
    total_records = len(df)
    routes_tracked = df['route'].nunique()
    total_checks = df['scrape_datetime'].nunique()

    # Best booking window
    avg_by_days = df.groupby('days_before_flight')['price'].mean()
    best_days_ahead = int(avg_by_days.idxmin()) if not avg_by_days.empty else "N/A"

    # Best day to fly
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    avg_by_dow = df.groupby(df['flight_date'].dt.dayofweek)['price'].mean()
    best_dow_fly = day_order[avg_by_dow.idxmin()] if not avg_by_dow.empty else "N/A"

    # Best hour to book
    avg_by_hour = df.groupby(df['scrape_datetime'].dt.hour)['price'].mean()
    best_hour = f"{int(avg_by_hour.idxmin()):02d}:00" if not avg_by_hour.empty and len(avg_by_hour) > 1 else "Need more data"

    # Best day to book
    avg_by_dow_book = df.groupby(df['scrape_datetime'].dt.dayofweek)['price'].mean()
    best_dow_book = day_order[avg_by_dow_book.idxmin()] if not avg_by_dow_book.empty and len(avg_by_dow_book) > 1 else "Need more data"

    # Price change vs previous check
    scrape_times = sorted(df['scrape_datetime'].unique())
    price_changes = {}
    if len(scrape_times) >= 2:
        latest = scrape_times[-1]
        previous = scrape_times[-2]
        latest_df = df[df['scrape_datetime'] == latest].groupby('route')['price'].mean()
        prev_df = df[df['scrape_datetime'] == previous].groupby('route')['price'].mean()
        for route in latest_df.index:
            if route in prev_df.index:
                price_changes[route] = latest_df[route] - prev_df[route]

    # Booking window summary table data
    booking_bins = [
        (1, 1, "1 day before"),
        (2, 2, "2 days before"),
        (3, 3, "3 days before"),
        (4, 4, "4 days before"),
        (5, 5, "5 days before"),
        (6, 6, "6 days before"),
        (7, 7, "1 week before"),
        (8, 10, "8-10 days"),
        (11, 14, "11-14 days (2 wks)"),
        (15, 21, "15-21 days (3 wks)"),
        (22, 28, "22-28 days (4 wks)"),
        (29, 45, "1-1.5 months"),
        (46, 60, "1.5-2 months"),
        (61, 90, "2-3 months"),
        (91, 120, "3-4 months"),
        (121, 150, "4-5 months"),
        (151, 180, "5-6 months"),
        (181, 999, "6+ months"),
    ]
    
    routes = ['All Routes'] + sorted(df['route'].unique().tolist())
    
    # Generate Tabs
    tabs_html = '<div class="route-tabs">'
    for i, r in enumerate(routes):
        r_id = r.replace(" ", "").replace("-", "")
        active_cls = ' active' if i == 0 else ''
        tabs_html += f'<button class="route-tab{active_cls}" onclick="switchTab(\'{r_id}\', this)">{r}</button>'
    tabs_html += '</div>'

    # Generate Tab Contents
    tables_html = ""
    for i, r in enumerate(routes):
        r_id = r.replace(" ", "").replace("-", "")
        display = 'block' if i == 0 else 'none'
        tables_html += f'<div id="content-{r_id}" class="tab-content" style="display:{display};">'
        tables_html += """
        <div style="width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch;">
        <table class="data-table">
            <thead>
                <tr>
                    <th>Window</th>
                    <th>Avg Price</th>
                    <th>Min</th>
                    <th>Samples</th>
                    <th>Price Level</th>
                </tr>
            </thead>
            <tbody>
        """
        
        route_df = df if r == 'All Routes' else df[df['route'] == r]
        best_bin_price = float('inf')
        
        for lo, hi, label in booking_bins:
            subset = route_df[(route_df['days_before_flight'] >= lo) & (route_df['days_before_flight'] <= hi)]
            if len(subset) > 0:
                avg_p = subset['price'].mean()
                min_p = subset['price'].min()
                cnt = len(subset)
                if avg_p < best_bin_price:
                    best_bin_price = avg_p
                bar_width = min(100, (avg_p / df['price'].max()) * 100) # Keep scale relative to global max
                color = '#4caf50' if avg_p <= df['price'].quantile(0.25) else '#ff9800' if avg_p <= df['price'].quantile(0.75) else '#f44336'
                tables_html += f"""<tr>
                    <td>{label}</td>
                    <td>R{avg_p:,.0f}</td>
                    <td style="color: #4caf50;">R{min_p:,.0f}</td>
                    <td>{cnt}</td>
                    <td><div style="background:{color}; height:16px; border-radius:4px; width:{bar_width}%;"></div></td>
                </tr>\n"""
            else:
                tables_html += f"""<tr><td>{label}</td><td colspan="4" style="color:#666;">No data yet</td></tr>\n"""
                
        tables_html += "</tbody></table></div></div>"

    booking_section_html = f"""
    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 2rem; flex-wrap: wrap; gap: 1rem;">
        <h2 class="section-title" style="margin: 0; border: none; padding: 0;">Booking Window Breakdown</h2>
        {tabs_html}
    </div>
    <div style="border-top: 1px solid rgba(255,255,255,0.1); margin-top: 1rem; padding-top: 1rem;">
        {tables_html}
    </div>
    <script>
    function switchTab(routeId, btn) {{
        // Hide all contents
        document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
        // Remove active class from all buttons
        document.querySelectorAll('.route-tab').forEach(el => el.classList.remove('active'));
        // Show target content
        document.getElementById('content-' + routeId).style.display = 'block';
        // Set button to active
        btn.classList.add('active');
    }}
    </script>
    """

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    now_iso = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    now_time = datetime.now().strftime('%H:%M:%S')

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FlySafair Price Tracker - Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
    <script>
        const SUPABASE_URL = "https://opiscawovakabjpmzwte.supabase.co";
        const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im9waXNjYXdvdmFrYWJqcG16d3RlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzIwMTIyNTEsImV4cCI6MjA4NzU4ODI1MX0.yEZ1A5WR0SIA24YuyBjFB6SlRPdq9FE2IzfWqj5cCGU";
        window.supabaseClient = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    </script>
    <style>
        .route-tabs {{
            display: inline-flex;
            border: 1px solid #4fc3f7;
            border-radius: 4px;
            overflow: hidden;
            margin-left: max(1rem, auto);
        }}
        .route-tab {{
            background: #24243e;
            color: #e0e0e0;
            border: none;
            padding: 8px 16px;
            font-size: 13px;
            font-family: inherit;
            cursor: pointer;
            border-right: 1px solid #4fc3f7;
            transition: all 0.2s ease;
        }}
        .route-tab:last-child {{
            border-right: none;
        }}
        .route-tab:hover {{
            background: rgba(79, 195, 247, 0.2);
        }}
        .route-tab.active {{
            background: #e91e8c;
            color: #ffffff;
            border-color: #e91e8c;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            color: #e0e0e0;
            min-height: 100vh;
            padding: 2rem;
            max-width: 100%;
            overflow-x: hidden;
        }}
        .header {{ text-align: center; margin-bottom: 1.5rem; }}
        .header h1 {{
            font-size: 2.5rem;
            background: linear-gradient(90deg, #e91e8c, #4fc3f7);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}
        .header p {{ color: #aaa; font-size: 0.9rem; }}
        .timer-bar {{
            display: flex;
            justify-content: center;
            gap: 2.5rem;
            margin: 1.5rem auto;
            padding: 1rem 2rem;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            backdrop-filter: blur(10px);
            max-width: 900px;
            flex-wrap: wrap;
        }}
        .timer-item {{ text-align: center; }}
        .timer-item .timer-value {{
            font-size: 1.3rem; font-weight: 600; color: #4fc3f7;
            font-variant-numeric: tabular-nums;
        }}
        .timer-item .timer-label {{
            font-size: 0.7rem; text-transform: uppercase;
            letter-spacing: 1px; color: #888; margin-top: 0.25rem;
        }}
        .timer-item.countdown .timer-value {{ color: #e91e8c; }}
        .section-title {{
            font-size: 1.2rem; color: #4fc3f7; margin: 2rem 0 1rem;
            padding-bottom: 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        .metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
            gap: 1rem; margin-bottom: 1.5rem;
        }}
        .metric-card {{
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px; padding: 1.2rem;
            backdrop-filter: blur(10px); text-align: center;
            transition: transform 0.2s;
        }}
        .metric-card:hover {{ transform: translateY(-4px); }}
        .metric-card .value {{ font-size: 1.6rem; font-weight: 700; color: #4fc3f7; }}
        .metric-card .label {{
            font-size: 0.7rem; text-transform: uppercase;
            letter-spacing: 1px; color: #888; margin-top: 0.4rem;
        }}
        .metric-card.highlight .value {{ color: #e91e8c; }}
        .metric-card.green .value {{ color: #4caf50; }}
        .charts {{
            display: grid; grid-template-columns: 1fr 1fr;
            gap: 1.5rem; margin-bottom: 1.5rem;
        }}
        .chart-card {{
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px; padding: 1rem;
            backdrop-filter: blur(10px);
            cursor: pointer; transition: border-color 0.3s;
        }}
        .chart-card:hover {{ border-color: rgba(79,195,247,0.4); }}
        .chart-card::after {{
            content: '🔍 Double-click to expand';
            display: block; text-align: center;
            font-size: 0.7rem; color: #555; margin-top: 0.3rem;
        }}
        .chart-card iframe {{
            width: 100%; height: 380px; border: none; border-radius: 8px;
            pointer-events: auto;
        }}
        .fullscreen-overlay {{
            display: none; position: fixed; top: 0; left: 0;
            width: 100vw; height: 100vh; z-index: 9999;
            background: rgba(15,12,41,0.97);
            backdrop-filter: blur(20px);
            flex-direction: column; padding: 1rem;
        }}
        .fullscreen-overlay.active {{ display: flex; }}
        .fullscreen-close {{
            align-self: flex-start;
            background: linear-gradient(135deg, #e91e8c, #c2185b);
            color: white; border: none; border-radius: 10px;
            padding: 0.6rem 1.5rem; font-family: 'Inter', sans-serif;
            font-size: 0.9rem; font-weight: 600; cursor: pointer;
            margin-bottom: 0.8rem; transition: all 0.3s ease;
        }}
        .fullscreen-close:hover {{ transform: scale(1.05); box-shadow: 0 4px 20px rgba(233,30,140,0.4); }}
        .fullscreen-overlay iframe {{
            flex: 1; width: 100%; border: none; border-radius: 12px;
        }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 0.5rem; }}
        th, td {{ padding: 0.6rem 0.8rem; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.08); }}
        th {{ color: #e91e8c; font-weight: 600; text-transform: uppercase; font-size: 0.7rem; letter-spacing: 1px; }}
        td {{ font-size: 0.85rem; }}
        .clickable-price {{
            cursor: pointer; text-decoration: underline; text-decoration-style: dotted;
            transition: all 0.2s;
        }}
        .clickable-price:hover {{ opacity: 0.8; transform: scale(1.05); display: inline-block; }}
        .price-modal {{
            display: none; position: fixed; top: 0; left: 0;
            width: 100vw; height: 100vh; z-index: 10000;
            background: rgba(0,0,0,0.7); backdrop-filter: blur(8px);
            justify-content: center; align-items: center;
        }}
        .price-modal.active {{ display: flex; }}
        .price-modal-content {{
            background: linear-gradient(145deg, #1a1a3e, #0f0c29);
            border: 1px solid rgba(79,195,247,0.3);
            border-radius: 16px; padding: 1.5rem; max-width: 500px;
            width: 90%; max-height: 70vh; overflow-y: auto;
        }}
        .price-modal-content h3 {{ color: #4fc3f7; margin-bottom: 1rem; }}
        .price-modal-content .detail-row {{
            display: flex; justify-content: space-between;
            padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.08);
            font-size: 0.85rem;
        }}
        .price-modal-content .detail-label {{ color: #888; }}
        .price-modal-content .detail-value {{ font-weight: 600; }}
        .price-modal-close {{
            background: linear-gradient(135deg, #e91e8c, #c2185b);
            color: white; border: none; border-radius: 8px;
            padding: 0.5rem 1.2rem; cursor: pointer; margin-top: 1rem;
            font-family: 'Inter', sans-serif; font-weight: 600;
        }}
        .insights-grid {{
            display: grid; grid-template-columns: 1fr 1fr;
            gap: 1.5rem; margin-bottom: 1.5rem;
        }}
        .updated {{ text-align: center; margin-top: 2rem; color: #555; font-size: 0.75rem; }}
        .check-btn {{
            background: linear-gradient(135deg, #e91e8c, #c2185b);
            color: white; border: none; border-radius: 12px;
            padding: 0.6rem 1.5rem; font-family: 'Inter', sans-serif;
            font-size: 0.85rem; font-weight: 600; cursor: pointer;
            transition: all 0.3s ease; letter-spacing: 0.5px;
        }}
        .check-btn:hover {{ transform: scale(1.05); box-shadow: 0 4px 20px rgba(233,30,140,0.4); }}
        .check-btn:disabled {{ opacity: 0.6; cursor: not-allowed; transform: none; box-shadow: none; }}
        .check-btn .spinner {{
            display: inline-block; animation: spin 1s linear infinite;
            margin-right: 0.4rem;
        }}
        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        .advisor-bar {{
            display: flex;
            align-items: center;
            gap: 1rem;
            margin: 1rem auto 1.5rem;
            padding: 1rem 1.5rem;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(79,195,247,0.3);
            border-radius: 12px;
            backdrop-filter: blur(10px);
            max-width: 900px;
            flex-wrap: wrap;
            justify-content: center;
        }}
        .advisor-bar label {{ color: #4fc3f7; font-size: 0.85rem; font-weight: 600; }}
        .advisor-bar input[type="date"] {{
            background: rgba(255,255,255,0.1); color: white;
            border: 1px solid rgba(255,255,255,0.2); border-radius: 8px;
            padding: 0.5rem 1rem; font-family: 'Inter', sans-serif;
            font-size: 0.9rem; cursor: pointer;
        }}
        .advisor-bar input[type="date"]::-webkit-calendar-picker-indicator {{ filter: invert(1); }}
        .advisor-results {{
            max-width: 900px; margin: 0 auto 1.5rem;
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(79,195,247,0.2);
            border-radius: 12px; padding: 1.5rem;
            backdrop-filter: blur(10px); display: none;
        }}
        .advisor-results.visible {{ display: block; }}
        .advisor-results .advice-text {{
            background: rgba(79,195,247,0.1); border-left: 3px solid #4fc3f7;
            padding: 0.8rem 1rem; border-radius: 0 8px 8px 0;
            margin-bottom: 1rem; font-size: 0.9rem; line-height: 1.5;
        }}
        .advisor-results .route-card {{
            display: flex; justify-content: space-between; align-items: center;
            padding: 0.7rem 1rem; border-bottom: 1px solid rgba(255,255,255,0.08);
        }}
        .advisor-results .route-card:last-child {{ border-bottom: none; }}
        .advisor-results .route-name {{ font-weight: 600; color: #e0e0e0; }}
        .advisor-results .route-price {{ font-size: 1.2rem; font-weight: 700; }}
        .advisor-results .trend-up {{ color: #f44336; }}
        .advisor-results .trend-down {{ color: #4caf50; }}
        .advisor-results .trend-stable {{ color: #888; }}
        .advisor-results .meta {{ font-size: 0.75rem; color: #888; }}
        .advisor-loading {{ text-align: center; padding: 1rem; color: #4fc3f7; }}
        @media (max-width: 768px) {{
            body {{ padding: 1rem; }}
            .timer-bar {{ gap: 1rem; padding: 1rem; }}
            .timer-item .timer-value {{ font-size: 1.1rem; }}
            .metrics {{ grid-template-columns: repeat(2, 1fr); gap: 0.5rem; }}
            .metric-card {{ padding: 1rem 0.5rem; }}
            .metric-card .value {{ font-size: 1.2rem; }}
            .charts, .insights-grid {{ grid-template-columns: 1fr; }}
            .route-tabs {{ flex-wrap: wrap; margin-left: 0; margin-top: 1rem; width: 100%; border-right: 1px solid #4fc3f7; }}
            .route-tab {{ flex: 1; padding: 10px 5px; text-align: center; border-bottom: 1px solid #4fc3f7; }}
            .header h1 {{ font-size: 1.8rem; }}
            .advisor-bar {{ flex-direction: column; align-items: stretch; }}
            .advisor-bar label {{ text-align: center; }}
            .chart-card iframe {{ height: 300px; }}
            .data-table th, .data-table td {{ font-size: 0.75rem; padding: 0.4rem; }}
        }}
    </style>
</head>
<body>
    <!-- Fullscreen chart overlay -->
    <div class="fullscreen-overlay" id="fullscreenOverlay">
        <button class="fullscreen-close" onclick="closeFullscreen()">← Back to Dashboard</button>
        <iframe id="fullscreenIframe" src=""></iframe>
    </div>

    <!-- Price detail modal -->
    <div class="price-modal" id="priceModal" onclick="if(event.target===this)closePriceModal()">
        <div class="price-modal-content" id="priceModalContent">
            <div id="priceModalBody">Loading...</div>
            <button class="price-modal-close" onclick="closePriceModal()">Close</button>
        </div>
    </div>

    <!-- Info Modal -->
    <div class="price-modal" id="infoModal" onclick="if(event.target===this)closeInfoModal()">
        <div class="price-modal-content" style="max-width: 600px;">
            <h3 style="color: #4fc3f7; margin-bottom: 1rem; border-bottom: 1px solid rgba(79,195,247,0.3); padding-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center;">
                How these metrics are calculated
                <button onclick="closeInfoModal()" style="background: none; border: none; color: #888; cursor: pointer; font-size: 1.5rem; line-height: 1;">&times;</button>
            </h3>
            
            <div style="font-size: 0.9rem; line-height: 1.6; color: #e0e0e0; max-height: 60vh; overflow-y: auto; padding-right: 0.5rem;">
                <p style="margin-bottom: 1rem;"><strong style="color: #e91e8c;">Lowest Price Found:</strong> Looks at every single price scraped for this route and finds the absolute minimum value across all dates and times.</p>
                <p style="margin-bottom: 1rem;"><strong style="color: #e91e8c;">Average Price:</strong> The mathematical average of all prices collected for this specific route, providing a normal baseline.</p>
                <p style="margin-bottom: 1rem;"><strong style="color: #e91e8c;">&#127919; Best Booking Window:</strong> Groups all prices by how many days before the flight the price was checked, calculates the average price for each window, and highlights the timeframe with the absolute lowest average.</p>
                <p style="margin-bottom: 1rem;"><strong style="color: #e91e8c;">&#9992;&#65039; Cheapest Day to Fly:</strong> Takes the departure date to find the day of the week, calculates the average price of flights departing on those days, and identifies the cheapest day to travel.</p>
                <p style="margin-bottom: 1rem;"><strong style="color: #e91e8c;">&#9200; Best Hour to Book:</strong> Extracts the exact hour the system checked the price, averages prices for each hour of the day, and highlights the historically cheapest hour to search for flights.</p>
                <p style="margin-bottom: 1rem;"><strong style="color: #e91e8c;">&#128197; Best Day to Book:</strong> Extracts the day of the week the system checked the price, averages the prices found, and highlights the best day of the week to catch general price drops.</p>
            </div>
            <button class="price-modal-close" onclick="closeInfoModal()" style="width: 100%; margin-top: 1rem; padding: 0.8rem;">Got it</button>
        </div>
    </div>

    <div class="header">
        <h1>FlySafair Price Tracker</h1>
        <p>Automated hourly monitoring \u2022 George, Cape Town & Johannesburg routes</p>
    </div>

    <div class="timer-bar">
        <div class="timer-item">
            <div class="timer-value" id="currentTime">--:--:--</div>
            <div class="timer-label">Current Time</div>
        </div>
        <div class="timer-item">
            <div class="timer-value" id="lastScrape">{now_time}</div>
            <div class="timer-label">Last Check</div>
        </div>
        <div class="timer-item countdown">
            <div class="timer-value" id="nextCheck">--:--</div>
            <div class="timer-label">Next Check In</div>
        </div>
        <div class="timer-item">
            <div class="timer-value" id="nextCheckTime">--:--:--</div>
            <div class="timer-label">Next Check At</div>
        </div>
        <div class="timer-item">
            <div class="timer-value">{total_checks}</div>
            <div class="timer-label">Total Checks</div>
        </div>
        <div class="timer-item" id="durationContainer" style="display: none;">
            <div class="timer-value" id="scrapeDuration" style="color: #4caf50; font-size: 1.1rem; padding-top: 0.2rem;">--m --s</div>
            <div class="timer-label">Scrape Duration</div>
        </div>
        <div class="timer-item">
            <button class="check-btn" id="checkNowBtn" onclick="triggerCheck()">
                &#128269; Check Now
            </button>
        </div>
    </div>

    <div class="advisor-bar">
        <label>&#9992; When do you want to fly?</label>
        <input type="date" id="flightDatePicker" onchange="getFlightAdvice()">
        <span id="advisorStatus" style="color: #888; font-size: 0.8rem;"></span>
    </div>
    <div class="advisor-results" id="advisorResults"></div>

    <h2 class="section-title">\U0001f4c5 Live Interactive Calendar</h2>
    <div style="width: 100%; border-radius: 12px; overflow: hidden; margin-bottom: 2rem; background: transparent;">
        <iframe id="calendarFrame" src="" style="width: 100%; height: 900px; border: none; background: transparent;"></iframe>
    </div>

    <h2 class="section-title" style="display: flex; align-items: center; justify-content: space-between;">
        <span>\U0001f4a1 Key Insights By Route</span>
        <button onclick="showInfoModal()" title="How are these calculated?" style="background: transparent; border: 1px solid #4fc3f7; color: #4fc3f7; border-radius: 50%; width: 26px; height: 26px; cursor: pointer; display: flex; align-items: center; justify-content: center; font-family: 'Inter', sans-serif; font-size: 14px; font-weight: bold; transition: all 0.2s; margin-left: 10px;" onmouseover="this.style.background='#4fc3f7'; this.style.color='#1a1a2e';" onmouseout="this.style.background='transparent'; this.style.color='#4fc3f7';">i</button>
    </h2>
"""
    
    for route in sorted(df['route'].unique()):
        route_df = df[df['route'] == route]
        
        r_avg_price = route_df['price'].mean()
        r_min_price = route_df['price'].min()
        r_total_records = len(route_df)
        
        # Best booking window
        r_avg_by_days = route_df.groupby('days_before_flight')['price'].mean()
        r_best_days_ahead = int(r_avg_by_days.idxmin()) if not r_avg_by_days.empty else "N/A"
        
        # Best day to fly
        r_avg_by_dow = route_df.groupby(route_df['flight_date'].dt.dayofweek)['price'].mean()
        r_best_dow_fly = day_order[r_avg_by_dow.idxmin()] if not r_avg_by_dow.empty else "N/A"
        
        # Best hour to book
        r_avg_by_hour = route_df.groupby(route_df['scrape_datetime'].dt.hour)['price'].mean()
        r_best_hour = f"{int(r_avg_by_hour.idxmin()):02d}:00" if not r_avg_by_hour.empty and len(r_avg_by_hour) > 1 else "Need more data"
        
        # Best day to book
        r_avg_by_dow_book = route_df.groupby(route_df['scrape_datetime'].dt.dayofweek)['price'].mean()
        r_best_dow_book = day_order[r_avg_by_dow_book.idxmin()] if not r_avg_by_dow_book.empty and len(r_avg_by_dow_book) > 1 else "Need more data"

        html += f"""
    <h3 style="color: #4fc3f7; margin: 1.5rem 0 1rem; font-size: 1.1rem;">✈️ {route}</h3>
    <div class="metrics">
        <div class="metric-card highlight">
            <div class="value">R{r_min_price:,.0f}</div>
            <div class="label">Lowest Price Found</div>
        </div>
        <div class="metric-card">
            <div class="value">R{r_avg_price:,.0f}</div>
            <div class="label">Average Price</div>
        </div>
        <div class="metric-card green">
            <div class="value">{r_best_days_ahead} days</div>
            <div class="label">\U0001f3af Best Booking Window</div>
        </div>
        <div class="metric-card green">
            <div class="value">{r_best_dow_fly}</div>
            <div class="label">\u2708 Cheapest Day to Fly</div>
        </div>
        <div class="metric-card highlight">
            <div class="value">{r_best_hour}</div>
            <div class="label">\u23f0 Best Hour to Book</div>
        </div>
        <div class="metric-card highlight">
            <div class="value">{r_best_dow_book}</div>
            <div class="label">\U0001f4c5 Best Day to Book</div>
        </div>
        <div class="metric-card">
            <div class="value">{r_total_records:,}</div>
            <div class="label">Data Points</div>
        </div>
    </div>
"""

    # Load volatility metrics directly to avoid CORS issues on local filesystem
    try:
        import json
        with open(os.path.join(output_dir, "price_trends.json"), "r") as f:
            trends_data = json.load(f)
            
        t_total = 0; t_up = 0; t_down = 0
        up_days_sum = 0; down_days_sum = 0
        up_routes = 0; down_routes = 0
        
        # Build tabular rows for per route volatility
        route_volatility_rows = ""
        
        for rt, d in trends_data.items():
            t_total += d['total_shifts']
            t_up += d['up_count']
            t_down += d['down_count']
            if d['avg_days_before_up'] is not None:
                up_days_sum += d['avg_days_before_up']
                up_routes += 1
            if d['avg_days_before_down'] is not None:
                down_days_sum += d['avg_days_before_down']
                down_routes += 1
                
            rt_avg_up = f"{d['avg_days_before_up']:.1f} Days" if d['avg_days_before_up'] is not None else "N/A"
            rt_avg_down = f"{d['avg_days_before_down']:.1f} Days" if d['avg_days_before_down'] is not None else "N/A"
            
            route_volatility_rows += f"""
                <tr onclick="showRouteShifts('{rt}')" style="cursor: pointer; transition: background 0.2s;" onmouseover="this.style.background='#f0f4f8'" onmouseout="this.style.background='transparent'">
                    <td><strong style="color: var(--fs-blue);">{rt}</strong></td>
                    <td>{d['total_shifts']}</td>
                    <td style="color: #f44336; font-weight: 600;">{d['up_count']}</td>
                    <td style="color: #4caf50; font-weight: 600;">{d['down_count']}</td>
                    <td>{rt_avg_up}</td>
                    <td>{rt_avg_down}</td>
                </tr>
            """
                
        avg_up = f"{(up_days_sum / up_routes):.1f} Days" if up_routes > 0 else "N/A"
        avg_down = f"{(down_days_sum / down_routes):.1f} Days" if down_routes > 0 else "N/A"
        
        html += f"""
    <h2 class="section-title">📉 Volatility & Price Trends</h2>
    <div class="metrics">
        <div class="metric-card">
            <div class="value">{t_total}</div>
            <div class="label">Total Price Shifts Detected</div>
        </div>
        <div class="metric-card highlight">
            <div class="value">{t_up}</div>
            <div class="label">Price Increases</div>
        </div>
        <div class="metric-card green">
            <div class="value">{t_down}</div>
            <div class="label">Price Drops</div>
        </div>
        <div class="metric-card highlight" style="grid-column: span 2;">
            <div class="value" style="font-size: 1.2rem; margin-top: 0.5rem;">{avg_up}</div>
            <div class="label">Average Days Before Price INCREASE</div>
        </div>
        <div class="metric-card green" style="grid-column: span 2;">
            <div class="value" style="font-size: 1.2rem; margin-top: 0.5rem;">{avg_down}</div>
            <div class="label">Average Days Before Price DROP</div>
        </div>
    </div>
    
    <div class="chart-card" style="margin-top: 1.5rem; margin-bottom: 2rem;">
        <h3 style="margin-bottom: 0.5rem; color: #4fc3f7; font-size: 0.95rem;">Volatility by Route</h3>
        <div style="width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch;">
        <table>
            <thead>
                <tr>
                    <th>Route</th>
                    <th>Total Shifts</th>
                    <th>Increases</th>
                    <th>Drops</th>
                    <th>Avg Days Before Increase</th>
                    <th>Avg Days Before Drop</th>
                </tr>
            </thead>
            <tbody>
                {route_volatility_rows}
            </tbody>
        </table>
        </div>
    </div>
    
    <div class="charts">
        <div class="chart-card" style="grid-column: span 2;"><iframe src="report_price_shifts.html"></iframe></div>
    </div>
"""
    except Exception as e:
        print(f"Could not load price trends for dashboard: {e}")

    html += f"""
    <h2 class="section-title">\U0001f4ca How Far in Advance Should You Book?</h2>
    <div class="insights-grid">
        <div class="chart-card"><iframe src="report_booking_window.html"></iframe></div>
        <div class="chart-card">
            {booking_section_html}
        </div>
    </div>

    <h2 class="section-title">\u2708 When to Fly & When to Book</h2>
    <div class="charts">
        <div class="chart-card"><iframe src="report_day_fly.html"></iframe></div>
        <div class="chart-card"><iframe src="report_hour_book.html"></iframe></div>
        <div class="chart-card"><iframe src="report_day_book.html"></iframe></div>
        <div class="chart-card"><iframe src="report_booking_by_route.html"></iframe></div>
    </div>

    <h2 class="section-title">\U0001f5fa Route Analysis</h2>
    <div class="charts">
        <div class="chart-card"><iframe src="report_routes.html"></iframe></div>
        <div class="chart-card"><iframe src="report_heatmap.html"></iframe></div>
    </div>

    <div class="chart-card" style="margin-top: 1.5rem;">
        <h3 style="margin-bottom: 0.5rem; color: #4fc3f7; font-size: 0.95rem;">Route Summary</h3>
        <div style="width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch;">
        <table>
            <thead>
                <tr><th>Route</th><th>Average</th><th>Minimum</th><th>Maximum</th><th>Change</th><th>Samples</th></tr>
            </thead>
            <tbody>
"""
    for _, row in route_stats.iterrows():
        route_name = row['Route']
        change = price_changes.get(route_name, None)
        if change is not None:
            if change > 0:
                change_html = f'<span style="color: #f44336;">&#9650; R{abs(change):,.0f}</span>'
            elif change < 0:
                change_html = f'<span style="color: #4caf50;">&#9660; R{abs(change):,.0f}</span>'
            else:
                change_html = '<span style="color: #888;">&#9472; No change</span>'
        else:
            change_html = '<span style="color: #888;">&#8211;</span>'

        html += f"""                <tr>
                    <td>{route_name}</td>
                    <td>R{row['Average Price']:,.2f}</td>
                    <td style="color: #4caf50;"><span class="clickable-price" onclick="showPriceDetail('{route_name}', 'min')">R{row['Min Price']:,.2f}</span></td>
                    <td style="color: #f44336;"><span class="clickable-price" onclick="showPriceDetail('{route_name}', 'max')">R{row['Max Price']:,.2f}</span></td>
                    <td>{change_html}</td>
                    <td>{int(row['Data Points'])}</td>
                </tr>\n"""

    html += f"""            </tbody>
        </table>
        </div>
    </div>

    <p class="updated">Data last updated: {now_str} &bull; Dashboard refreshes after each scrape</p>

    <script>
        // Use Supabase client configured in HEAD
        const lastScrapeStr = "{now_iso}";
        const CHECK_INTERVAL_MS = 1.5 * 60 * 60 * 1000;
        const lastScrapeDate = new Date(lastScrapeStr);
        
        // Align next check to the top of the next hour
        let nextCheckDate = new Date(lastScrapeDate.getTime() + CHECK_INTERVAL_MS);
        nextCheckDate.setMinutes(0, 0, 0);
        
        // If the calculation accidentally landed in the past or exactly now, push forward 1 hour
        if (nextCheckDate <= lastScrapeDate) {{
            nextCheckDate = new Date(nextCheckDate.getTime() + CHECK_INTERVAL_MS);
        }}
        
        // Use relative links for Vercel
        document.getElementById('calendarFrame').src = "calendar.html";

        function pad(n) {{ return n.toString().padStart(2, '0'); }}

        function updateTimers() {{
            const now = new Date();
            document.getElementById('currentTime').textContent =
                pad(now.getHours()) + ':' + pad(now.getMinutes()) + ':' + pad(now.getSeconds());
            document.getElementById('nextCheckTime').textContent =
                pad(nextCheckDate.getHours()) + ':' + pad(nextCheckDate.getMinutes()) + ':' + pad(nextCheckDate.getSeconds());
            let diff = nextCheckDate.getTime() - now.getTime();
            if (diff <= 0) {{
                document.getElementById('nextCheck').textContent = 'NOW';
                document.getElementById('nextCheck').style.color = '#4caf50';
            }} else {{
                const mins = Math.floor(diff / 60000);
                const secs = Math.floor((diff % 60000) / 1000);
                document.getElementById('nextCheck').textContent = pad(mins) + ':' + pad(secs);
            }}
        }}
        updateTimers();
        setInterval(updateTimers, 1000);

        // Serverless Vercel deployment has no status endpoint
        async function pollStatus() {{
            const btn = document.getElementById('checkNowBtn');
            btn.innerHTML = '&#9203; Running on Vercel';
            btn.disabled = true;
        }}
        pollStatus();

        // Flight Date Advisor
        async function getFlightAdvice() {{
            const dateInput = document.getElementById('flightDatePicker');
            const resultsDiv = document.getElementById('advisorResults');
            const statusSpan = document.getElementById('advisorStatus');
            const selectedDate = dateInput.value;
            if (!selectedDate) return;

            statusSpan.textContent = '⏳ Analysing data...';
            resultsDiv.className = 'advisor-results visible';
            resultsDiv.innerHTML = '<div class="advisor-loading"><span class="spinner">⏳</span> Checking data for ' + selectedDate + '...</div>';

            try {{
                // Supabase equivalent for flight advice
                const {{ data, error }} = await window.supabaseClient
                    .from('flight_prices')
                    .select('route, price, scrape_datetime, days_before_flight')
                    .eq('flight_date', selectedDate)
                    .order('scrape_datetime');
                    
                if (error) throw error;
                statusSpan.textContent = '';
                
                if (!data || data.length === 0) {{
                    resultsDiv.innerHTML = '<div class="advice-text">❌ No exact data for this date yet. Check back later!</div>';
                    return;
                }}
                
                let route_prices = {{}};
                data.forEach(r => {{
                    if (!route_prices[r.route]) route_prices[r.route] = [];
                    route_prices[r.route].push(r);
                }});
                
                let routesInfo = [];
                for (const route in route_prices) {{
                    const entries = route_prices[route];
                    const prices = entries.map(e => e.price);
                    const latest = entries[entries.length - 1];
                    const first = entries[0];
                    let trend = "stable";
                    if (prices.length > 1) {{
                        if (latest.price < first.price) trend = "dropping";
                        else if (latest.price > first.price) trend = "rising";
                    }}
                    routesInfo.push({{
                        route: route,
                        current_price: latest.price,
                        lowest_seen: Math.min(...prices),
                        highest_seen: Math.max(...prices),
                        avg_price: Math.round(prices.reduce((a,b)=>a+b,0)/prices.length),
                        checks: prices.length,
                        trend: trend
                    }});
                }}
                
                // Extremely simple local booking advice 
                const flightDate = new Date(selectedDate);
                const day_of_week = flightDate.toLocaleString('default', {{ weekday: 'long' }});
                const days_until = Math.floor((flightDate - new Date()) / (1000 * 60 * 60 * 24));
                
                let advice = "You have " + days_until + " days left.";
                if (days_until > 30) advice += " Plenty of time. Watch for price drops.";
                else if (days_until > 14) advice += " Good window to book soon.";
                else if (days_until > 7) advice += " Prices usually start rising now. Book this week.";
                else advice += " Book NOW for the best remaining price.";

                let html = '<h3 style="color: #4fc3f7; margin-bottom: 0.8rem;">✈️ Flight Advice for ' +
                    day_of_week + ', ' + selectedDate + '</h3>';
                html += '<div style="color: #aaa; margin-bottom: 0.8rem; font-size: 0.85rem;">' +
                    (days_until >= 0 ? '📅 ' + days_until + ' days from now' : '⚠️ This date has passed') + '</div>';
                html += '<div class="advice-text">💡 ' + advice + '</div>';

                html += '<h4 style="color: #e91e8c; margin: 1rem 0 0.5rem; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px;">Current Prices for This Date</h4>';
                routesInfo.forEach(r => {{
                    const trendIcon = r.trend === 'dropping' ? '<span class="trend-down">▼ dropping</span>' :
                                      r.trend === 'rising' ? '<span class="trend-up">▲ rising</span>' :
                                      '<span class="trend-stable">─ stable</span>';
                    const priceColor = r.current_price <= r.avg_price ? '#4caf50' : '#ff9800';
                    html += '<div class="route-card">' +
                        '<div><div class="route-name">' + r.route + '</div>' +
                        '<div class="meta">Low: R' + r.lowest_seen.toLocaleString() + ' · High: R' + r.highest_seen.toLocaleString() + ' · ' + r.checks + ' checks · Trend: ' + trendIcon + '</div></div>' +
                        '<div class="route-price" style="color:' + priceColor + '">R' + r.current_price.toLocaleString() + '</div></div>';
                }});

                resultsDiv.innerHTML = html;
            }} catch(e) {{
                statusSpan.textContent = '';
                resultsDiv.innerHTML = '<div class="advice-text">❌ Could not load advice from Supabase.</div>';
            }}
        }}

        // Price detail popup
        async function showPriceDetail(route, type) {{
            const modal = document.getElementById('priceModal');
            const body = document.getElementById('priceModalBody');
            modal.classList.add('active');
            body.innerHTML = '<div style=\"text-align:center; color: #4fc3f7;\">Loading from Supabase...</div>';

            try {{
                // Fetch to find min or max price for route
                const {{ data, error }} = await window.supabaseClient
                    .from('flight_prices')
                    .select('price, flight_date, scrape_datetime, days_before_flight')
                    .eq('route', route)
                    .order('price', {{ ascending: type === 'min' }})
                    .limit(50);
                    
                if (error) throw error;

                if (!data || data.length === 0) {{
                    body.innerHTML = '<div style=\"color: #f44336;\">No data for this route</div>';
                    return;
                }}

                const targetPrice = data[0].price;
                const records = data.filter(r => r.price === targetPrice).slice(0, 10); // show up to 10

                const color = type === 'min' ? '#4caf50' : '#f44336';
                const label = type === 'min' ? 'Lowest' : 'Highest';
                let html = '<h3>' + label + ' Price for ' + route + '</h3>';
                html += '<div style=\"font-size: 2rem; font-weight: 700; color:' + color + '; margin-bottom: 1rem;\">R' + targetPrice.toLocaleString() + '</div>';
                html += '<div style=\"color: #888; font-size: 0.8rem; margin-bottom: 0.8rem;\">Found ' + records.length + ' time(s) at this price (showing latest)</div>';

                records.forEach(function(r) {{
                    const dt = new Date(r.flight_date);
                    const dayName = dt.toLocaleString('default', {{ weekday: 'long' }});
                    
                    html += '<div style=\"background: rgba(255,255,255,0.03); border-radius: 8px; padding: 0.6rem; margin-bottom: 0.5rem;\">';
                    html += '<div class=\"detail-row\"><span class=\"detail-label\">Flight Date</span><span class=\"detail-value\">' + dayName + ', ' + r.flight_date + '</span></div>';
                    html += '<div class=\"detail-row\"><span class=\"detail-label\">Seen At</span><span class=\"detail-value\">' + new Date(r.scrape_datetime).toLocaleString() + '</span></div>';
                    html += '<div class=\"detail-row\"><span class=\"detail-label\">Days Before Flight</span><span class=\"detail-value\">' + r.days_before_flight + ' days</span></div>';
                    html += '</div>';
                }});

                body.innerHTML = html;
            }} catch(e) {{
                body.innerHTML = '<div style=\"color: #f44336;\">Could not load details from Supabase.</div>';
            }}
        }}

        function closePriceModal() {{
            document.getElementById('priceModal').classList.remove('active');
        }}

        function showInfoModal() {{
            document.getElementById('infoModal').classList.add('active');
        }}

        function closeInfoModal() {{
            document.getElementById('infoModal').classList.remove('active');
        }}

        // Fullscreen chart on double-click
        document.querySelectorAll('.chart-card').forEach(card => {{
            card.addEventListener('dblclick', () => {{
                const iframe = card.querySelector('iframe');
                if (iframe && iframe.src) {{
                    const overlay = document.getElementById('fullscreenOverlay');
                    const fsIframe = document.getElementById('fullscreenIframe');
                    fsIframe.src = iframe.src;
                    overlay.classList.add('active');
                }}
            }});
        }});

        function closeFullscreen() {{
            const overlay = document.getElementById('fullscreenOverlay');
            overlay.classList.remove('active');
            document.getElementById('fullscreenIframe').src = '';
        }}

        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') closeFullscreen();
        }});

        // Auto-refresh: poll for dashboard.html changes every 30s
        let knownUpdateTime = 0;
        async function checkForUpdates() {{
            try {{
                const res = await fetch(API_BASE + '/api/last-update');
                const data = await res.json();
                if (knownUpdateTime === 0) {{
                    knownUpdateTime = data.last_update;
                }} else if (data.last_update > knownUpdateTime) {{
                    console.log('Dashboard updated — reloading...');
                    location.reload();
                }}
            }} catch(e) {{}}
        }}
        setInterval(checkForUpdates, 30000);  // check every 30 seconds
        checkForUpdates();  // initial check

        // Wake Lock — keeps PC and screen awake while dashboard is open
        let wakeLock = null;
        async function requestWakeLock() {{
            try {{
                wakeLock = await navigator.wakeLock.request('screen');
                console.log('Wake Lock active — screen will stay on');
                wakeLock.addEventListener('release', () => {{
                    console.log('Wake Lock released');
                }});
            }} catch (err) {{
                console.log('Wake Lock not supported:', err.message);
            }}
        }}
        if ('wakeLock' in navigator) {{
            requestWakeLock();
            // Re-acquire if page becomes visible again (e.g. after tab switch)
            document.addEventListener('visibilitychange', () => {{
                if (document.visibilityState === 'visible') requestWakeLock();
            }});
        }}
        
    </script>
    <style>
        .modal-overlay {{
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }}
        .modal-overlay.hidden {{
            display: none;
        }}
        .modal-content {{
            background: var(--bg-color, #1e1e2d);
            border-radius: 12px;
            padding: 2rem;
            width: 90%;
            max-width: 800px;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            position: relative;
        }}
        .modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding-bottom: 1rem;
        }}
        .modal-header h2 {{
            margin: 0;
            color: var(--fs-blue, #4fc3f7);
        }}
        .close-btn {{
            background: none;
            border: none;
            color: #aaa;
            font-size: 2rem;
            cursor: pointer;
        }}
        .close-btn:hover {{
            color: #fff;
        }}
        .flights-list-header {{
            display: grid;
            padding: 1rem;
            background: rgba(255,255,255,0.05);
            border-radius: 8px;
            font-weight: bold;
            color: #aaa;
            margin-bottom: 0.5rem;
        }}
        .flight-row {{
            display: grid;
            padding: 1rem;
            border-bottom: 1px solid rgba(255,255,255,0.05);
            align-items: center;
        }}
        .flight-row:hover {{
            background: rgba(255,255,255,0.02);
        }}
    </style>
    
    <!-- Route Shifts Modal -->
    <div id="routeShiftsModal" class="modal-overlay hidden">
        <div class="modal-content" style="max-width: 800px;">
            <div class="modal-header">
                <h2 id="routeShiftsTitle">Price Shifts Data</h2>
                <button class="close-btn" onclick="document.getElementById('routeShiftsModal').classList.add('hidden');">&times;</button>
            </div>
            
            <div id="routeShiftsSummaryContainer" style="margin-bottom: 2rem;">
                <h3 style="color: #e91e8c; margin-bottom: 0.8rem; font-size: 1rem;">Comparison by Flight Time</h3>
                <div class="flights-list-header" style="grid-template-columns: 1fr 1fr 1fr 1fr 1fr 1.5fr;">
                    <span>Flight</span>
                    <span>Time</span>
                    <span>Total Shifts</span>
                    <span>Increases</span>
                    <span>Drops</span>
                    <span>Avg Shift</span>
                </div>
                <div class="flights-list" id="routeShiftsSummary">
                    <!-- Populated by JS -->
                </div>
            </div>

            <div class="flights-list-container">
                <h3 style="color: #e91e8c; margin-bottom: 0.8rem; font-size: 1rem;">Individual Flights</h3>
                <div class="flights-list-header" style="grid-template-columns: 2fr 1.5fr 1.5fr 1.5fr 1fr;">
                    <span>Flight</span>
                    <span>Initial Price</span>
                    <span>Latest Price</span>
                    <span>Shift Amount</span>
                    <span>Days Before</span>
                </div>
                <div class="flights-list" id="routeShiftsList">
                    <!-- Populated by JS -->
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Inject shifts data from analyzer.py directly to bypass CORS
"""
    try:
        import json
        with open(os.path.join(output_dir, "shifts_data_full.json"), "r") as f:
            full_shifts_json = f.read()
        with open(os.path.join(output_dir, "flight_summary.json"), "r") as f:
            flight_summary_json = f.read()
    except Exception:
        full_shifts_json = "{}"
        flight_summary_json = "{}"
        
    html += """
        const SHIFT_DATA = __SHIFTS_DATA_PLACEHOLDER__;
        const FLIGHT_SUMMARY_DATA = __FLIGHT_SUMMARY_PLACEHOLDER__;
        
        function showRouteShifts(route) {
            const modal = document.getElementById('routeShiftsModal');
            const title = document.getElementById('routeShiftsTitle');
            const summaryList = document.getElementById('routeShiftsSummary');
            const summaryContainer = document.getElementById('routeShiftsSummaryContainer');
            const list = document.getElementById('routeShiftsList');
            
            title.textContent = 'Price Shifts for ' + route;
            list.innerHTML = '';
            summaryList.innerHTML = '';
            
            if (!SHIFT_DATA[route] || SHIFT_DATA[route].length === 0) {
                summaryContainer.style.display = 'none';
                list.innerHTML = '<div style="padding: 2rem; text-align: center; color: #888;">No price shifts detected for this route yet.</div>';
            } else {
                summaryContainer.style.display = 'block';
                
                // Render summary
                if (FLIGHT_SUMMARY_DATA[route]) {
                    FLIGHT_SUMMARY_DATA[route].forEach(summary => {
                        const row = document.createElement('div');
                        row.className = 'flight-row';
                        row.style.gridTemplateColumns = '1fr 1fr 1fr 1fr 1fr 1.5fr';
                        
                        const avgColor = summary.avg_price_diff > 0 ? 'var(--negative)' : 'var(--positive)';
                        const avgSign = summary.avg_price_diff > 0 ? '+' : '';
                        
                        row.innerHTML = `
                            <div class="f-num" style="color: var(--fs-blue); font-weight: bold;">${summary.flight_number}</div>
                            <div style="color: #ccc;">${summary.departure_time}</div>
                            <div>${summary.total_shifts}</div>
                            <div style="color: var(--negative);">${summary.up_count}</div>
                            <div style="color: var(--positive);">${summary.down_count}</div>
                            <div style="color: ${avgColor}; font-weight: bold;">${avgSign}R${Math.round(summary.avg_price_diff).toLocaleString()}</div>
                        `;
                        summaryList.appendChild(row);
                    });
                }
                
                // Render details
                SHIFT_DATA[route].forEach(shift => {
                    const color = shift.direction === 'Up' ? 'var(--negative)' : 'var(--positive)';
                    const sign = shift.direction === 'Up' ? '+' : '';
                    
                    const row = document.createElement('div');
                    row.className = 'flight-row';
                    row.style.gridTemplateColumns = '2fr 1.5fr 1.5fr 1.5fr 1fr';
                    
                    row.innerHTML = `
                        <div class="f-num">${shift.flight}</div>
                        <div style="color: #666;">R${shift.initial_price.toLocaleString()}</div>
                        <div class="f-price">R${shift.latest_price.toLocaleString()}</div>
                        <div style="color: ${color}; font-weight: bold;">${sign}R${shift.price_diff.toLocaleString()}</div>
                        <div>${shift.days_before}d</div>
                    `;
                    list.appendChild(row);
                });
            }
            
            modal.classList.remove('hidden');
        }
        
        // Close modal when clicking outside
        document.getElementById('routeShiftsModal').addEventListener('click', function(e) {
            if (e.target === this) {
                this.classList.add('hidden');
            }
        });
    </script>
</body>
</html>""".replace("__SHIFTS_DATA_PLACEHOLDER__", full_shifts_json).replace("__FLIGHT_SUMMARY_PLACEHOLDER__", flight_summary_json)

    dashboard_path = os.path.join(output_dir, "dashboard.html")
    with open(dashboard_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"\n  DASHBOARD -> {dashboard_path}")
    print("  Open dashboard.html in your browser to see all insights!")


if __name__ == "__main__":
    run_analysis()
