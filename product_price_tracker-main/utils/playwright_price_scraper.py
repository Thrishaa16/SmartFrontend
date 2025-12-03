import asyncio

from playwright.async_api import Page, async_playwright

from utils.common import console, display_price_table, fetch_products
from utils.db import init_db, save_price

from .email_reports import send_report
from .scrape_amazon import scrape_amazon
from .scrape_flipkart import scrape_flipkart

CHECK_INTERVAL = 60 * 60  # check every 1 hour



async def scrape_product(page:Page, product:dict) -> dict | None:
    """Scrape price info for Amazon or Flipkart product."""
    url = product["url"]

    current_price, original_price, discount = 10e9, 10e9, 0.0

    if "amazon" in url:
        amazon_scraped_prices = await scrape_amazon(url, page)
        if amazon_scraped_prices is None:
            return None
        current_price, original_price = amazon_scraped_prices

    elif "flipkart" in url:
        flipkart_scraped_prices = await scrape_flipkart(url, page)
        console.print(f"{flipkart_scraped_prices=}")
        if flipkart_scraped_prices is None:
            return None
        current_price, original_price = flipkart_scraped_prices

    discount = (
        round(((original_price - current_price) / original_price) * 100, 2)
        if original_price > current_price
        else 0
    )
    # Send email only if there is a real discount AND price meets threshold
    send_email = (current_price < original_price) and (
        current_price <= product["threshold"]
    )

    status = "[OK] Threshold & Discount Met"
    if not send_email:
        if current_price > product["threshold"]:
            diff = current_price - product["threshold"]
            status = f"[X] Above threshold by Rs {diff:.2f}"
        else:
            status = "[X] No Email (no discount)"

    return {
        "name": product["name"],
        "url": url,
        "current_price": current_price,
        "original_price": original_price,
        "discount": discount,
        "threshold": product["threshold"],
        "status": status,
        "send_email": send_email,
    }


async def track_prices() -> None:
    """Launch Playwright and track all products."""
    products = fetch_products()
    if not products:
        console.print("No products to track. Please add products to the PRODUCTS list.")
        return
    results = report_details = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            #                               ,proxy={
            #     "server": "socks5://127.0.0.1:9050"
            # }
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        for product in products:
            info = await scrape_product(page, product)
            if info:
                results.append(info)
                current_price = info["current_price"]
                console.print(
                    f"[cyan]{product['name']}[/] => Rs {current_price} (Threshold Rs {product['threshold']})",
                )

                # Save price to DB with original_price
                save_price(
                    product["name"],
                    product["url"],
                    product["platform"],
                    current_price,
                    product["threshold"],
                    info["original_price"],
                )
                # Check if there is a real discount AND price meets threshold for email notification
                if (current_price < info["original_price"]) and (
                    current_price <= product["threshold"]
                ):
                    report_details.append(info)
            else:
                console.print(f"[X] Failed to fetch price for {product['name']}")

        await browser.close()

    if results:
        display_price_table(results)

    # Ensure we only email when items still satisfy discount condition
    eligible_reports = [
        item
        for item in report_details
        if (item["current_price"] < item["original_price"])
        and (item["current_price"] <= item["threshold"])
    ]

    if eligible_reports:
        send_report(eligible_reports)
    else:
        console.print("[yellow]No products met discount + threshold criteria. Skipping email.")


async def main() -> None:
    """Start the price tracking process."""
    init_db()
    await track_prices()


if __name__ == "__main__":
    asyncio.run(track_prices())
    # while True:
    #     time.sleep(CHECK_INTERVAL)
