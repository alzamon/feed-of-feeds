import hashlib
import json
from pathlib import Path

class ArticleManager:
    """Manages the state of read articles with persistence."""
    
    def __init__(self, storage_path: str = "read_articles.json"):
        self.storage_path = Path(storage_path)
        self.read_articles = self._load_state()
    
    def _generate_hash(self, title: str, content: str) -> str:
        """Generate a hash based on the title and content of an article."""
        hasher = hashlib.sha256()
        hasher.update(title.encode('utf-8'))
        hasher.update(content.encode('utf-8'))
        return hasher.hexdigest()
    
    def _load_state(self) -> set:
        """Load the state of read articles from the storage file."""
        if self.storage_path.exists():
            try:
                with self.storage_path.open("r", encoding="utf-8") as file:
                    return set(json.load(file))
            except Exception as e:
                print(f"Error loading article manager state: {e}")
                return set()
        return set()
    
    def _save_state(self):
        """Save the state of read articles to the storage file."""
        try:
            with self.storage_path.open("w", encoding="utf-8") as file:
                json.dump(list(self.read_articles), file)
        except Exception as e:
            print(f"Error saving article manager state: {e}")
    
    def is_read(self, title: str, content: str) -> bool:
        """Check if an article is already read."""
        article_hash = self._generate_hash(title, content)
        return article_hash in self.read_articles
    
    def mark_as_read(self, title: str, content: str):
        """Mark an article as read."""
        article_hash = self._generate_hash(title, content)
        self.read_articles.add(article_hash)
        self._save_state()
