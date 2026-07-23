from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["db"] in {"connected", "unavailable"}


def test_security_headers_present_on_every_response(client: TestClient) -> None:
    response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "Permissions-Policy" in response.headers


def test_hsts_only_advertised_behind_a_proxy_that_terminated_https(
    client: TestClient,
) -> None:
    plain = client.get("/health")
    assert "Strict-Transport-Security" not in plain.headers

    behind_tls_proxy = client.get("/health", headers={"X-Forwarded-Proto": "https"})
    assert "Strict-Transport-Security" in behind_tls_proxy.headers
