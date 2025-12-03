"""Flask API server for Price Tracker frontend."""

import asyncio
from threading import Thread

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from utils import playwright_price_scraper
from utils.common import fetch_products
from utils.db import get_price_history, get_product_summary, init_db

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Initialize database on startup
init_db()

# Scheduler for automatic price scraping every 30 minutes
scheduler = BackgroundScheduler(daemon=True)

def run_scrape_job():
    """Background job to run price scraping."""
    try:
        asyncio.run(playwright_price_scraper.track_prices())
    except Exception as e:
        print(f"Error in scheduled scrape: {e}")

# Schedule scraping every 30 minutes
scheduler.add_job(
    func=run_scrape_job,
    trigger="interval",
    minutes=30,
    id='price_scrape_job',
    name='Scrape prices every 30 minutes',
    replace_existing=True
)

# Start scheduler
scheduler.start()
print("Scheduler started - Price scraping will run every 30 minutes")

# Run initial scrape on startup (after a short delay)
import time
def initial_scrape():
    """Run initial scrape after server starts."""
    time.sleep(5)  # Wait 5 seconds for server to fully start
    print("Running initial price scrape...")
    run_scrape_job()

initial_thread = Thread(target=initial_scrape, daemon=True)
initial_thread.start()


@app.route("/")
def index():
    """Serve the frontend HTML."""
    return send_from_directory('static', 'index.html')


@app.route("/api/products", methods=["GET"])
def get_products():
    """Get list of products being tracked."""
    try:
        products = fetch_products()
        return jsonify({"success": True, "data": products})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/products", methods=["POST"])
def add_product():
    """Add a new product to products.csv."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ["name", "url", "platform", "threshold"]
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400
        
        # Validate platform
        platform = data["platform"].lower()
        if platform not in ["amazon", "flipkart"]:
            return jsonify({"success": False, "error": "Platform must be 'amazon' or 'flipkart'"}), 400
        
        # Validate threshold
        try:
            threshold = float(data["threshold"])
            if threshold <= 0:
                return jsonify({"success": False, "error": "Threshold must be greater than 0"}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Threshold must be a valid number"}), 400
        
        # Validate URL contains platform
        url = data["url"].lower()
        if platform not in url:
            return jsonify({"success": False, "error": f"URL must be from {platform}"}), 400
        
        # Read existing products
        products = fetch_products()
        
        # Check if product already exists
        for product in products:
            if product["name"].lower() == data["name"].lower():
                return jsonify({"success": False, "error": "Product with this name already exists"}), 400
        
        # Add new product to CSV
        import csv
        from utils.config import PRODUCTS_FILE
        
        with open(PRODUCTS_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                data["name"],
                data["url"],
                platform,
                threshold
            ])
        
        return jsonify({
            "success": True,
            "message": "Product added successfully",
            "data": {
                "name": data["name"],
                "url": data["url"],
                "platform": platform,
                "threshold": threshold
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/products/<product_name>", methods=["DELETE"])
def delete_product(product_name):
    """Delete a product from products.csv."""
    try:
        import csv
        from utils.config import PRODUCTS_FILE
        
        # Read all products
        products = fetch_products()
        
        # Check if product exists
        product_found = False
        for product in products:
            if product["name"].lower() == product_name.lower():
                product_found = True
                break
        
        if not product_found:
            return jsonify({"success": False, "error": "Product not found"}), 404
        
        # Write all products except the one to delete
        with open(PRODUCTS_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["name", "url", "platform", "threshold"])  # Header
            
            for product in products:
                if product["name"].lower() != product_name.lower():
                    writer.writerow([
                        product["name"],
                        product["url"],
                        product["platform"],
                        product["threshold"]
                    ])
        
        return jsonify({
            "success": True,
            "message": f"Product '{product_name}' deleted successfully"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/products/summary", methods=["GET"])
def get_products_summary():
    """Get summary of all products with latest prices, merged with products.csv."""
    try:
        # Get products from CSV (source of truth)
        csv_products = fetch_products()
        # Get price history from database
        db_summary = get_product_summary()
        
        # Create a dictionary of database data by product name
        db_dict = {item['name']: item for item in db_summary}
        
        # Merge CSV products with database data
        merged_products = []
        for csv_product in csv_products:
            product_name = csv_product['name']
            if product_name in db_dict:
                # Product exists in database, merge data
                db_product = db_dict[product_name]
                merged_products.append({
                    'name': csv_product['name'],
                    'url': csv_product['url'],
                    'platform': csv_product['platform'],
                    'threshold': csv_product['threshold'],
                    'current_price': db_product.get('current_price', 0),
                    'original_price': db_product.get('original_price', csv_product['threshold']),
                    'previous_price': db_product.get('previous_price'),
                    'price_change': db_product.get('price_change'),
                    'price_change_percent': db_product.get('price_change_percent'),
                    'last_updated': db_product.get('last_updated')
                })
            else:
                # Product not yet scraped, show from CSV only
                merged_products.append({
                    'name': csv_product['name'],
                    'url': csv_product['url'],
                    'platform': csv_product['platform'],
                    'threshold': csv_product['threshold'],
                    'current_price': None,
                    'original_price': None,
                    'previous_price': None,
                    'price_change': None,
                    'price_change_percent': None,
                    'last_updated': None
                })
        
        return jsonify({"success": True, "data": merged_products})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/prices/history", methods=["GET"])
def get_price_history_endpoint():
    """Get price history for a specific product or all products."""
    try:
        name = request.args.get("name")
        limit = int(request.args.get("limit", 100))
        
        history = get_price_history(name=name, limit=limit)
        return jsonify({"success": True, "data": history})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/scrape", methods=["POST"])
def trigger_scrape():
    """Manually trigger a price scraping operation."""
    try:
        # Run scraping in background thread to avoid blocking
        def run_scrape():
            asyncio.run(playwright_price_scraper.track_prices())
        
        thread = Thread(target=run_scrape, daemon=True)
        thread.start()
        
        return jsonify({
            "success": True,
            "message": "Price scraping started in background"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"success": True, "status": "healthy"})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

