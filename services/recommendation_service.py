"""
Recommendation Engine
Generates personalized book recommendations using multiple strategies.
"""

import json
import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Tuple, Optional
from sqlalchemy import func, and_, or_

from models import db
from models.book import Book
from models.review import Review
from models.reading_record import ReadingRecord
from models.shelf import Shelf, BookShelf
from models.recommendation import Recommendation, RecommendationDismissal
from services.book_discovery_service import BookDiscoveryService

logger = logging.getLogger(__name__)


class RecommendationEngine:
    """
    Main recommendation engine that coordinates multiple recommendation strategies.
    """

    CACHE_DURATION_HOURS = 24
    MIN_RATING_FOR_RECOMMENDATION = 4.0
    MIN_RATED_BOOKS = 5

    def __init__(self, db_session=None):
        self.db = db_session or db.session
        self.discovery_service = BookDiscoveryService()
        self.strategies = {
            'author_based': AuthorBasedStrategy(self.db, self.discovery_service),
            'shelf_based': ShelfBasedStrategy(self.db, self.discovery_service)
        }

    def generate_recommendations(self, limit: int = 20, force_refresh: bool = False) -> List[Recommendation]:
        """
        Generate personalized recommendations combining all strategies.

        Args:
            limit: Maximum number of recommendations to return
            force_refresh: If True, regenerate all recommendations ignoring cache

        Returns:
            List of Recommendation objects sorted by score
        """
        logger.info(f"Generating recommendations (limit={limit}, force_refresh={force_refresh})")

        # Check if user has enough data for recommendations
        if not self._has_sufficient_data():
            logger.warning("Insufficient data for recommendations")
            return []

        # Try to get cached recommendations first
        if not force_refresh:
            cached = self.get_cached_recommendations(limit)
            if cached and len(cached) >= min(limit, 10):  # Return cache if we have enough
                logger.info(f"Returning {len(cached)} cached recommendations")
                return cached

        # Clear old recommendations
        self._clear_expired_recommendations()
        if force_refresh:
            self._clear_all_recommendations()

        # Get dismissed book identifiers
        dismissed_ids = self._get_dismissed_book_identifiers()

        # Run all strategies and collect results
        all_candidates = []
        for strategy_name, strategy in self.strategies.items():
            try:
                logger.info(f"Running strategy: {strategy_name}")
                candidates = strategy.generate_recommendations()
                all_candidates.extend(candidates)
                logger.info(f"Strategy {strategy_name} generated {len(candidates)} candidates")
            except Exception as e:
                logger.error(f"Strategy {strategy_name} failed: {e}", exc_info=True)
                continue

        if not all_candidates:
            logger.warning("No candidates generated from any strategy")
            return []

        # Combine and score recommendations
        final_recommendations = self._combine_and_score(all_candidates, dismissed_ids, limit)

        # Save to database
        self._save_recommendations(final_recommendations)

        logger.info(f"Generated {len(final_recommendations)} recommendations")
        return final_recommendations

    def get_cached_recommendations(self, limit: int = 20) -> List[Recommendation]:
        """
        Retrieve cached recommendations that haven't expired.

        Args:
            limit: Maximum number of recommendations to return

        Returns:
            List of Recommendation objects
        """
        recommendations = (
            Recommendation.query
            .filter(Recommendation.expires_at > datetime.utcnow())
            .order_by(Recommendation.score.desc())
            .limit(limit)
            .all()
        )
        return recommendations

    def dismiss_recommendation(self, book_identifier: str, reason: str = 'not_interested', title: str = None) -> bool:
        """
        Mark a recommendation as dismissed so it won't appear again.

        Args:
            book_identifier: Unique identifier for the book
            reason: Reason for dismissal
            title: Optional book title for reference

        Returns:
            True if dismissed successfully
        """
        try:
            # Check if already dismissed
            existing = RecommendationDismissal.query.filter_by(book_identifier=book_identifier).first()
            if existing:
                logger.info(f"Book {book_identifier} already dismissed")
                return True

            # Create dismissal record
            dismissal = RecommendationDismissal(
                book_identifier=book_identifier,
                reason=reason,
                title=title
            )
            self.db.add(dismissal)

            # Remove from active recommendations
            Recommendation.query.filter_by(book_identifier=book_identifier).delete()

            self.db.commit()
            logger.info(f"Dismissed recommendation: {book_identifier}")
            return True

        except Exception as e:
            logger.error(f"Error dismissing recommendation: {e}")
            self.db.rollback()
            return False

    def _has_sufficient_data(self) -> bool:
        """Check if user has enough data to generate recommendations"""
        # Count books with ratings >= 4.0
        high_rated_count = (
            Review.query
            .filter(Review.rating >= self.MIN_RATING_FOR_RECOMMENDATION)
            .count()
        )

        if high_rated_count < self.MIN_RATED_BOOKS:
            logger.info(f"Only {high_rated_count} highly rated books, need {self.MIN_RATED_BOOKS}")
            return False

        return True

    def _get_dismissed_book_identifiers(self) -> set:
        """Get set of book identifiers that have been dismissed"""
        dismissals = RecommendationDismissal.query.all()
        return {d.book_identifier for d in dismissals}

    def _clear_expired_recommendations(self):
        """Remove expired recommendations from database"""
        try:
            deleted = (
                Recommendation.query
                .filter(Recommendation.expires_at <= datetime.utcnow())
                .delete()
            )
            if deleted > 0:
                self.db.commit()
                logger.info(f"Cleared {deleted} expired recommendations")
        except Exception as e:
            logger.error(f"Error clearing expired recommendations: {e}")
            self.db.rollback()

    def _clear_all_recommendations(self):
        """Remove all recommendations (for force refresh)"""
        try:
            deleted = Recommendation.query.delete()
            if deleted > 0:
                self.db.commit()
                logger.info(f"Cleared all {deleted} recommendations for refresh")
        except Exception as e:
            logger.error(f"Error clearing recommendations: {e}")
            self.db.rollback()

    def _combine_and_score(self, candidates: List[Dict], dismissed_ids: set, limit: int) -> List[Recommendation]:
        """
        Combine candidates from multiple strategies, apply scoring adjustments, and deduplicate.

        Args:
            candidates: List of candidate recommendations with scores
            dismissed_ids: Set of dismissed book identifiers
            limit: Maximum number to return

        Returns:
            List of Recommendation objects sorted by final score
        """
        # Group by book_identifier and aggregate scores
        book_scores = defaultdict(lambda: {'scores': [], 'data': None})

        for candidate in candidates:
            book_id = candidate['book_identifier']

            # Skip dismissed books
            if book_id in dismissed_ids:
                continue

            # Skip books already in library
            if self._is_book_in_library(candidate):
                continue

            book_scores[book_id]['scores'].append(candidate['score'])
            if not book_scores[book_id]['data']:
                book_scores[book_id]['data'] = candidate

        # Calculate final scores
        recommendations = []
        for book_id, data in book_scores.items():
            candidate = data['data']
            scores = data['scores']

            # Combine scores (weighted average if from multiple strategies)
            base_score = sum(scores) / len(scores)

            # Apply adjustments
            final_score = self._apply_score_adjustments(base_score, candidate)

            # Create Recommendation object
            rec = Recommendation(
                book_identifier=book_id,
                title=candidate['title'],
                authors=json.dumps(candidate.get('authors', [])),
                isbn=candidate.get('isbn'),
                isbn13=candidate.get('isbn13'),
                cover_url=candidate.get('cover_url'),
                publish_year=candidate.get('publish_year'),
                page_count=candidate.get('page_count'),
                subjects=json.dumps(candidate.get('subjects', [])),
                description=candidate.get('description'),
                strategy=candidate['strategy'],
                score=final_score,
                reason=candidate['reason']
            )
            recommendations.append(rec)

        # Sort by score and return top N
        recommendations.sort(key=lambda x: x.score, reverse=True)
        return recommendations[:limit]

    def _is_book_in_library(self, candidate: Dict) -> bool:
        """Check if book is already in user's library"""
        title = candidate.get('title', '').lower().strip()
        authors = candidate.get('authors', [])

        if not title:
            return False

        # Check by ISBN first (most reliable)
        isbn = candidate.get('isbn')
        isbn13 = candidate.get('isbn13')

        if isbn:
            existing = Book.query.filter(
                or_(Book.isbn == isbn, Book.isbn13 == isbn)
            ).first()
            if existing:
                return True

        if isbn13:
            existing = Book.query.filter(
                or_(Book.isbn == isbn13, Book.isbn13 == isbn13)
            ).first()
            if existing:
                return True

        # Check by title + author (fuzzy match)
        if authors:
            author_str = ', '.join(authors).lower().strip()
            existing = Book.query.filter(
                and_(
                    func.lower(Book.title) == title,
                    func.lower(Book.author).contains(author_str)
                )
            ).first()
            if existing:
                return True

        return False

    def _apply_score_adjustments(self, base_score: float, candidate: Dict) -> float:
        """Apply adjustments to base score based on book attributes"""
        score = base_score

        # Boost recent publications (last 3 years)
        publish_year = candidate.get('publish_year')
        if publish_year and publish_year >= datetime.now().year - 3:
            score *= 1.1

        # Boost books with covers
        if candidate.get('cover_url'):
            score *= 1.05

        # Ensure score stays in 0-1 range
        return min(score, 1.0)

    def _save_recommendations(self, recommendations: List[Recommendation]):
        """Save recommendations to database"""
        try:
            for rec in recommendations:
                self.db.add(rec)
            self.db.commit()
            logger.info(f"Saved {len(recommendations)} recommendations to database")
        except Exception as e:
            logger.error(f"Error saving recommendations: {e}")
            self.db.rollback()


