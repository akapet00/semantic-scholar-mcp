"""Unit tests for author consolidation functionality."""

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from semantic_scholar_mcp.exceptions import NotFoundError
from semantic_scholar_mcp.models import (
    Author,
    AuthorConsolidationResult,
    AuthorExternalIds,
    AuthorGroup,
)
from semantic_scholar_mcp.tools import (
    consolidate_authors,
    find_duplicate_authors,
)
from semantic_scholar_mcp.tools._common import set_client_getter
from semantic_scholar_mcp.tools.authors import _normalize_dblp


class TestAuthorGroup:
    """Tests for AuthorGroup model."""

    def test_author_group_creation(self) -> None:
        """Test creating an AuthorGroup."""
        primary = Author(
            authorId="1",
            name="John Smith",
            citationCount=1000,
        )
        candidates = [
            Author(authorId="2", name="J. Smith", citationCount=500),
            Author(authorId="3", name="John D. Smith", citationCount=200),
        ]

        group = AuthorGroup(
            primary_author=primary,
            candidates=candidates,
            match_reasons=["same_orcid:0000-0001-2345-6789"],
        )

        assert group.primary_author.authorId == "1"
        assert len(group.candidates) == 2
        assert group.match_reasons[0].startswith("same_orcid")

    def test_author_group_with_dblp_match(self) -> None:
        """Test AuthorGroup with DBLP match reason."""
        group = AuthorGroup(
            primary_author=Author(authorId="1", name="Test"),
            candidates=[Author(authorId="2", name="Test2")],
            match_reasons=["same_dblp:homepages/j/JohnSmith"],
        )

        assert "same_dblp" in group.match_reasons[0]


class TestAuthorConsolidationResult:
    """Tests for AuthorConsolidationResult model."""

    def test_consolidation_result_creation(self) -> None:
        """Test creating an AuthorConsolidationResult."""
        merged = Author(
            authorId="1",
            name="John Smith",
            citationCount=1500,
            paperCount=50,
        )
        sources = [
            Author(authorId="1", name="John Smith", citationCount=1000),
            Author(authorId="2", name="J. Smith", citationCount=500),
        ]

        result = AuthorConsolidationResult(
            merged_author=merged,
            source_authors=sources,
            match_type="orcid",
            confidence=1.0,
        )

        assert result.merged_author.citationCount == 1500
        assert len(result.source_authors) == 2
        assert result.match_type == "orcid"
        assert result.confidence == 1.0

    def test_consolidation_result_user_confirmed(self) -> None:
        """Test consolidation result with user_confirmed match type."""
        result = AuthorConsolidationResult(
            merged_author=Author(authorId="1", name="Test"),
            source_authors=[
                Author(authorId="1", name="Test"),
                Author(authorId="2", name="Test2"),
            ],
            match_type="user_confirmed",
            confidence=None,
        )

        assert result.match_type == "user_confirmed"
        assert result.confidence is None


class TestAuthorExternalIds:
    """Tests for AuthorExternalIds model."""

    def test_external_ids_creation(self) -> None:
        """Test creating AuthorExternalIds."""
        ids = AuthorExternalIds(
            ORCID="0000-0001-2345-6789",
            DBLP="homepages/s/JohnSmith",
        )

        assert ids.ORCID == "0000-0001-2345-6789"
        assert ids.DBLP == "homepages/s/JohnSmith"

    def test_external_ids_partial(self) -> None:
        """Test AuthorExternalIds with only some IDs."""
        ids = AuthorExternalIds(ORCID="0000-0001-2345-6789")

        assert ids.ORCID == "0000-0001-2345-6789"
        assert ids.DBLP is None

    def test_external_ids_dblp_as_list(self) -> None:
        """Test AuthorExternalIds with DBLP as a list (API can return this format)."""
        ids = AuthorExternalIds(
            ORCID="0000-0001-2345-6789",
            DBLP=["homepages/s/JohnSmith"],
        )

        assert ids.ORCID == "0000-0001-2345-6789"
        assert ids.DBLP == ["homepages/s/JohnSmith"]

    def test_external_ids_dblp_as_empty_list(self) -> None:
        """Test AuthorExternalIds with DBLP as an empty list."""
        ids = AuthorExternalIds(DBLP=[])

        assert ids.DBLP == []


