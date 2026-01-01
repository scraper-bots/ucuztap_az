#!/usr/bin/env python3
"""
Web scraper for ucuztap.az real estate listings
Crash-proof version with incremental saves and resume capability
"""

import asyncio
import aiohttp
import csv
import json
import os
import re
import signal
import sys
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Set
from datetime import datetime
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CrashProofScraper:
    """Crash-proof scraper with incremental saves and resume capability"""

    def __init__(
        self,
        max_concurrent_requests: int = 50,
        delay_between_requests: float = 0.1,
        batch_size: int = 10,
        progress_dir: str = ".scraper_progress"
    ):
        """
        Initialize the crash-proof scraper

        Args:
            max_concurrent_requests: Maximum number of concurrent HTTP requests
            delay_between_requests: Delay in seconds between requests
            batch_size: Number of listings to scrape before saving
            progress_dir: Directory to store progress files
        """
        self.base_url = "https://ucuztap.az"
        self.max_concurrent_requests = max_concurrent_requests
        self.delay_between_requests = delay_between_requests
        self.batch_size = batch_size
        self.progress_dir = Path(progress_dir)
        self.semaphore = asyncio.Semaphore(max_concurrent_requests)
        self.session: Optional[aiohttp.ClientSession] = None

        # Progress tracking
        self.progress_file = self.progress_dir / "progress.json"
        self.scraped_urls: Set[str] = set()
        self.all_data: List[Dict[str, str]] = []

        # Shutdown flag
        self.should_shutdown = False

        # Create progress directory
        self.progress_dir.mkdir(exist_ok=True)

        # Load existing progress
        self._load_progress()

        # Setup signal handlers
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.warning(f"Received signal {signum}. Initiating graceful shutdown...")
            self.should_shutdown = True

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def _load_progress(self):
        """Load progress from previous run"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)
                    self.scraped_urls = set(progress_data.get('scraped_urls', []))
                    logger.info(f"Loaded progress: {len(self.scraped_urls)} URLs already scraped")
            except Exception as e:
                logger.error(f"Error loading progress: {e}")
                # Backup corrupted progress file
                if self.progress_file.exists():
                    backup_path = self.progress_file.with_suffix('.json.backup')
                    self.progress_file.rename(backup_path)
                    logger.info(f"Backed up corrupted progress file to {backup_path}")

    def _save_progress(self):
        """Save current progress to file (atomic write)"""
        try:
            progress_data = {
                'scraped_urls': list(self.scraped_urls),
                'last_updated': datetime.now().isoformat(),
                'total_scraped': len(self.scraped_urls)
            }

            # Write to temporary file first (atomic write)
            temp_file = self.progress_file.with_suffix('.json.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2, ensure_ascii=False)

            # Rename to actual file (atomic operation on most filesystems)
            temp_file.replace(self.progress_file)
            logger.debug(f"Progress saved: {len(self.scraped_urls)} URLs")
        except Exception as e:
            logger.error(f"Error saving progress: {e}")

    def _save_data_incremental(self, filename: str, append: bool = True):
        """
        Save data incrementally to CSV file

        Args:
            filename: Output CSV filename
            append: Whether to append to existing file
        """
        if not self.all_data:
            return

        try:
            file_exists = Path(filename).exists()
            mode = 'a' if (append and file_exists) else 'w'

            # Get all unique keys
            fieldnames = sorted(set().union(*[d.keys() for d in self.all_data]))

            # Use temporary file for atomic write
            temp_file = Path(filename).with_suffix('.csv.tmp')

            if mode == 'w':
                # Write entire file
                with open(temp_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self.all_data)

                # Atomic rename
                temp_file.replace(filename)
                logger.info(f"Saved {len(self.all_data)} listings to {filename}")
            else:
                # Append mode - write directly to avoid reading entire file
                with open(filename, 'a', newline='', encoding='utf-8-sig') as csvfile:
                    # Get fieldnames from existing file
                    if file_exists:
                        with open(filename, 'r', encoding='utf-8-sig') as f:
                            reader = csv.DictReader(f)
                            existing_fieldnames = reader.fieldnames or []
                    else:
                        existing_fieldnames = []

                    # Merge fieldnames
                    all_fieldnames = sorted(set(existing_fieldnames) | set(fieldnames))

                    writer = csv.DictWriter(csvfile, fieldnames=all_fieldnames)

                    # Write header if file is empty
                    if not file_exists or csvfile.tell() == 0:
                        writer.writeheader()

                    # Write new data only (data since last save)
                    writer.writerows(self.all_data)

                logger.info(f"Appended {len(self.all_data)} new listings to {filename}")

                # IMPORTANT: Clear all_data after successful append to prevent duplicates
                self.all_data = []

        except Exception as e:
            logger.error(f"Error saving data: {e}")
            # Try to save to backup file
            backup_file = Path(filename).with_suffix('.csv.backup')
            try:
                with open(backup_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
                    fieldnames = sorted(set().union(*[d.keys() for d in self.all_data]))
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self.all_data)
                logger.info(f"Saved backup to {backup_file}")
            except Exception as backup_error:
                logger.error(f"Failed to save backup: {backup_error}")

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def fetch_page(self, url: str, max_retries: int = 3) -> Optional[str]:
        """
        Fetch a page with rate limiting, error handling, and retries

        Args:
            url: URL to fetch
            max_retries: Maximum number of retry attempts

        Returns:
            HTML content or None if error
        """
        async with self.semaphore:
            for attempt in range(max_retries):
                try:
                    await asyncio.sleep(self.delay_between_requests)
                    async with self.session.get(url, timeout=30) as response:
                        if response.status == 200:
                            return await response.text()
                        elif response.status == 500:
                            logger.warning(f"Server error (500) for {url}")
                            return None
                        else:
                            logger.warning(f"Failed to fetch {url}: Status {response.status}")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                                continue
                            return None
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return None
                except Exception as e:
                    logger.error(f"Error fetching {url}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return None
            return None

    def extract_listing_urls(self, html: str) -> List[str]:
        """Extract listing URLs from a listings page"""
        soup = BeautifulSoup(html, 'html.parser')
        urls = []

        listings = soup.find_all('section', class_='thumbnail i-product')
        for listing in listings:
            link = listing.find('a', href=True)
            if link and '/elan/' in link['href']:
                url = link['href']
                if not url.startswith('http'):
                    url = self.base_url + url
                urls.append(url)

        return urls

    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text).strip()

    def extract_price(self, html: str) -> Dict[str, str]:
        """Extract price information"""
        soup = BeautifulSoup(html, 'html.parser')
        price_data = {"price": "", "price_numeric": ""}

        # Fixed: use 'btn-price' instead of 'btn btn-price' to match any element with this class
        price_elem = soup.find('button', class_='btn-price')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price_data["price"] = self.clean_text(price_text)

            numbers = re.findall(r'[\d\s]+', price_text.replace(' ', ''))
            if numbers:
                price_data["price_numeric"] = ''.join(numbers).strip()

        return price_data

    def extract_details_table(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract details from the details table"""
        details = {}

        table = soup.find('table', class_='table')
        if table:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) == 2:
                    key = self.clean_text(cells[0].get_text())
                    value = self.clean_text(cells[1].get_text())
                    key = key.replace(':', '').strip()
                    details[key] = value

        return details

    def extract_seller_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract seller information"""
        seller_info = {"seller_name": "", "seller_phones": ""}

        seller_name_elem = soup.find('h3', class_='m-t-1')
        if seller_name_elem:
            seller_info["seller_name"] = self.clean_text(seller_name_elem.get_text())

        phones = []
        phone_section = soup.find('div', class_='i-shop-listNumber')
        if phone_section:
            phone_elements = phone_section.find_all('strong', class_='fs-20')
            for phone_elem in phone_elements:
                phone_text = self.clean_text(phone_elem.get_text())
                if phone_text:
                    phones.append(phone_text)

        seller_info["seller_phones"] = "; ".join(phones)
        return seller_info

    def extract_location_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract location and view information"""
        location_info = {"location": "", "view_count": "", "date_posted": ""}

        stats_section = soup.find('div', class_='color-9e9e9e')
        if stats_section:
            spans = stats_section.find_all('span')
            for span in spans:
                text = self.clean_text(span.get_text())

                if 'dəfə' in text:
                    location_info["view_count"] = text
                elif 'i-profile-statsBorder' in span.get('class', []):
                    if 'dəfə' not in text:
                        location_info["date_posted"] = text
                else:
                    if text and not any(x in text for x in ['dəfə', 'həftə', 'Bu həftə']):
                        location_info["location"] = text

        return location_info

    async def extract_listing_details(self, url: str) -> Optional[Dict[str, str]]:
        """Extract detailed information from a listing page"""
        try:
            html = await self.fetch_page(url)
            if not html:
                return None

            soup = BeautifulSoup(html, 'html.parser')

            data = {
                "url": url,
                "listing_id": "",
                "title": "",
                "category": "",
                "price": "",
                "price_numeric": "",
                "area_m2": "",
                "room_count": "",
                "district": "",
                "location_area": "",
                "listing_number": "",
                "description": "",
                "seller_name": "",
                "seller_phones": "",
                "location": "",
                "view_count": "",
                "date_posted": "",
                "images_count": "",
                "scraped_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            id_elem = soup.find('div', class_='txt-right')
            if id_elem and '#' in id_elem.get_text():
                data["listing_id"] = self.clean_text(id_elem.get_text()).replace('#', '')

            title_elem = soup.find('h1', {'data-check': 'false'})
            if title_elem:
                data["title"] = self.clean_text(title_elem.get_text())

            category_elem = soup.find('a', class_='fs-15 f-light color-313131 txt-underline')
            if category_elem:
                data["category"] = self.clean_text(category_elem.get_text())

            price_data = self.extract_price(html)
            data.update(price_data)

            details = self.extract_details_table(soup)
            data["area_m2"] = details.get("Sahə, m²", "")
            data["room_count"] = details.get("Otaq sayı", "")
            data["district"] = details.get("Rayon", "")
            data["location_area"] = details.get("Ərazi", "")
            data["listing_number"] = details.get("Elanın nömrəsi", "")

            desc_elem = soup.find('h2', class_='fs-15 m-t-1 f-w-50')
            if desc_elem:
                data["description"] = self.clean_text(desc_elem.get_text())

            seller_info = self.extract_seller_info(soup)
            data.update(seller_info)

            location_info = self.extract_location_info(soup)
            data.update(location_info)

            images = soup.find_all('a', {'data-carousel': 'carousel'})
            data["images_count"] = str(len(images))

            logger.info(f"Extracted listing: {data['listing_id']} - {data['title'][:50]}")
            return data

        except Exception as e:
            logger.error(f"Error extracting details from {url}: {e}")
            return None

    async def scrape_page(self, page_num: int) -> List[str]:
        """Scrape a single listings page"""
        url = f"{self.base_url}/dasinmaz-emlak/?page={page_num}"
        logger.info(f"Scraping page {page_num}: {url}")

        html = await self.fetch_page(url)
        if html:
            urls = self.extract_listing_urls(html)
            logger.info(f"Found {len(urls)} listing URLs on page {page_num}")
            return urls
        return []

    async def scrape_all_pages(self, start_page: int = 1, end_page: int = 10) -> List[str]:
        """Scrape multiple pages to collect all listing URLs"""
        tasks = [self.scrape_page(page) for page in range(start_page, end_page + 1)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_urls = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Error scraping page: {result}")
                continue
            all_urls.extend(result)

        all_urls = list(set(all_urls))
        logger.info(f"Total unique listings found: {len(all_urls)}")
        return all_urls

    async def scrape_listings_batch(
        self,
        urls: List[str],
        output_file: str,
        append_mode: bool = False
    ) -> int:
        """
        Scrape listings in batches with incremental saves

        Args:
            urls: List of listing URLs to scrape
            output_file: Output CSV filename
            append_mode: Whether to append to existing file

        Returns:
            Number of successfully scraped listings
        """
        # Filter out already scraped URLs
        urls_to_scrape = [url for url in urls if url not in self.scraped_urls]

        if not urls_to_scrape:
            logger.info("All URLs already scraped. Nothing to do.")
            return 0

        logger.info(f"Scraping {len(urls_to_scrape)} new URLs (skipping {len(urls) - len(urls_to_scrape)} already scraped)")

        total_scraped = 0
        batch_data = []

        for i, url in enumerate(urls_to_scrape):
            # Check for shutdown signal
            if self.should_shutdown:
                logger.warning("Shutdown requested. Saving progress and exiting...")
                # Save remaining batch data
                if batch_data:
                    self.all_data.extend(batch_data)
                    self._save_data_incremental(output_file, append=True)
                    self._save_progress()
                break

            try:
                listing_data = await self.extract_listing_details(url)

                if listing_data:
                    batch_data.append(listing_data)
                    self.scraped_urls.add(url)
                    total_scraped += 1

                # Save batch when batch_size is reached
                if len(batch_data) >= self.batch_size:
                    self.all_data.extend(batch_data)
                    self._save_data_incremental(output_file, append=(append_mode or i > 0))
                    self._save_progress()
                    logger.info(f"Batch saved: {len(batch_data)} listings. Total: {total_scraped}/{len(urls_to_scrape)}")
                    batch_data = []  # Clear batch after saving

            except Exception as e:
                logger.error(f"Error processing {url}: {e}")
                continue

        # Save any remaining data
        if batch_data:
            self.all_data.extend(batch_data)
            self._save_data_incremental(output_file, append=True)
            self._save_progress()
            logger.info(f"Final batch saved: {len(batch_data)} listings")

        return total_scraped


async def main():
    """Main function to run the crash-proof scraper"""

    # Configuration
    START_PAGE = 1
    END_PAGE = 398  # Adjust this to scrape more pages
    OUTPUT_FILE = "ucuztap_listings.csv"
    BATCH_SIZE = 10  # Save after every 10 listings
    PROGRESS_DIR = ".scraper_progress"

    logger.info("=" * 70)
    logger.info("Starting crash-proof ucuztap.az scraper...")
    logger.info("=" * 70)
    logger.info(f"Configuration:")
    logger.info(f"  - Pages: {START_PAGE} to {END_PAGE}")
    logger.info(f"  - Output file: {OUTPUT_FILE}")
    logger.info(f"  - Batch size: {BATCH_SIZE}")
    logger.info(f"  - Progress directory: {PROGRESS_DIR}")
    logger.info("=" * 70)

    try:
        async with CrashProofScraper(
            max_concurrent_requests=15,
            delay_between_requests=0.3,
            batch_size=BATCH_SIZE,
            progress_dir=PROGRESS_DIR
        ) as scraper:
            # Step 1: Collect all listing URLs
            logger.info(f"Collecting listing URLs from pages {START_PAGE} to {END_PAGE}...")
            all_urls = await scraper.scrape_all_pages(start_page=START_PAGE, end_page=END_PAGE)

            if not all_urls:
                logger.warning("No URLs found. Exiting.")
                return

            # Step 2: Scrape listings in batches with incremental saves
            logger.info(f"Starting batch scraping of {len(all_urls)} listings...")
            scraped_count = await scraper.scrape_listings_batch(
                urls=all_urls,
                output_file=OUTPUT_FILE,
                append_mode=False
            )

            logger.info("=" * 70)
            logger.info("Scraping completed!")
            logger.info(f"Successfully scraped: {scraped_count} listings")
            logger.info(f"Results saved to: {OUTPUT_FILE}")
            logger.info(f"Progress saved to: {scraper.progress_file}")
            logger.info("=" * 70)

    except KeyboardInterrupt:
        logger.warning("Interrupted by user. Progress has been saved.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