class AuthorBasedStrategy:
    """
    Recommends books by authors the user has enjoyed.
    Weight: 0.6 (highest priority)
    """

    WEIGHT = 0.6
    MIN_RATING = 4.0
    TOP_AUTHORS_COUNT = 5
    BOOKS_PER_AUTHOR = 10

    def __init__(self, db_session, discovery_service: BookDiscoveryService):
        self.db = db_session
        self.discovery = discovery_service

    def generate_recommendations(self) -> List[Dict]:
        """Generate author-based recommendations"""
        # Find favorite authors (those with high-rated books)
        favorite_authors = self._get_favorite_authors()

        if not favorite_authors:
            logger.warning("No favorite authors found")
            return []

        # Search for books by these authors
        recommendations = []
        for author_name, avg_rating, book_count in favorite_authors[:self.TOP_AUTHORS_COUNT]:
            try:
                logger.info(f"Searching for books by {author_name} (avg rating: {avg_rating:.1f})")
                books = self.discovery.search_by_author(author_name, limit=self.BOOKS_PER_AUTHOR)

                for book in books:
                    # Calculate score based on author's rating and popularity
                    author_score = (avg_rating / 5.0) * min(book_count / 3.0, 1.0)
                    final_score = author_score * self.WEIGHT

                    recommendations.append({
                        **book,
                        'strategy': 'author_based',
                        'score': final_score,
                        'reason': f"You rated {book_count} book{'s' if book_count > 1 else ''} by {author_name} {avg_rating:.1f} stars on average"
                    })

            except Exception as e:
                logger.error(f"Error searching for author {author_name}: {e}")
                continue

        return recommendations

    def _get_favorite_authors(self) -> List[Tuple[str, float, int]]:
        """
        Get list of favorite authors based on ratings.

        Returns:
            List of tuples: (author_name, avg_rating, book_count)
        """
        # Query books with high ratings
        high_rated_books = (
            self.db.query(Book, Review)
            .join(Review, Book.id == Review.book_id)
            .filter(Review.rating >= self.MIN_RATING)
            .all()
        )

        # Group by author and calculate stats
        author_stats = defaultdict(lambda: {'ratings': [], 'count': 0})

        for book, review in high_rated_books:
            # Split multiple authors if needed
            authors = [a.strip() for a in book.author.split(',')]
            for author in authors:
                author_stats[author]['ratings'].append(review.rating)
                author_stats[author]['count'] += 1

        # Calculate average ratings
        favorite_authors = []
        for author, stats in author_stats.items():
            avg_rating = sum(stats['ratings']) / len(stats['ratings'])
            book_count = stats['count']
            favorite_authors.append((author, avg_rating, book_count))

        # Sort by average rating * book count
        favorite_authors.sort(key=lambda x: x[1] * min(x[2] / 2.0, 1.5), reverse=True)

        logger.info(f"Found {len(favorite_authors)} favorite authors")
        return favorite_authors


