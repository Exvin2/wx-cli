"""Location favorites management for wx."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class FavoriteLocation:
    """A saved favorite location."""

    name: str
    display_name: str
    lat: float
    lon: float
    timezone: str | None = None
    notes: str | None = None


class FavoritesManager:
    """Manage favorite weather locations."""

    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.favorites_file = state_dir / "favorites.json"
        self._ensure_state_dir()

    def _ensure_state_dir(self) -> None:
        """Ensure the state directory exists."""
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def add_favorite(
        self,
        name: str,
        display_name: str,
        lat: float,
        lon: float,
        timezone: str | None = None,
        notes: str | None = None,
    ) -> bool:
        """Add a location to favorites."""
        favorites = self.load_favorites()

        # Check if already exists
        if name in favorites:
            return False

        favorites[name] = {
            "name": name,
            "display_name": display_name,
            "lat": lat,
            "lon": lon,
            "timezone": timezone,
            "notes": notes,
        }

        return self._save_favorites(favorites)

    def remove_favorite(self, name: str) -> bool:
        """Remove a location from favorites."""
        favorites = self.load_favorites()

        if name not in favorites:
            return False

        del favorites[name]
        return self._save_favorites(favorites)

    def get_favorite(self, name: str) -> FavoriteLocation | None:
        """Get a favorite location by name."""
        favorites = self.load_favorites()
        data = favorites.get(name)

        if not data:
            return None

        return FavoriteLocation(
            name=data["name"],
            display_name=data["display_name"],
            lat=data["lat"],
            lon=data["lon"],
            timezone=data.get("timezone"),
            notes=data.get("notes"),
        )

    def list_favorites(self) -> list[FavoriteLocation]:
        """List all favorite locations."""
        favorites = self.load_favorites()
        return [
            FavoriteLocation(
                name=data["name"],
                display_name=data["display_name"],
                lat=data["lat"],
                lon=data["lon"],
                timezone=data.get("timezone"),
                notes=data.get("notes"),
            )
            for data in favorites.values()
        ]

    def load_favorites(self) -> dict[str, Any]:
        """Load favorites from disk."""
        if not self.favorites_file.exists():
            return {}

        try:
            return json.loads(self.favorites_file.read_text())
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_favorites(self, favorites: dict[str, Any]) -> bool:
        """Save favorites to disk with secure permissions."""
        import os
        import tempfile

        try:
            # Atomic write with temp file
            fd, temp_path = tempfile.mkstemp(
                dir=self.state_dir, prefix=".wx_fav_", suffix=".json"
            )
            try:
                with os.fdopen(fd, "w") as f:
                    f.write(json.dumps(favorites, ensure_ascii=True, indent=2))

                # Set restrictive permissions
                os.chmod(temp_path, 0o600)

                # Atomic move
                os.replace(temp_path, self.favorites_file)
                return True
            except Exception:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise
        except OSError:
            return False
