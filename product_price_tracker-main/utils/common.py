# utils/common.py
"""Shared Rich console for pretty output across the project."""

# ruff: noqa: BLE001
import csv
import traceback
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from rich.console import Console
from rich.table import Table

from .config import PRODUCTS_FILE

console = Console()

P = ParamSpec("P")
R = TypeVar("R")

def safe_run(func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R | None:
    """Run a function safely.

    Returns the result of the function or None if any error occurs.

    Exceptions are logged to the console with traceback.
    """
    try:
        return func(*args, **kwargs)
    except BaseException as e:  # Broad catch, safe fallback
        console.print("[red]Unexpected error:[/]", e)
        console.print(traceback.format_exc())
        return None

def fetch_products() -> list[dict]:
    """Fetch product list from products.py."""
    try:
        products = []
        # Read products from CSV
        with open(PRODUCTS_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=2):  # start=2 because row 1 is header
                try:
                    # Clean and validate threshold value
                    threshold_str = str(row.get("threshold", "")).strip()
                    # Remove any non-numeric characters except decimal point
                    import re
                    threshold_clean = re.sub(r'[^\d.]', '', threshold_str)
                    
                    if not threshold_clean:
                        console.print(f"[yellow]Warning: Invalid threshold in row {row_num}, skipping product[/]")
                        continue
                    
                    threshold = float(threshold_clean)
                    
                    # Validate other fields
                    if not row.get("name") or not row.get("url"):
                        console.print(f"[yellow]Warning: Missing name or URL in row {row_num}, skipping[/]")
                        continue
                    
                    products.append({
                        "name": row["name"].strip(),
                        "url": row["url"].strip(),
                        "platform": row.get("platform", "").lower().strip(),
                        "threshold": threshold,
                    })
                except (ValueError, KeyError) as e:
                    console.print(f"[red]Error parsing row {row_num}:[/] {e}")
                    console.print(f"[red]Row data:[/] {row}")
                    continue
    except FileNotFoundError:
        console.print("[red]Error: products.csv file not found[/]")
        return []
    except Exception as e:
        console.print("[red]Error importing PRODUCTS:[/]", e)
        return []
    return products

def display_price_table(results: list[dict]) -> None:
    """Display price tracker results in a Rich table.

    Each item in results should have:
    - name: str
    - current_price: float
    - original_price: float
    """
    table = Table(title="Price Tracker Results")

    table.add_column("Product", style="bold cyan", no_wrap=True)
    table.add_column("Current Price (Rs)", justify="right", style="green")
    table.add_column("Desired Price (Rs)", justify="right", style="yellow")
    table.add_column("Discount (%)", justify="right", style="magenta")

    # Remove duplicates by product name (keep the first occurrence)
    seen_products = set()
    unique_results = []
    for item in results:
        name = item.get("name", "Unknown")
        if name not in seen_products:
            seen_products.add(name)
            unique_results.append(item)

    for item in unique_results:
        name = item.get("name", "Unknown")
        current = item.get("current_price", 0)
        desired = item.get("threshold", 0)
        original = item.get("original_price", 0)
        discount = 0
        if original > 0:
            discount = round((original - current) / original * 100, 2)
        table.add_row(name, f"{current:.2f}", f"{desired:.2f}", f"{discount:.2f}%")

    console.print(table)