class TestNormalizeDblp:
    """Tests for _normalize_dblp helper function."""

    def test_normalize_dblp_string(self) -> None:
        """Test normalizing DBLP when it's already a string."""
        assert _normalize_dblp("homepages/s/JohnSmith") == "homepages/s/JohnSmith"

    def test_normalize_dblp_list_single(self) -> None:
        """Test normalizing DBLP when it's a list with one element."""
        assert _normalize_dblp(["homepages/s/JohnSmith"]) == "homepages/s/JohnSmith"

    def test_normalize_dblp_list_multiple(self) -> None:
        """Test normalizing DBLP when it's a list with multiple elements (takes first)."""
        assert _normalize_dblp(["first", "second"]) == "first"

    def test_normalize_dblp_empty_list(self) -> None:
        """Test normalizing DBLP when it's an empty list."""
        assert _normalize_dblp([]) is None

    def test_normalize_dblp_none(self) -> None:
        """Test normalizing DBLP when it's None."""
        assert _normalize_dblp(None) is None


class TestFindDuplicateAuthors:
    """Tests for find_duplicate_authors tool."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client."""
        mock = MagicMock()
        mock.get_with_retry = AsyncMock()
        return mock

    @pytest.fixture(autouse=True)
    def mock_client_getter(self, mock_client: MagicMock) -> Generator[None]:
        """Set mock client for all tests."""
        set_client_getter(lambda: mock_client)
        yield

    @pytest.mark.asyncio
    async def test_find_duplicate_authors_empty_names(self) -> None:
        """Test that empty names list returns error message."""
        result = await find_duplicate_authors([])

        assert isinstance(result, str)
        assert "provide at least one" in result.lower()

    @pytest.mark.asyncio
    async def test_find_duplicate_authors_with_orcid_match(self, mock_client: MagicMock) -> None:
        """Test finding duplicates by ORCID match."""
        mock_response = {
            "total": 2,
            "data": [
                {
                    "authorId": "1",
                    "name": "John Smith",
                    "citationCount": 1000,
                    "externalIds": {"ORCID": "0000-0001-2345-6789"},
                },
                {
                    "authorId": "2",
                    "name": "J. Smith",
                    "citationCount": 500,
                    "externalIds": {"ORCID": "0000-0001-2345-6789"},
                },
            ],
        }

        mock_client.get_with_retry.return_value = mock_response

        result = await find_duplicate_authors(["John Smith"])

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].primary_author.authorId == "1"
        assert len(result[0].candidates) == 1
        assert "same_orcid" in result[0].match_reasons[0]

    @pytest.mark.asyncio
    async def test_find_duplicate_authors_no_duplicates(self, mock_client: MagicMock) -> None:
        """Test when no duplicates are found."""
        mock_response = {
            "total": 2,
            "data": [
                {
                    "authorId": "1",
                    "name": "John Smith",
                    "externalIds": {"ORCID": "0000-0001-1111-1111"},
                },
                {
                    "authorId": "2",
                    "name": "Jane Doe",
                    "externalIds": {"ORCID": "0000-0002-2222-2222"},
                },
            ],
        }

        mock_client.get_with_retry.return_value = mock_response

        result = await find_duplicate_authors(["John Smith"])

        assert isinstance(result, str)
        assert "no potential duplicate" in result.lower()


