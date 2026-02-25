# ✈️ FlySafair Price Tracker

A fully automated, end-to-end flight price monitoring system for FlySafair. This tool scrapes ticket prices, stores them historically in a SQLite database, and generates a stunning, high-fidelity interactive dashboard to help travelers find the absolute best time to book their flights.

![Dashboard Preview](screenshots/dashboard_preview.png)

## 🌟 Key Features

The tracker goes far beyond simple price alerts. It analyzes historical data to uncover hidden algorithms and pricing trends:

*   **🕵️ Automated Hour-by-Hour Scraping:** Continuously monitors flight prices across key routes (e.g., George, Cape Town, Johannesburg) without manual intervention.
*   **📉 Price Volatility & Trend Tracking:** Automatically detects when airlines adjust their prices, telling you if a route is trending up or down, and calculating the exact average number of days before a price hike occurs. 
*   **📅 Live Interactive Calendar:** A visual heatmap integrated directly into the dashboard, showing daily price fluctuations at a glance.
*   **💡 Smart Flight Advisor:** A dynamic input that accepts your intended travel date and provides immediate, data-backed advice on whether you should book now or wait, based on historical data for that specific booking window.
*   **📊 Comprehensive Market Analytics:** Generates interactive Plotly charts detailing:
    *   The Optimal Booking Window (how many days in advance to buy).
    *   The Cheapest Day of the Week to Fly.
    *   The Cheapest Hour of the Day to check for prices.
    *   Detailed Route Analysis and Price Heatmaps.
*   **🪄 High-Fidelity Dashboard:** All insights are combined into a premium, responsive, single-page HTML dashboard featuring glassmorphism design, smooth modal transitions, and interactive data tables.

## 🛠️ Technology Stack

*   **Backend & Scraping:** Python, Playwright/Selenium (for handling dynamic JS-rendered airline sites).
*   **Data Storage:** SQLite (`flights.db`).
*   **Data Analysis & Visualization:** Pandas, Plotly Express, Plotly Graph Objects.
*   **Frontend (Dashboard):** HTML5, Vanilla CSS (with modern gradients and glassmorphism UI), Vanilla JavaScript.
*   **Server:** A lightweight Python web server (`serve_dashboard.py`) to handle live API requests for the calendar and advisor.

## 🚀 Getting Started

### Prerequisites

You need Python 3.10+ installed on your system.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Andre6553/FlightPriceTracker.git
    cd FlightPriceTracker
    ```

2.  **Create a Virtual Environment:**
    ```bash
    python -m venv venv
    ```

3.  **Activate the Environment:**
    *   Windows: `venv\Scripts\activate`
    *   macOS/Linux: `source venv/bin/activate`

4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Initialize Playwright (if applicable):**
    ```bash
    playwright install
    ```

## 🎮 Usage

### 1. Run the Scraper
To collect a fresh batch of data from the airline site, run:
```bash
python scraper.py
```
*(Tip: Set this up on a cron job or scheduled task to run every 1-2 hours for the best data resolution).*

### 2. Generate the Analytics
Once you have data in `flights.db`, analyze it and generate the dashboard charts:
```bash
python analyzer.py
```
This will create a `dashboard.html` file in the project root.

### 3. Start the Live Server
To use the Interactive Calendar and the Smart Flight Advisor, you must run the local server:
```bash
python serve_dashboard.py
```
Then, open your web browser and navigate to `http://localhost:8080` (or simply open the `dashboard.html` file, which will automatically attempt to connect to the local API).

## 🗂️ Project Structure

*   `scraper.py`: The automation script that visits the airline site and extracts prices.
*   `db_manager.py`: Handles all SQLite database interactions and query logic.
*   `analyzer.py`: The brain of the operation. Processes data via Pandas, generates Plotly charts, calculates volatility, and builds the UI.
*   `serve_dashboard.py`: Lightweight API backend for real-time dashboard features.
*   `dashboard.html`: The final, generated front-end application.
*   `flights.db`: (Generated) The SQLite database holding historical ticket records.

## 🤝 Contributing
Contributions, issues, and feature requests are welcome!

## 📝 License
This project is for educational and personal use. Please respect airline terms of service when scraping data.
