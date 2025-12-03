import statistics

from utils.common import console

DEBUG = False


async def scrape_flipkart(url, page) -> tuple[float, float] | None:
    try:
        await page.goto(url, wait_until="networkidle")

        elements = page.locator("xpath=//*[contains(text(),'₹')]")
        count = await elements.count()

        prices = []
        for i in range(count):
            text = (await elements.nth(i).inner_text()).strip()
            if not text:
                continue

            # Skip unwanted text
            lowered = text.lower()
            if any(
                skip in lowered
                for skip in [
                    "month",
                    "emi",
                    "delivery",
                    "fee",
                    "off",
                    "save",
                    "protect",
                    "promise",
                    "cashback",
                    "card",
                    "upto",
                    "quarter",
                ]
            ):
                continue
            if text.startswith("+") or "up to" in lowered:
                continue

            import re

            match = re.search(r"₹\s?([\d,]+(?:\.\d{1,2})?)", text)
            if match:
                price = float(match.group(1).replace(",", ""))
                prices.append((price, text))

        if not prices:
            console.print("No prices found on Flipkart page.")
            return None

        values = [p for p, _ in prices]

        import collections

        # Outlier filtering: remove prices far below median
        median_val = statistics.median(values)
        cutoff = 0.7 * median_val
        filtered = [(p, t) for p, t in prices if p >= cutoff]

        if not filtered:
            filtered = prices  # fallback

        values_only = [p for p, _ in filtered]

        # Pick the most frequent price as current (mode)
        counter = collections.Counter(values_only)
        current_price = counter.most_common(1)[0][0]

        # Original = max price > current
        larger_prices = [p for p in values_only if p > current_price]
        original_price = max(larger_prices) if larger_prices else current_price

        if DEBUG:
            console.print("\nDEBUG - ")
            console.print("All captured prices:", prices)
            console.print("Filtered prices:", filtered)
            console.print("Median value:", median_val)
            console.print("Current price:", current_price, "| Original price:", original_price)

        return current_price, original_price

    except Exception as e:
        console.print(f"Error scraping Flipkart: {e}")
        return None
