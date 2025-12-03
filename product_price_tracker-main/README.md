# Price Tracker (Amazon + Flipkart)

A Python project using Playwright to track product prices on Amazon and Flipkart, 
send notifications, and generate reports with a modern web frontend.

## Features
- Track multiple products from Amazon & Flipkart
- Detect discounts vs original price
- Email notifications when discounts are available
- Modern web dashboard with charts and price history
- Real-time price tracking
- SQLite database for price history

## Setup

### Prerequisites
- Python 3.13+
- `uv` package manager (install with `pip install uv`)

### Installation
```bash
git clone https://github.com/username/price-tracker.git
cd price-tracker
uv sync
uv run playwright install
```

### Configuration
1. Copy `.env.example` to `.env`
2. Edit `.env` and add your Gmail credentials for email notifications:
   ```
   SENDER_EMAIL=your-email@gmail.com
   SENDER_PASSWORD=your-app-password
   RECEIVER_EMAIL=receiver-email@gmail.com
   ```
   > Note: Use Gmail App Password, not your regular password. Generate one at: https://myaccount.google.com/apppasswords

3. Edit `utils/products.csv` to add products you want to track:
   ```csv
   name,url,platform,threshold
   Product Name,https://amazon.in/product-url,amazon,5000
   ```

## Usage

### Web Dashboard (Recommended)
Start the Flask web server:
```bash
uv run python app.py
```

Then open your browser to: http://localhost:5000

The web dashboard provides:
- Real-time product price tracking
- Price history charts
- Discount detection and alerts
- Manual price refresh
- Product management interface

### Command Line
Run the scraper directly:
```bash
uv run python main.py
```

## Email Notifications

Emails are automatically sent when:
- Current price is **lower than original price** (discount detected)

Configure email settings in `.env` file.

## Project Structure
```
├── app.py                  # Flask web server
├── main.py                 # CLI entry point
├── static/                 # Frontend files
│   ├── index.html         # Dashboard HTML
│   ├── styles.css         # Dashboard styles
│   └── app.js             # Dashboard JavaScript
├── utils/
│   ├── products.csv       # Products to track
│   ├── scrape_amazon.py   # Amazon scraper
│   ├── scrape_flipkart.py # Flipkart scraper
│   ├── db.py              # Database functions
│   ├── email_reports.py   # Email functionality
│   └── common.py          # Shared utilities
└── price_tracker.db       # SQLite database (auto-created)
```

## License
MIT