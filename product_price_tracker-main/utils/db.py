"""SQLite helpers for storing price history."""

import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("price_tracker.db")

def init_db() -> None:
    """Initialize the SQLite database and create tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            url TEXT,
            platform TEXT,
            price REAL,
            original_price REAL,
            threshold REAL,
            date TIMESTAMP
        )
    """)
    # Add original_price column if it doesn't exist (for existing databases)
    try:
        c.execute("ALTER TABLE price_history ADD COLUMN original_price REAL")
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.commit()
    conn.close()

def save_price(name: str, url: str, platform: str, price: float, threshold: float, original_price: float = None) -> None:
    """Save a price entry to the database.
    
    Args:
        name: Product name
        url: Product URL
        platform: Platform (amazon/flipkart)
        price: Current price
        threshold: Price threshold
        original_price: Original price (if None, will use max price from history)
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # If original_price not provided, get max price from history for this product
    if original_price is None:
        c.execute("""
            SELECT MAX(price) FROM price_history WHERE name = ?
        """, (name,))
        max_price = c.fetchone()[0]
        original_price = max_price if max_price and max_price > price else price
    
    c.execute("""
        INSERT INTO price_history (name, url, platform, price, original_price, threshold, date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, url, platform, price, original_price, threshold, datetime.now()))
    conn.commit()
    conn.close()

def get_latest_prices() -> list[tuple]:
    """Retrieve the latest price entries from the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT name, price, threshold, date
        FROM price_history
        ORDER BY date DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows

def get_price_history(name: str = None, limit: int = 100) -> list[dict]:
    """Retrieve price history from the database.
    
    Args:
        name: Optional product name to filter by
        limit: Maximum number of records to return
    
    Returns:
        List of dictionaries with price history data
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    if name:
        c.execute("""
            SELECT id, name, url, platform, price, original_price, threshold, date
            FROM price_history
            WHERE name = ?
            ORDER BY date DESC
            LIMIT ?
        """, (name, limit))
    else:
        c.execute("""
            SELECT id, name, url, platform, price, original_price, threshold, date
            FROM price_history
            ORDER BY date DESC
            LIMIT ?
        """, (limit,))
    
    rows = c.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_product_summary() -> list[dict]:
    """Get summary of all products with their latest prices."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Get latest price for each product (ensure unique by name)
    c.execute("""
        SELECT DISTINCT 
            ph1.name, 
            ph1.url, 
            ph1.platform, 
            ph1.price as current_price, 
            ph1.original_price, 
            ph1.threshold, 
            ph1.date,
            (SELECT price FROM price_history ph2 
             WHERE ph2.name = ph1.name 
             ORDER BY date DESC LIMIT 1 OFFSET 1) as previous_price
        FROM price_history ph1
        INNER JOIN (
            SELECT name, MAX(date) as max_date
            FROM price_history 
            GROUP BY name
        ) latest ON ph1.name = latest.name AND ph1.date = latest.max_date
        ORDER BY ph1.name
    """)
    
    rows = c.fetchall()
    conn.close()
    
    # Use a dictionary to ensure unique products by name (in case of duplicates)
    products_dict = {}
    for row in rows:
        data = dict(row)
        current_price = data['current_price']
        previous_price = data.get('previous_price')
        # Use stored original_price or fallback to current_price
        original_price = data.get('original_price') or current_price
        
        if previous_price:
            price_change = current_price - previous_price
            price_change_percent = ((current_price - previous_price) / previous_price) * 100
        else:
            price_change = None
            price_change_percent = None
        
        product_name = data['name']
        # Keep only the first entry for each product name (should already be unique from SQL)
        if product_name not in products_dict:
            products_dict[product_name] = {
                'name': product_name,
                'url': data['url'],
                'platform': data['platform'],
                'current_price': current_price,
                'original_price': original_price,
                'threshold': data['threshold'],
                'previous_price': previous_price,
                'price_change': price_change,
                'price_change_percent': price_change_percent,
                'last_updated': data['date']
            }
    
    return list(products_dict.values())