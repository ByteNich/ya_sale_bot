"""Yandex Market parser module."""
import logging
import re
from typing import Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

from config import settings

logger = logging.getLogger(__name__)


class YandexMarketParser:
    """Parser for Yandex Market products."""

    BASE_URL = "https://market.yandex.ru"

    # Predefined category URLs
    CATEGORIES = {
        "smartphones": "/catalog--smartfony/26893750/list",
        "tv": "/catalog--televizory/90639/list",
        "laptops": "/catalog--noutbuki/54544/list",
        "tablets": "/catalog--planshety/54545/list",
        "headphones": "/catalog--naushniki-i-bluetooth-garnitury/54546/list",
        "smartwatches": "/catalog--umnye-chasy-i-braslety/56172/list",
        "cameras": "/catalog--tsifrovye-fotoapparaty/90561/list",
        "gaming_consoles": "/catalog--igrovye-pristavki/90594/list",
        "monitors": "/catalog--monitory/90783/list",
        "printers": "/catalog--printery/90592/list",
    }

    def __init__(self):
        """Initialize parser."""
        self.headers = {
            "User-Agent": settings.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    async def fetch_page(self, url: str) -> Optional[str]:
        """
        Fetch page content.

        Args:
            url: Page URL

        Returns:
            Page HTML content or None if error
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers, timeout=30) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.error(f"Failed to fetch {url}: status {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def parse_price(self, price_str: str) -> Optional[float]:
        """
        Parse price from string.

        Args:
            price_str: Price string (e.g., "12 990 ₽" or "12990")

        Returns:
            Price as float or None
        """
        if not price_str:
            return None

        # Remove all non-digit characters except comma and dot
        price_clean = re.sub(r"[^\d,.]", "", price_str)
        price_clean = price_clean.replace(",", ".")

        try:
            return float(price_clean)
        except (ValueError, AttributeError):
            return None

    async def parse_category_page(self, category_url: str, limit: int = 30) -> List[Dict]:
        """
        Parse category page and extract products.

        Args:
            category_url: Category URL path
            limit: Maximum number of products to parse

        Returns:
            List of product dictionaries
        """
        url = urljoin(self.BASE_URL, category_url)
        logger.info(f"Parsing category: {url}")

        html = await self.fetch_page(url)
        if not html:
            return []

        soup = BeautifulSoup(html, "lxml")
        products = []

        # Find product cards (this selector may need adjustment based on Yandex Market's current layout)
        # Note: Yandex Market changes their layout frequently, so selectors may need updates
        product_cards = soup.find_all("article", {"data-auto": "product-snippet"})

        if not product_cards:
            # Try alternative selectors
            product_cards = soup.find_all("div", class_=re.compile(r".*product.*snippet.*", re.I))

        logger.info(f"Found {len(product_cards)} product cards")

        for card in product_cards[:limit]:
            try:
                product = self._extract_product_info(card)
                if product:
                    products.append(product)
            except Exception as e:
                logger.error(f"Error parsing product card: {e}")
                continue

        logger.info(f"Successfully parsed {len(products)} products")
        return products

    def _extract_product_info(self, card) -> Optional[Dict]:
        """
        Extract product information from product card.

        Args:
            card: BeautifulSoup product card element

        Returns:
            Product dictionary or None
        """
        try:
            # Product name
            name_elem = card.find("h3", {"data-auto": "snippet-title"}) or card.find("a", {"data-auto": "snippet-link"})
            name = name_elem.get_text(strip=True) if name_elem else None

            # Product URL
            link_elem = card.find("a", {"data-auto": "snippet-link"})
            url = urljoin(self.BASE_URL, link_elem.get("href")) if link_elem else None

            # Extract product ID from URL
            product_id = None
            if url:
                match = re.search(r"/product--[^/]+/(\d+)", url)
                if match:
                    product_id = match.group(1)

            # Price
            price_elem = card.find("span", {"data-auto": "snippet-price-current"}) or card.find("span", class_=re.compile(r".*price.*current.*", re.I))
            price_str = price_elem.get_text(strip=True) if price_elem else None
            price = self.parse_price(price_str) if price_str else None

            # Old price (if discounted)
            old_price_elem = card.find("span", {"data-auto": "snippet-price-old"}) or card.find("del", class_=re.compile(r".*price.*old.*", re.I))
            old_price_str = old_price_elem.get_text(strip=True) if old_price_elem else None
            old_price = self.parse_price(old_price_str) if old_price_str else None

            # Calculate discount
            discount = 0
            if old_price and price and old_price > price:
                discount = round(((old_price - price) / old_price) * 100, 2)

            # Image
            img_elem = card.find("img", {"data-auto": "snippet-image"}) or card.find("img")
            image_url = img_elem.get("src") or img_elem.get("data-src") if img_elem else None

            # Rating
            rating_elem = card.find("div", {"data-auto": "rating-badge"})
            rating = None
            if rating_elem:
                rating_text = rating_elem.get_text(strip=True)
                rating_match = re.search(r"(\d+\.?\d*)", rating_text)
                if rating_match:
                    rating = float(rating_match.group(1))

            # Reviews count
            reviews_elem = card.find("span", {"data-auto": "reviews-count"})
            reviews_count = 0
            if reviews_elem:
                reviews_text = reviews_elem.get_text(strip=True)
                reviews_match = re.search(r"(\d+)", reviews_text.replace(" ", ""))
                if reviews_match:
                    reviews_count = int(reviews_match.group(1))

            if not name or not price or not url:
                return None

            return {
                "name": name,
                "yandex_product_id": product_id,
                "url": url,
                "current_price": price,
                "previous_price": old_price,
                "discount_percentage": discount,
                "image_url": image_url,
                "rating": rating,
                "reviews_count": reviews_count,
            }

        except Exception as e:
            logger.error(f"Error extracting product info: {e}")
            return None

    async def get_products_by_category(self, category_name: str, limit: int = 30) -> List[Dict]:
        """
        Get products from predefined category.

        Args:
            category_name: Category name (from CATEGORIES dict)
            limit: Maximum number of products

        Returns:
            List of product dictionaries
        """
        category_url = self.CATEGORIES.get(category_name)
        if not category_url:
            logger.error(f"Unknown category: {category_name}")
            return []

        return await self.parse_category_page(category_url, limit)

    @classmethod
    def get_available_categories(cls) -> Dict[str, str]:
        """
        Get available predefined categories.

        Returns:
            Dictionary of category names and URLs
        """
        return cls.CATEGORIES.copy()
