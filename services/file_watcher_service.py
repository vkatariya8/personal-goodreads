"""
File Watcher Service
Monitors the markdown library directory for changes and syncs them to SQLite.
Uses watchdog library for filesystem monitoring.
"""

import time
import logging
from pathlib import Path
from threading import Thread, Event
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent

from services.markdown_sync_service import MarkdownSyncService

logger = logging.getLogger(__name__)


class MarkdownFileEventHandler(FileSystemEventHandler):
    """
    Handles file system events for markdown files.
    Debounces rapid changes and triggers sync to database.
    """

    def __init__(self, sync_service: MarkdownSyncService, debounce_seconds: int = 2):
        """
        Initialize the event handler.

        Args:
            sync_service: MarkdownSyncService instance for syncing
            debounce_seconds: Seconds to wait before processing changes
        """
        self.sync_service = sync_service
        self.debounce_seconds = debounce_seconds
        self.pending_changes = {}  # file_path -> last_event_time
        self.debounce_thread = None
        self.stop_event = Event()

    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory or not self._is_markdown_file(event.src_path):
            return

        logger.debug(f"File modified: {event.src_path}")
        self._schedule_sync(event.src_path)

    def on_created(self, event):
        """Handle file creation events"""
        if event.is_directory or not self._is_markdown_file(event.src_path):
            return

        logger.info(f"New file detected: {event.src_path}")
        self._schedule_sync(event.src_path)

    def on_deleted(self, event):
        """Handle file deletion events"""
        if event.is_directory or not self._is_markdown_file(event.src_path):
            return

        logger.info(f"File deleted: {event.src_path}")
        # TODO: Implement delete sync (mark book as deleted or remove from DB)
        # For now, we'll skip this - files are source of truth

    def _is_markdown_file(self, path: str) -> bool:
        """Check if path is a markdown file"""
        return path.endswith('.md') and not path.endswith('.tmp')

    def _schedule_sync(self, file_path: str):
        """
        Schedule a sync for this file after debounce period.
        Multiple rapid changes to same file will be batched.
        """
        self.pending_changes[file_path] = time.time()

        # Start debounce thread if not already running
        if self.debounce_thread is None or not self.debounce_thread.is_alive():
            self.debounce_thread = Thread(target=self._debounce_worker, daemon=True)
            self.debounce_thread.start()

    def _debounce_worker(self):
        """
        Background worker that processes pending changes after debounce period.
        """
        while not self.stop_event.is_set():
            current_time = time.time()
            files_to_sync = []

            # Find files that haven't been modified for debounce_seconds
            for file_path, last_event_time in list(self.pending_changes.items()):
                if current_time - last_event_time >= self.debounce_seconds:
                    files_to_sync.append(file_path)
                    del self.pending_changes[file_path]

            # Sync each file
            for file_path in files_to_sync:
                try:
                    logger.info(f"Syncing markdown to database: {file_path}")
                    success = self.sync_service.sync_markdown_to_db(file_path)
                    if success:
                        logger.info(f"✅ Successfully synced: {file_path}")
                    else:
                        logger.error(f"❌ Failed to sync: {file_path}")
                except Exception as e:
                    logger.error(f"Error syncing {file_path}: {e}", exc_info=True)

            # Exit if no more pending changes
            if not self.pending_changes:
                break

            # Sleep briefly before checking again
            time.sleep(0.5)

    def stop(self):
        """Stop the debounce worker"""
        self.stop_event.set()
        if self.debounce_thread and self.debounce_thread.is_alive():
            self.debounce_thread.join(timeout=5)


class FileWatcherService:
    """
    Main service for watching markdown library directory.
    Manages the watchdog observer and event handler.
    """

    def __init__(self, books_path: str, debounce_seconds: int = 2):
        """
        Initialize the file watcher service.

        Args:
            books_path: Path to books directory to monitor
            debounce_seconds: Seconds to wait before processing changes
        """
        self.books_path = Path(books_path)
        self.debounce_seconds = debounce_seconds
        self.observer = None
        self.event_handler = None
        self.sync_service = None

    def start(self):
        """Start watching the books directory"""
        if self.observer and self.observer.is_alive():
            logger.warning("File watcher already running")
            return

        # Ensure directory exists
        self.books_path.mkdir(parents=True, exist_ok=True)

        # Initialize services
        self.sync_service = MarkdownSyncService(str(self.books_path))
        self.event_handler = MarkdownFileEventHandler(
            self.sync_service,
            self.debounce_seconds
        )

        # Create and start observer
        self.observer = Observer()
        self.observer.schedule(
            self.event_handler,
            str(self.books_path),
            recursive=False  # Only watch books directory, not subdirectories
        )
        self.observer.start()

        logger.info(f"📂 File watcher started: monitoring {self.books_path}")

    def stop(self):
        """Stop watching the books directory"""
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=5)
            logger.info("File watcher stopped")

        if self.event_handler:
            self.event_handler.stop()

    def is_running(self) -> bool:
        """Check if the file watcher is currently running"""
        return self.observer is not None and self.observer.is_alive()


# Global instance for the Flask app
_file_watcher = None


def get_file_watcher() -> FileWatcherService:
    """Get the global file watcher instance"""
    return _file_watcher


def init_file_watcher(app):
    """
    Initialize and start the file watcher for a Flask app.
    Should be called after app creation.

    Args:
        app: Flask application instance
    """
    global _file_watcher

    if not app.config.get('ENABLE_FILE_WATCHER', True):
        logger.info("File watcher disabled in config")
        return

    books_path = app.config['BOOKS_PATH']
    debounce_seconds = app.config.get('FILE_WATCHER_DEBOUNCE_SECONDS', 2)

    _file_watcher = FileWatcherService(books_path, debounce_seconds)

    # Start in a separate thread to avoid blocking app startup
    watcher_thread = Thread(target=_file_watcher.start, daemon=True)
    watcher_thread.start()

    # Register cleanup on app teardown
    @app.teardown_appcontext
    def shutdown_watcher(exception=None):
        if _file_watcher:
            _file_watcher.stop()

    logger.info("File watcher initialized")
