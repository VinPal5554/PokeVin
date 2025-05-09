from .models import PokemonPrice
from decimal import Decimal
from playwright.async_api import async_playwright
from asgiref.sync import sync_to_async
import re

@sync_to_async
def save_to_db(name, price):
    # Make sure this runs in a synchronous context
    card, created = PokemonPrice.objects.update_or_create(
        name=name,
        defaults={'price': price, 'source': 'eBay'}
    )
    return card

async def scrape_and_update_cards(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)

        try:
            # Wait for the title to appear
            await page.wait_for_selector('h1.x-item-title__mainTitle span.ux-textspans--BOLD', timeout=60000)

            # Extract card name (eBay listing title)
            raw_title = await page.locator('h1.x-item-title__mainTitle span.ux-textspans--BOLD').inner_text()
            name = raw_title.strip()

            # Extract price
            price_text = await page.locator("div.x-price-primary span.ux-textspans").first.inner_text()
            print(f"Raw price text: {price_text}")  # Debug: Print raw price text

            # Clean price (remove symbols and convert to Decimal)
            if price_text:
                price_text = re.sub(r'[^\d.]', '', price_text)  # Remove non-numeric characters
                print(f"Cleaned price text: {price_text}")  # Debug: Print cleaned price
                cleaned_price = Decimal(price_text)
            else:
                print("Price not found!")
                return  # Skip saving if price is missing

            # Save to database using sync_to_async
            await save_to_db(name, cleaned_price)
            print(f"Saved to DB: {name} - {cleaned_price}")

        except Exception as e:
            print(f"Error scraping {url}: {e}")

        finally:
            await browser.close()