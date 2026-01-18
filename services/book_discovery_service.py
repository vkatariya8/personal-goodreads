"""
Book Discovery Service
Integrates with Open Library API to discover new books for recommendations.
"""

import requests
import time
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class BookDiscoveryService:
    """
    Service for discovering books via Open Library API.
    Implements rate limiting and error handling for respectful API usage.
    """

    BASE_URL = "https://openlibrary.org"
    RATE_LIMIT_DELAY = 0.5  # 0.5 seconds between requests
    REQUEST_TIMEOUT = 10  # seconds
    MAX_RETRIES = 3

    def __init__(self):
        self.last_request_time = 0

    def _rate_limit(self):
        """Implement rate limiting to respect API guidelines"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self.last_request_time = time.time()

    def _make_api_request(self, url: str, params: Optional[Dict] = None, retries: int = 0) -> Optional[Dict]:
        """
        Make an API request with rate limiting, error handling, and retries.

        Args:
            url: The API endpoint URL
            params: Query parameters
            retries: Current retry attempt

        Returns:
            JSON response as dictionary, or None if request failed
        """
        self._rate_limit()

        try:
            logger.debug(f"Making API request to: {url} with params: {params}")
            response = requests.get(
                url,
                params=params,
                timeout=self.REQUEST_TIMEOUT,
                headers={'User-Agent': 'PersonalGoodreads/1.0 (Educational Project)'}
            )

            if response.status_code == 429:  # Too Many Requests
                if retries < self.MAX_RETRIES:
                    wait_time = (2 ** retries) * self.RATE_LIMIT_DELAY  # Exponential backoff
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry {retries + 1}/{self.MAX_RETRIES}")
                    time.sleep(wait_time)
                    return self._make_api_request(url, params, retries + 1)
                else:
                    logger.error(f"Max retries exceeded for URL: {url}")
                    return None

            response.raise_for_status()
            return response.json()

        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for URL: {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for URL: {url}. Error: {e}")
            if retries < self.MAX_RETRIES:
                time.sleep(self.RATE_LIMIT_DELAY * (retries + 1))
                return self._make_api_request(url, params, retries + 1)
            return None
        except Exception as e:
            logger.error(f"Unexpected error during API request: {e}")
            return None

    def _parse_work(self, work_data: Dict) -> Optional[Dict]:
        """
        Parse a work object from Open Library API response.

        Args:
            work_data: Work data from API

        Returns:
            Normalized book dictionary
        """
        try:
            # Extract work key
            work_key = work_data.get('key', '').replace('/works/', '')
            if not work_key:
                return None

            # Get basic info
            title = work_data.get('title', '')
            if not title:
                return None

            # Get authors
            authors = []
            author_data = work_data.get('authors', [])
            if isinstance(author_data, list):
                for author in author_data:
                    if isinstance(author, dict):
                        author_name = author.get('name', '')
                        if author_name:
                            authors.append(author_name)

            # Get first edition key for cover
            edition_key = None
            if 'edition_key' in work_data and work_data['edition_key']:
                edition_key = work_data['edition_key'][0]

            # Get cover
            cover_url = None
            cover_id = work_data.get('cover_id') or work_data.get('cover_i')
            if cover_id:
                cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"

            # Get publication year
            publish_year = work_data.get('first_publish_year')

            # Get subjects/genres
            subjects = work_data.get('subject', [])
            if not isinstance(subjects, list):
                subjects = []

            # Get ISBNs if available
            isbn = None
            isbn13 = None
            if 'isbn' in work_data and work_data['isbn']:
                isbns = work_data['isbn']
                for i in isbns:
                    if len(i) == 10:
                        isbn = i
                    elif len(i) == 13:
                        isbn13 = i
                    if isbn and isbn13:
                        break

            # Create book identifier (use ISBN13, ISBN, or work key)
            book_identifier = isbn13 or isbn or f"OL:{work_key}"

            return {
                'book_identifier': book_identifier,
                'title': title,
                'authors': authors,
                'isbn': isbn,
                'isbn13': isbn13,
                'cover_url': cover_url,
                'publish_year': publish_year,
                'page_count': work_data.get('number_of_pages_median'),
                'subjects': subjects[:10],  # Limit to first 10 subjects
                'description': None,  # Would need separate API call
                'work_key': work_key,
                'edition_key': edition_key
            }

        except Exception as e:
            logger.error(f"Error parsing work data: {e}")
            return None

    def search_by_author(self, author_name: str, limit: int = 20) -> List[Dict]:
        """
        Search for books by a specific author.

        Args:
            author_name: Author's name to search for
            limit: Maximum number of results to return

        Returns:
            List of normalized book dictionaries
        """
        url = f"{self.BASE_URL}/search.json"
        params = {
            'author': author_name,
            'limit': min(limit, 100),  # API limit
            'fields': 'key,title,author_name,first_publish_year,isbn,edition_key,cover_i,cover_id,subject,number_of_pages_median'
        }

        logger.info(f"Searching for books by author: {author_name}")
        response = self._make_api_request(url, params)

        if not response or 'docs' not in response:
            logger.warning(f"No results found for author: {author_name}")
            return []

        books = []
        for doc in response['docs']:
            book = self._parse_work(doc)
            if book and book not in books:  # Avoid duplicates
                books.append(book)

        logger.info(f"Found {len(books)} books by author: {author_name}")
        return books[:limit]

    def search_by_subject(self, subject: str, limit: int = 20) -> List[Dict]:
        """
        Search for books by subject/genre.

        Args:
            subject: Subject or genre to search for (e.g., "science fiction", "fantasy")
            limit: Maximum number of results to return

        Returns:
            List of normalized book dictionaries
        """
        url = f"{self.BASE_URL}/search.json"
        params = {
            'subject': subject,
            'limit': min(limit, 100),
            'fields': 'key,title,author_name,first_publish_year,isbn,edition_key,cover_i,cover_id,subject,number_of_pages_median'
        }

        logger.info(f"Searching for books by subject: {subject}")
        response = self._make_api_request(url, params)

        if not response or 'docs' not in response:
            logger.warning(f"No results found for subject: {subject}")
            return []

        books = []
        for doc in response['docs']:
            book = self._parse_work(doc)
            if book and book not in books:
                books.append(book)

        logger.info(f"Found {len(books)} books for subject: {subject}")
        return books[:limit]

    def get_book_details(self, isbn: str) -> Optional[Dict]:
        """
        Get detailed information about a specific book by ISBN.

        Args:
            isbn: ISBN-10 or ISBN-13

        Returns:
            Normalized book dictionary, or None if not found
        """
        url = f"{self.BASE_URL}/isbn/{isbn}.json"

        logger.info(f"Fetching book details for ISBN: {isbn}")
        response = self._make_api_request(url)

        if not response:
            logger.warning(f"No details found for ISBN: {isbn}")
            return None

        # Parse edition data
        try:
            title = response.get('title', '')
            authors = []

            # Get author names from author keys
            author_keys = response.get('authors', [])
            for author_data in author_keys:
                if isinstance(author_data, dict) and 'key' in author_data:
                    author_key = author_data['key']
                    author_info = self._make_api_request(f"{self.BASE_URL}{author_key}.json")
                    if author_info and 'name' in author_info:
                        authors.append(author_info['name'])

            # Get cover
            cover_url = None
            cover_ids = response.get('covers', [])
            if cover_ids and cover_ids[0]:
                cover_url = f"https://covers.openlibrary.org/b/id/{cover_ids[0]}-M.jpg"

            publish_year = response.get('publish_date')
            if publish_year:
                # Try to extract year from publish date
                try:
                    import re
                    year_match = re.search(r'\d{4}', publish_year)
                    if year_match:
                        publish_year = int(year_match.group())
                except:
                    pass

            return {
                'book_identifier': isbn,
                'title': title,
                'authors': authors,
                'isbn': isbn if len(isbn) == 10 else None,
                'isbn13': isbn if len(isbn) == 13 else None,
                'cover_url': cover_url,
                'publish_year': publish_year,
                'page_count': response.get('number_of_pages'),
                'subjects': response.get('subjects', [])[:10],
                'description': None,
                'work_key': response.get('works', [{}])[0].get('key', '').replace('/works/', '') if response.get('works') else None,
                'edition_key': response.get('key', '').replace('/books/', '')
            }

        except Exception as e:
            logger.error(f"Error parsing book details: {e}")
            return None
