document.addEventListener("DOMContentLoaded", () => {

    let currentDate = new Date();
    // Default to next month if today is late in the month
    currentDate.setMonth(currentDate.getMonth() + 1);

    let currentRoute = "";
    let priceChart = null;

    const routeSelect = document.getElementById("routeSelect");
    const currentMonthYear = document.getElementById("currentMonthYear");
    const calendarGrid = document.getElementById("calendarGrid");

    // Modal
    const modal = document.getElementById("flightModal");
    const closeModal = document.getElementById("closeModal");
    const modalDateTitle = document.getElementById("modalDateTitle");
    const flightsList = document.getElementById("flightsList");

    // Initialization
    async function init() {
        // Hardcode routes for the calendar widget
        const routes = ["CPT-JNB", "GRJ-JNB", "JNB-CPT", "JNB-GRJ"];

        routes.forEach(route => {
            const opt = document.createElement("option");
            opt.value = route;
            opt.textContent = route;
            routeSelect.appendChild(opt);
        });

        if (routes.length > 0) {
            currentRoute = routes[0];
            loadCalendar();
        }

        routeSelect.addEventListener("change", (e) => {
            currentRoute = e.target.value;
            loadCalendar();
        });

        document.getElementById("prevMonth").addEventListener("click", () => {
            currentDate.setMonth(currentDate.getMonth() - 1);
            loadCalendar();
        });

        document.getElementById("nextMonth").addEventListener("click", () => {
            currentDate.setMonth(currentDate.getMonth() + 1);
            loadCalendar();
        });

        closeModal.addEventListener("click", () => {
            modal.classList.add("hidden");
        });
    }

    async function loadCalendar() {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth() + 1;
        const monthTxt = month < 10 ? `0${month}` : month;
        const monthPrefix = `${year}-${monthTxt}`;

        // Get the accurate last day of the month to prevent Postgres invalid date errors (e.g., April 31st)
        const lastDay = new Date(year, month, 0).getDate();
        const lastDayTxt = lastDay < 10 ? `0${lastDay}` : lastDay;

        currentMonthYear.textContent = currentDate.toLocaleString('default', { month: 'long', year: 'numeric' });
        calendarGrid.innerHTML = "Loading data...";

        try {
            // Use gte and lte instead of like for Postgres dates
            const { data, error } = await window.supabaseClient
                .from('flight_details')
                .select('flight_date, flight_number, price, scrape_datetime')
                .eq('route', currentRoute)
                .gte('flight_date', `${monthPrefix}-01`)
                .lte('flight_date', `${monthPrefix}-${lastDayTxt}`)
                .order('scrape_datetime', { ascending: false });

            if (error) throw error;

            // THE "ABSOLUTE CURRENT CHEAPEST" LOGIC (Fix: Account for millisecond jitter)
            // 1. Group all records by flight_date
            let resultsByDate = {};
            data.forEach(r => {
                if (!resultsByDate[r.flight_date]) resultsByDate[r.flight_date] = [];
                resultsByDate[r.flight_date].push(r);
            });

            let finalCalData = {};
            for (const date in resultsByDate) {
                const records = resultsByDate[date];
                
                // 2. Find the Absolute MAX scrape time for this date
                let maxTime = new Date(0);
                records.forEach(r => {
                    const t = new Date(r.scrape_datetime);
                    if (t > maxTime) maxTime = t;
                });

                // 3. Filter to ONLY include flights within a 10-minute window of the MAX time
                // This captures all flights from the same search session even if they have different millisecond offsets
                const windowMs = 10 * 60 * 1000; 
                let latestScrapeFlights = records.filter(r => {
                    const t = new Date(r.scrape_datetime);
                    return (maxTime - t) < windowMs;
                });

                // 4. Display the absolute cheapest from that recent window
                if (latestScrapeFlights.length > 0) {
                    finalCalData[date] = Math.min(...latestScrapeFlights.map(f => f.price));
                }
            }

            const calData = finalCalData;

            drawGrid(year, month, calData);
        } catch (e) {
            calendarGrid.innerHTML = "Failed to load database. Is the scraper running?";
        }
    }

    function drawGrid(year, month, data) {
        calendarGrid.innerHTML = "";

        // Find min price for highlighting
        let minPrice = Infinity;
        for (const date in data) {
            if (data[date] < minPrice) minPrice = data[date];
        }

        const firstDay = new Date(year, month - 1, 1).getDay();
        const daysInMonth = new Date(year, month, 0).getDate();

        // Adjust for Monday start (0 = Mon, 6 = Sun)
        const startOffset = firstDay === 0 ? 6 : firstDay - 1;

        // Empty cells before start
        for (let i = 0; i < startOffset; i++) {
            const div = document.createElement("div");
            div.className = "day-cell empty";
            calendarGrid.appendChild(div);
        }

        // Day cells
        for (let day = 1; day <= daysInMonth; day++) {
            const dayTxt = day < 10 ? `0${day}` : day;
            const flightDate = `${year}-${month < 10 ? '0' + month : month}-${dayTxt}`;
            const price = data[flightDate];

            const cell = document.createElement("div");
            cell.className = "day-cell";

            const dateSpan = document.createElement("div");
            dateSpan.className = "day-date";
            dateSpan.textContent = day;
            cell.appendChild(dateSpan);

            if (price) {
                const priceSpan = document.createElement("div");
                priceSpan.className = "day-price";
                priceSpan.textContent = `R${price.toFixed(2)}`;
                cell.appendChild(priceSpan);

                if (price === minPrice) {
                    cell.classList.add("cheapest");
                }

                cell.addEventListener("click", () => openModal(flightDate));
            } else {
                cell.classList.add("empty");
            }

            calendarGrid.appendChild(cell);
        }
    }

    async function openModal(date) {
        modalDateTitle.textContent = `Flights for ${date} (${currentRoute})`;
        flightsList.innerHTML = '<div class="loading-spinner">Locating flights...</div>';
        modal.classList.remove("hidden");

        if (priceChart) {
            priceChart.destroy();
            priceChart = null;
        }

        try {
            // 1. Get ALL data for this day
            const { data, error } = await window.supabaseClient
                .from('flight_details')
                .select('*')
                .eq('route', currentRoute)
                .eq('flight_date', date);

            if (error) throw error;

            // 2. Find the absolute LATEST scrape timestamp for this specific date
            let maxScrapeTime = "";
            data.forEach(r => {
                if (r.scrape_datetime > maxScrapeTime) maxScrapeTime = r.scrape_datetime;
            });

            // 3. Filter to ONLY show flights from that latest scrape
            let latestRecords = data.filter(r => r.scrape_datetime === maxScrapeTime);
            
            let flights = latestRecords.map(r => ({
                flight_number: r.flight_number,
                departure_time: r.departure_time,
                arrival_time: r.arrival_time,
                latest_price: r.price,
                is_special: r.is_special,
                scrape_datetime: r.scrape_datetime
            }));

            flights.sort((a, b) => {
                if (a.latest_price !== b.latest_price) return a.latest_price - b.latest_price;
                return a.departure_time.localeCompare(b.departure_time);
            });

            flightsList.innerHTML = "";

            if (flights.length === 0) {
                flightsList.innerHTML = '<div class="loading-spinner">No deep scrape data available for this day.</div>';
                return;
            }

            flights.forEach((f, idx) => {
                const row = document.createElement("div");
                row.className = "flight-row";
                if (idx === 0) row.classList.add("selected");

                let trendHtml = `<span class="trend trend-flat">-</span>`;
                if (f.price_change < 0) {
                    trendHtml = `<span class="trend trend-down">↓ <span class="trend-amount">R${Math.abs(f.price_change).toFixed(0)}</span></span>`;
                } else if (f.price_change > 0) {
                    trendHtml = `<span class="trend trend-up">↑ <span class="trend-amount">R${Math.abs(f.price_change).toFixed(0)}</span></span>`;
                }

                row.innerHTML = `
                    <div class="f-num">${f.flight_number} ${f.is_special ? '<span class="f-special">PROMO</span>' : ''}</div>
                    <div class="f-time">${f.departure_time}</div>
                    <div class="f-time">${f.arrival_time}</div>
                    <div class="f-price">R${f.latest_price.toFixed(2)}</div>
                    <div>${trendHtml}</div>
                `;

                row.addEventListener("click", () => {
                    document.querySelectorAll(".flight-row").forEach(r => r.classList.remove("selected"));
                    row.classList.add("selected");
                    loadChart(date, f.flight_number);
                });

                flightsList.appendChild(row);
            });

            // Auto-load chart for the first cheapest flight
            if (flights.length > 0) {
                loadChart(date, flights[0].flight_number);
            }

        } catch (e) {
            flightsList.innerHTML = '<div class="loading-spinner">Error loading flights.</div>';
        }
    }

    async function loadChart(date, flightNumber) {
        try {
            const { data, error } = await window.supabaseClient
                .from('flight_details')
                .select('scrape_datetime, price')
                .eq('route', currentRoute)
                .eq('flight_date', date)
                .eq('flight_number', flightNumber)
                .order('scrape_datetime', { ascending: true });

            if (error) throw error;
            const history = data.map(r => ({ x: r.scrape_datetime, y: r.price }));

            const ctx = document.getElementById("priceHistoryChart").getContext("2d");

            if (priceChart) {
                priceChart.destroy();
            }

            const labels = history.map(h => {
                const d = new Date(h.x);
                return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${d.getMinutes().toString().padStart(2, '0')}`;
            });
            const dataPts = history.map(h => h.y);

            priceChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: `Price History for ${flightNumber}`,
                        data: dataPts,
                        borderColor: '#ed0080',
                        backgroundColor: 'rgba(237, 0, 128, 0.1)',
                        borderWidth: 3,
                        pointBackgroundColor: '#ed0080',
                        pointRadius: 4,
                        fill: true,
                        tension: 0.3
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: false,
                            ticks: {
                                callback: function (value) { return 'R' + value; }
                            }
                        }
                    },
                    plugins: {
                        legend: { display: false }
                    }
                }
            });

        } catch (e) {
            console.error("Failed to draw chart");
        }
    }

    init();
});
