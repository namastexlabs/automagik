import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Verify `/health` returns status=healthy."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json().get("status") == "healthy"


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Verify root `/` endpoint reports online status."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json().get("status") == "online"


@pytest.mark.asyncio
async def test_openapi_schema(client):
    """`/api/v1/openapi.json` contains paths & info keys."""
    resp = client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    body = resp.json()
    assert "paths" in body and "info" in body


@pytest.mark.asyncio
async def test_swagger_docs(client):
    resp = client.get("/api/v1/docs")
    assert resp.status_code == 200
    # The docs endpoint returns HTML, verify content type header.
    assert "text/html" in resp.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_redoc_docs(client):
    resp = client.get("/api/v1/redoc")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("content-type", "") 