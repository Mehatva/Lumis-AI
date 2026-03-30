"""
Scraper Service — Extracts and cleans text from public websites.
"""
import requests
from bs4 import BeautifulSoup
import re

class ScraperService:
    @staticmethod
    def scrape_url(url: str) -> str:
        """
        Fetches the URL and extracts text content, stripping HTML tags.
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            # Limit length to avoid token issues (e.g., first 10k chars)
            return text[:10000]

        except Exception as e:
            print(f"[ScraperService] Error scraping {url}: {e}")
            return ""