class TestConsolidateAuthors:
    """Tests for consolidate_authors tool."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client."""
        mock = MagicMock()
        mock.get_with_retry = AsyncMock()
        return mock

    @pytest.fixture(autouse=True)
    def mock_client_getter(self, mock_client: MagicMock) -> Generator[None]:
        """Set mock client for all tests."""
        set_client_getter(lambda: mock_client)
        yield

    @pytest.mark.asyncio
    async def test_consolidate_authors_requires_two_ids(self) -> None:
        """Test that at least two author IDs are required."""
        result = await consolidate_authors(["single_id"])

        assert isinstance(result, str)
        assert "at least two" in result.lower()

    @pytest.mark.asyncio
    async def test_consolidate_authors_preview(self, mock_client: MagicMock) -> None:
        """Test preview mode of author consolidation."""
        author1_response: dict[str, Any] = {
            "authorId": "1",
            "name": "John Smith",
            "citationCount": 1000,
            "paperCount": 30,
            "hIndex": 15,
            "affiliations": ["MIT"],
            "externalIds": {"ORCID": "0000-0001-2345-6789"},
        }
        author2_response: dict[str, Any] = {
            "authorId": "2",
            "name": "J. Smith",
            "citationCount": 500,
            "paperCount": 20,
            "hIndex": 10,
            "affiliations": ["Stanford"],
            "externalIds": {"ORCID": "0000-0001-2345-6789"},
        }

        mock_client.get_with_retry.side_effect = [author1_response, author2_response]

        result = await consolidate_authors(["1", "2"], confirm_merge=False)

        assert isinstance(result, AuthorConsolidationResult)
        assert result.merged_author.authorId == "1"  # Primary has higher citations
        assert result.merged_author.citationCount == 1500  # Sum of citations
        assert result.merged_author.paperCount == 50  # Sum of papers
        assert result.match_type == "orcid"
        assert result.confidence == 1.0

    @pytest.mark.asyncio
    async def test_consolidate_authors_merges_affiliations(self, mock_client: MagicMock) -> None:
        """Test that affiliations are merged correctly."""
        author1_response: dict[str, Any] = {
            "authorId": "1",
            "name": "John Smith",
            "citationCount": 1000,
            "affiliations": ["MIT", "Google"],
        }
        author2_response: dict[str, Any] = {
            "authorId": "2",
            "name": "J. Smith",
            "citationCount": 500,
            "affiliations": ["Stanford", "MIT"],  # MIT duplicate
        }

        mock_client.get_with_retry.side_effect = [author1_response, author2_response]

        result = await consolidate_authors(["1", "2"])

        assert isinstance(result, AuthorConsolidationResult)
        affiliations = result.merged_author.affiliations or []
        assert "MIT" in affiliations
        assert "Google" in affiliations
        assert "Stanford" in affiliations
        assert affiliations.count("MIT") == 1  # No duplicates

    @pytest.mark.asyncio
    async def test_consolidate_authors_not_found(self, mock_client: MagicMock) -> None:
        """Test consolidation with non-existent author."""
        mock_client.get_with_retry.side_effect = NotFoundError("Not found")

        result = await consolidate_authors(["1", "2"])

        assert isinstance(result, str)
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_consolidate_authors_user_confirmed_match(self, mock_client: MagicMock) -> None:
        """Test consolidation without matching external IDs."""
        author1_response: dict[str, Any] = {
            "authorId": "1",
            "name": "John Smith",
            "citationCount": 1000,
            "externalIds": {"ORCID": "0000-0001-1111-1111"},
        }
        author2_response: dict[str, Any] = {
            "authorId": "2",
            "name": "J. Smith",
            "citationCount": 500,
            "externalIds": {"ORCID": "0000-0002-2222-2222"},
        }

        mock_client.get_with_retry.side_effect = [author1_response, author2_response]

        result = await consolidate_authors(["1", "2"])

        assert isinstance(result, AuthorConsolidationResult)
        assert result.match_type == "user_confirmed"
        assert result.confidence is None

    @pytest.mark.asyncio
    async def test_consolidate_authors_dblp_match(self, mock_client: MagicMock) -> None:
        """Test consolidation with DBLP match type detection."""
        author1_response: dict[str, Any] = {
            "authorId": "1",
            "name": "John Smith",
            "citationCount": 1000,
            "paperCount": 30,
            "hIndex": 15,
            "externalIds": {"DBLP": "homepages/s/JohnSmith"},
        }
        author2_response: dict[str, Any] = {
            "authorId": "2",
            "name": "J. Smith",
            "citationCount": 500,
            "paperCount": 20,
            "hIndex": 10,
            "externalIds": {"DBLP": "homepages/s/JohnSmith"},
        }

        mock_client.get_with_retry.side_effect = [author1_response, author2_response]

        result = await consolidate_authors(["1", "2"])

        assert isinstance(result, AuthorConsolidationResult)
        assert result.match_type == "dblp"
        assert result.confidence == 0.95

    @pytest.mark.asyncio
    async def test_consolidate_authors_external_ids_fallback(self, mock_client: MagicMock) -> None:
        """Test that external IDs fall back to non-primary author when primary has none."""
        author1_response: dict[str, Any] = {
            "authorId": "1",
            "name": "John Smith",
            "citationCount": 1000,
            "paperCount": 30,
            "externalIds": None,
        }
        author2_response: dict[str, Any] = {
            "authorId": "2",
            "name": "J. Smith",
            "citationCount": 500,
            "paperCount": 20,
            "externalIds": {"ORCID": "0000-0001-2345-6789"},
        }

        mock_client.get_with_retry.side_effect = [author1_response, author2_response]

        result = await consolidate_authors(["1", "2"])

        assert isinstance(result, AuthorConsolidationResult)
        assert result.merged_author.externalIds is not None
        assert result.merged_author.externalIds.ORCID == "0000-0001-2345-6789"


