"""
FoJin Data Bridge — connects Buddha-skill to FoJin's Buddhist text platform.

Two modes:
- API mode (default): calls fojin.app REST API, works for any user
- Local mode: direct database access, for FoJin developers only
"""

import json
import logging
import os
from typing import Optional

import requests


class FojinUnavailableError(Exception):
    """Raised when FoJin API is unreachable. Callers should handle gracefully."""
    pass


class FojinBridge:
    """Bridge to FoJin Buddhist text platform."""

    def __init__(self, mode: str = "api", base_url: str = "https://fojin.app"):
        self.mode = mode
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    # ── Search ──────────────────────────────────────────────

    def search_texts(self, query: str, sources: Optional[str] = None, lang: Optional[str] = None, page: int = 1, size: int = 20) -> dict:
        """Search Buddhist texts by keyword."""
        params = {"q": query, "page": page, "size": size}
        if sources:
            params["sources"] = sources
        if lang:
            params["lang"] = lang
        return self._get("/api/search", params)

    def search_content(self, query: str, sources: Optional[str] = None, page: int = 1, size: int = 20) -> dict:
        """Full-text content search with highlighting."""
        params = {"q": query, "page": page, "size": size}
        if sources:
            params["sources"] = sources
        return self._get("/api/search/content", params)

    def semantic_search(self, query: str, top_k: int = 10) -> dict:
        """Vector similarity search using pgvector embeddings."""
        params = {"q": query, "size": top_k}
        return self._get("/api/search/semantic", params)

    # ── Texts ───────────────────────────────────────────────

    def get_text(self, text_id: int) -> dict:
        """Get text metadata by ID."""
        return self._get(f"/api/texts/{text_id}")

    def get_text_content(self, text_id: int, juan_num: int, lang: Optional[str] = None) -> dict:
        """Get full content of a specific juan (scroll/fascicle)."""
        params = {}
        if lang:
            params["lang"] = lang
        return self._get(f"/api/texts/{text_id}/juans/{juan_num}", params)

    def get_text_juans(self, text_id: int) -> dict:
        """List all juans for a text."""
        return self._get(f"/api/texts/{text_id}/juans")

    def lookup_cbeta_ids(self, ids: str) -> dict:
        """Batch lookup CBETA IDs to internal IDs."""
        return self._get("/api/texts/lookup-cbeta", {"ids": ids})

    def get_similar_passages(self, text_id: int, juan_num: int) -> dict:
        """Find similar passages using pgvector similarity."""
        return self._get(f"/api/texts/{text_id}/juans/{juan_num}/similar")

    # ── Knowledge Graph ─────────────────────────────────────

    def search_kg_entities(self, query: str, entity_type: Optional[str] = None, limit: int = 20) -> dict:
        """Search knowledge graph entities."""
        params = {"q": query, "limit": limit}
        if entity_type:
            params["entity_type"] = entity_type
        return self._get("/api/kg/entities", params)

    def get_kg_entity(self, entity_id: int) -> dict:
        """Get detailed entity info with relations."""
        return self._get(f"/api/kg/entities/{entity_id}")

    def get_kg_graph(self, entity_id: int, depth: int = 2, max_nodes: int = 150, predicates: Optional[str] = None) -> dict:
        """Get entity's relationship graph."""
        params = {"depth": depth, "max_nodes": max_nodes}
        if predicates:
            params["predicates"] = predicates
        return self._get(f"/api/kg/entities/{entity_id}/graph", params)

    # ── Dictionary ──────────────────────────────────────────

    def search_dictionary(self, query: str, lang: Optional[str] = None, source: Optional[str] = None, page: int = 1, size: int = 20) -> dict:
        """Search Buddhist dictionaries."""
        params = {"q": query, "page": page, "size": size}
        if lang:
            params["lang"] = lang
        if source:
            params["source"] = source
        return self._get("/api/dictionary/search", params)

    def search_dictionary_grouped(self, query: str) -> dict:
        """Search dictionaries, results grouped by source."""
        return self._get("/api/dictionary/search/grouped", {"q": query})

    # ── Helpers ──────────────────────────────────────────────

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        """Make GET request to FoJin API.

        Raises:
            FojinUnavailableError: When FoJin is unreachable (connection/timeout)
            requests.HTTPError: On 4xx/5xx responses
        """
        url = f"{self.base_url}{path}"
        try:
            resp = self.session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.ConnectionError as e:
            raise FojinUnavailableError(f"FoJin API unreachable: {e}") from e
        except requests.Timeout as e:
            raise FojinUnavailableError(f"FoJin API timeout: {e}") from e

    def test_connection(self) -> bool:
        """Test if FoJin API is reachable."""
        try:
            self._get("/api/stats")
            return True
        except Exception:
            return False


def create_bridge() -> FojinBridge:
    """Create a FojinBridge from environment variables."""
    mode = os.environ.get("FOJIN_MODE", "api")
    url = os.environ.get("FOJIN_URL", "https://fojin.app")
    return FojinBridge(mode=mode, base_url=url)
