"""Tests for the health endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient
from src.app.main import app


@pytest.fixture
def client() -> AsyncClient:
    """Create a test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_health_returns_200_with_ok_status(client: AsyncClient) -> None:
    """AC-11: GET /health returns 200 with status ok."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