class TestFindDuplicateAuthorsDblp:
    """Tests for DBLP matching in find_duplicate_authors."""

    @pytest.fixture
    def mock_client(self) -> MagicMock:
        """Create a mock client."""
        mock = MagicMock()
        mock.get_with_retry = AsyncMock()
        return mock

    @pytest.fixture(autouse=True)
    def mock_client_getter(self, mock_client: MagicMock) -> Generator[None]:
        """Set mock client for all tests."""
        set_client_getter(lambda: mock_client)
        yield

    @pytest.mark.asyncio
    async def test_find_duplicate_authors_with_dblp_match(self, mock_client: MagicMock) -> None:
        """Test finding duplicates by DBLP match."""
        mock_response = {
            "total": 2,
            "data": [
                {
                    "authorId": "1",
                    "name": "John Smith",
                    "citationCount": 1000,
                    "externalIds": {"DBLP": "homepages/s/JohnSmith"},
                },
                {
                    "authorId": "2",
                    "name": "J. Smith",
                    "citationCount": 500,
                    "externalIds": {"DBLP": "homepages/s/JohnSmith"},
                },
            ],
        }

        mock_client.get_with_retry.return_value = mock_response

        result = await find_duplicate_authors(
            ["John Smith"], match_by_orcid=False, match_by_dblp=True
        )

        assert isinstance(result, list)
        assert len(result) == 1
        assert "same_dblp" in result[0].match_reasons[0]

    @pytest.mark.asyncio
    async def test_find_duplicate_authors_dblp_not_duplicated_with_orcid(
        self, mock_client: MagicMock
    ) -> None:
        """Test that authors matched by ORCID are not double-counted in DBLP groups."""
        mock_response = {
            "total": 2,
            "data": [
                {
                    "authorId": "1",
                    "name": "John Smith",
                    "citationCount": 1000,
                    "externalIds": {
                        "ORCID": "0000-0001-2345-6789",
                        "DBLP": "homepages/s/JohnSmith",
                    },
                },
                {
                    "authorId": "2",
                    "name": "J. Smith",
                    "citationCount": 500,
                    "externalIds": {
                        "ORCID": "0000-0001-2345-6789",
                        "DBLP": "homepages/s/JohnSmith",
                    },
                },
            ],
        }

        mock_client.get_with_retry.return_value = mock_response

        result = await find_duplicate_authors(["John Smith"])

        assert isinstance(result, list)
        # Should only have 1 group (ORCID), not 2 (ORCID + DBLP)
        assert len(result) == 1
        assert "same_orcid" in result[0].match_reasons[0]
