from starlette.requests import Request

from app.core.rate_limit import check_rate_limit, get_client_ip, reset_rate_limits


def _make_request(headers: dict[str, str], client_host: str | None = "10.0.0.1") -> Request:
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in headers.items()]
    scope = {
        "type": "http",
        "headers": raw_headers,
        "client": (client_host, 12345) if client_host else None,
    }
    return Request(scope)


def test_get_client_ip_prefers_x_real_ip_set_by_nginx() -> None:
    request = _make_request({"x-real-ip": "203.0.113.7"}, client_host="172.19.0.5")
    assert get_client_ip(request) == "203.0.113.7"


def test_get_client_ip_falls_back_to_direct_peer_without_proxy_header() -> None:
    request = _make_request({}, client_host="203.0.113.7")
    assert get_client_ip(request) == "203.0.113.7"


def test_check_rate_limit_allows_up_to_the_configured_max() -> None:
    reset_rate_limits()
    key = "test:rate-limit-key"
    for _ in range(5):
        assert check_rate_limit(key, max_requests=5, window_seconds=60) is True
    assert check_rate_limit(key, max_requests=5, window_seconds=60) is False
