"""
FoJin Data Bridge — connects Master-skill to FoJin's Buddhist text platform.

Every call goes through the fojin.app REST API. The `mode` argument (and
`FOJIN_MODE`) is accepted but inert: the "local mode: direct database access"
this docstring advertised for two years was never implemented, and describing
an unwritten feature as a shipped one is its own kind of unverified claim.
"""

import json
import logging
import os
from typing import Optional
from urllib.parse import urlparse

import requests

# A response this big is a broken endpoint or a hostile one, never a real
# search result — the largest legitimate payload observed is a full juan at
# well under 2 MB. Without a cap, `resp.json()` reads the whole body into
# memory first, so a wedged or redirected host can take the process out.
MAX_RESPONSE_BYTES = 16 * 1024 * 1024

# (connect, read). One scalar timeout applies the same value to both, so a
# host that accepts the connection and then says nothing held the old code for
# the full 30s. Connecting is either fast or not happening.
DEFAULT_TIMEOUT = (5, 30)


class FojinUnavailableError(Exception):
    """Raised when FoJin API is unreachable. Callers should handle gracefully."""
    pass


class FojinConfigError(ValueError):
    """Raised when FOJIN_URL is not a usable https base URL."""
    pass


def _validate_base_url(url: str) -> str:
    """Reject a base URL that is not plain https.

    FOJIN_URL is read from the environment and every request is built on top of
    it, so it decides where citations are verified against. Allowing `http://`
    or a `file://`-ish scheme through would silently downgrade or redirect that
    check. `http://localhost` stays legal because the local-development path
    documented in references/fojin-api.md needs it.
    """
    parsed = urlparse(url)
    if parsed.scheme == "https":
        return url.rstrip("/")
    if parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1", "::1"):
        return url.rstrip("/")
    raise FojinConfigError(
        f"FOJIN_URL must be https (or http on localhost): {url!r}"
    )


class FojinBridge:
    """Bridge to FoJin Buddhist text platform."""

    def __init__(self, mode: str = "api", base_url: str = "https://fojin.app"):
        # `mode` has never done anything: the docstring's "local mode: direct
        # database access" was never implemented, and every call goes through
        # the REST path regardless. Kept as an accepted argument so existing
        # callers and FOJIN_MODE=… do not break, but it is now recorded as
        # inert rather than left looking like a feature.
        if mode not in ("api", ""):
            logging.getLogger(__name__).warning(
                "FojinBridge mode=%r is not implemented; using the REST API", mode
            )
        self.mode = "api"
        self.base_url = _validate_base_url(base_url)
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
        resp = None
        try:
            # stream=True so the body is not pulled into memory before its
            # size can be checked.
            resp = self.session.get(
                url, params=params, timeout=DEFAULT_TIMEOUT, stream=True
            )
            resp.raise_for_status()
            body = self._read_capped(resp)
        except requests.ConnectionError as e:
            raise FojinUnavailableError(f"FoJin API unreachable: {e}") from e
        except requests.Timeout as e:
            raise FojinUnavailableError(f"FoJin API timeout: {e}") from e
        finally:
            # A streamed response holds its connection until closed.
            if resp is not None:
                resp.close()
        return json.loads(body)

    @staticmethod
    def _read_capped(resp) -> bytes:
        """Read a response body, refusing one over MAX_RESPONSE_BYTES.

        Checked while reading rather than from Content-Length, which a hostile
        or merely chunked response need not send truthfully.
        """
        chunks: list[bytes] = []
        total = 0
        for chunk in resp.iter_content(64 * 1024):
            total += len(chunk)
            if total > MAX_RESPONSE_BYTES:
                raise FojinUnavailableError(
                    f"FoJin API response exceeded {MAX_RESPONSE_BYTES} bytes; "
                    "refusing to buffer it"
                )
            chunks.append(chunk)
        return b"".join(chunks)

    def test_connection(self) -> bool:
        """Test if FoJin API is reachable."""
        try:
            self._get("/api/stats")
            return True
        except Exception:
            return False


def create_bridge() -> FojinBridge:
    """Create a FojinBridge from environment variables.

    Raises FojinConfigError if FOJIN_URL is not a usable https base URL.
    """
    mode = os.environ.get("FOJIN_MODE", "api")
    url = os.environ.get("FOJIN_URL", "https://fojin.app")
    return FojinBridge(mode=mode, base_url=url)
