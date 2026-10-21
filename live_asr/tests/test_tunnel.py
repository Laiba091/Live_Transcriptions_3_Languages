from app.core.tunnel import extract_url


def test_finds_cloudflare_link_in_output():
    line = "2026-10-19T09:00:00Z INF |  https://brave-lion-cat-fox.trycloudflare.com                    |"
    assert extract_url(line) == "https://brave-lion-cat-fox.trycloudflare.com"


def test_ignores_other_lines():
    assert extract_url("INF Requesting new quick Tunnel on trycloudflare.com...") is None
    assert extract_url("INF Visit https://www.cloudflare.com/website-terms/") is None


def test_ignores_cloudflare_api_address_in_errors():
    line = 'ERR Error unmarshaling QuickTunnel response: error="..." url=https://api.trycloudflare.com/tunnel'
    assert extract_url(line) is None