class ShelfBasedStrategy:
    """
    Recommends books from user's favorite genres/shelves.
    Weight: 0.4
    """

    WEIGHT = 0.4
    TOP_SHELVES_COUNT = 3
    BOOKS_PER_SHELF = 15

    # Map shelf names to Open Library subjects
    SHELF_TO_SUBJECT_MAP = {
        'fiction': 'fiction',
        'non-fiction': 'nonfiction',
        'science fiction': 'science_fiction',
        'fantasy': 'fantasy',
        'mystery': 'mystery',
        'thriller': 'thriller',
        'romance': 'romance',
        'biography': 'biography',
        'autobiography': 'autobiography',
        'history': 'history',
        'science': 'science',
        'philosophy': 'philosophy',
        'self-help': 'self-help',
        'business': 'business',
        'young adult': 'young_adult',
        'children': 'children',
        'horror': 'horror',
        'poetry': 'poetry',
        'classics': 'classics'
    }

    def __init__(self, db_session, discovery_service: BookDiscoveryService):
        self.db = db_session
        self.discovery = discovery_service

    def generate_recommendations(self) -> List[Dict]:
        """Generate shelf-based recommendations"""
        # Find favorite shelves
        favorite_shelves = self._get_favorite_shelves()

        if not favorite_shelves:
            logger.warning("No favorite shelves found")
            return []

        # Search for books in these genres
        recommendations = []
        for shelf_name, shelf_score, book_count in favorite_shelves[:self.TOP_SHELVES_COUNT]:
            # Map shelf name to Open Library subject
            subject = self._map_shelf_to_subject(shelf_name)
            if not subject:
                logger.warning(f"Could not map shelf '{shelf_name}' to subject")
                continue

            try:
                logger.info(f"Searching for books in genre: {subject} (shelf: {shelf_name}, score: {shelf_score:.2f})")
                books = self.discovery.search_by_subject(subject, limit=self.BOOKS_PER_SHELF)

                for book in books:
                    # Calculate score based on shelf preference
                    final_score = shelf_score * self.WEIGHT

                    recommendations.append({
                        **book,
                        'strategy': 'shelf_based',
                        'score': final_score,
                        'reason': f"Top pick from your favorite genre: {shelf_name.title()} ({book_count} books)"
                    })

            except Exception as e:
                logger.error(f"Error searching for subject {subject}: {e}")
                continue

        return recommendations

    def _get_favorite_shelves(self) -> List[Tuple[str, float, int]]:
        """
        Get list of favorite shelves based on book count and ratings.

        Returns:
            List of tuples: (shelf_name, score, book_count)
        """
        # Query all shelves with their books and ratings
        shelves_data = (
            self.db.query(
                Shelf.name,
                func.count(BookShelf.book_id).label('book_count'),
                func.avg(Review.rating).label('avg_rating')
            )
            .join(BookShelf, Shelf.id == BookShelf.shelf_id)
            .outerjoin(Review, BookShelf.book_id == Review.book_id)
            .group_by(Shelf.id, Shelf.name)
            .all()
        )

        # Calculate shelf scores
        shelf_scores = []
        for shelf_name, book_count, avg_rating in shelves_data:
            if book_count < 2:  # Skip shelves with too few books
                continue

            # Score = (book_count * avg_rating) normalized
            avg_rating = avg_rating or 3.0  # Default if no ratings
            score = min(book_count / 10.0, 1.0) * (avg_rating / 5.0)

            shelf_scores.append((shelf_name, score, book_count))

        # Sort by score
        shelf_scores.sort(key=lambda x: x[1], reverse=True)

        logger.info(f"Found {len(shelf_scores)} shelves with scores")
        return shelf_scores

    def _map_shelf_to_subject(self, shelf_name: str) -> Optional[str]:
        """Map a shelf name to an Open Library subject"""
        shelf_lower = shelf_name.lower().strip()

        # Direct mapping
        if shelf_lower in self.SHELF_TO_SUBJECT_MAP:
            return self.SHELF_TO_SUBJECT_MAP[shelf_lower]

        # Partial matching
        for key, value in self.SHELF_TO_SUBJECT_MAP.items():
            if key in shelf_lower or shelf_lower in key:
                return value

        # Default: use shelf name as-is (Open Library is flexible)
        return shelf_lower.replace(' ', '_')
