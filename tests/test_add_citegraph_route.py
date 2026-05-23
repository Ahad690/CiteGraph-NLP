"""Unit tests for scripts/add_citegraph_route.py — the helper that injects
the /citegraph/ Nginx route into the shared hetzner-api.duckdns.org config."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "add_citegraph_route.py"

NGINX_CONF_WITH_PENORA = """\
server {
    listen 443 ssl http2;
    server_name hetzner-api.duckdns.org;

    ssl_certificate /etc/letsencrypt/live/hetzner-api.duckdns.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hetzner-api.duckdns.org/privkey.pem;

    location /penora/ {
        rewrite ^/penora/(.*) /$1 break;
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
    }

    location /api/ {
        proxy_pass http://localhost:5000;
    }

    location / {
        proxy_pass http://localhost:8000;
    }
}

server {
    listen 80;
    server_name hetzner-api.duckdns.org;
    return 301 https://$server_name$request_uri;
}
"""

NGINX_CONF_BROKEN_NESTED = """\
server {
    listen 443 ssl http2;
    server_name hetzner-api.duckdns.org;

    location /penora/ {
        rewrite ^/penora/(.*) /$1 break;
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
    location /citegraph/ {
        proxy_pass http://127.0.0.1:8002/;
        proxy_set_header Host $host;
    }
    }
}
"""

NGINX_CONF_MULTIPLE_SERVERS = """\
server {
    listen 443 ssl http2;
    server_name other.example.com;

    location /penora/ {
        proxy_pass http://localhost:9999;
    }
}

server {
    listen 443 ssl http2;
    server_name hetzner-api.duckdns.org;

    location /penora/ {
        proxy_pass http://localhost:8001;
    }
}
"""

NGINX_CONF_NO_PENORA = """\
server {
    listen 443 ssl http2;
    server_name hetzner-api.duckdns.org;

    location / {
        proxy_pass http://localhost:8000;
    }
}
"""


def run_script(config_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(config_path)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_fresh_insert_after_penora(tmp_path: Path) -> None:
    conf = tmp_path / "site.conf"
    conf.write_text(NGINX_CONF_WITH_PENORA)
    proc = run_script(conf)
    assert proc.returncode == 0, proc.stderr
    text = conf.read_text()
    assert text.count("location /citegraph/ {") == 1
    # Citegraph must appear after penora and before /api/
    penora_idx = text.index("location /penora/")
    citegraph_idx = text.index("location /citegraph/")
    api_idx = text.index("location /api/")
    assert penora_idx < citegraph_idx < api_idx
    # Literal Nginx variables preserved
    assert "$host" in text
    assert "$proxy_add_x_forwarded_for" in text
    assert "$scheme" in text
    # Backend proxy URL present
    assert "proxy_pass http://127.0.0.1:8002/" in text


def test_idempotent_repair_of_broken_nested_block(tmp_path: Path) -> None:
    conf = tmp_path / "site.conf"
    conf.write_text(NGINX_CONF_BROKEN_NESTED)
    proc = run_script(conf)
    assert proc.returncode == 0, proc.stderr
    text = conf.read_text()
    # Only one citegraph block; no nesting inside penora
    assert text.count("location /citegraph/ {") == 1
    # Penora block must be balanced: its opening brace and closing brace
    # must appear before the citegraph block.
    penora_open = text.index("location /penora/")
    citegraph_open = text.index("location /citegraph/")
    between = text[penora_open:citegraph_open]
    # Within the penora→citegraph slice, '{' and '}' counts must balance
    # (penora opens with 1 '{' and must close with 1 '}' before citegraph).
    assert between.count("{") == between.count("}"), \
        f"Penora block not balanced before citegraph block:\n{between}"


def test_idempotent_rerun_does_not_duplicate(tmp_path: Path) -> None:
    conf = tmp_path / "site.conf"
    conf.write_text(NGINX_CONF_WITH_PENORA)
    assert run_script(conf).returncode == 0
    # Re-run on the already-injected config
    proc = run_script(conf)
    assert proc.returncode == 0, proc.stderr
    text = conf.read_text()
    assert text.count("location /citegraph/ {") == 1


def test_multiple_server_blocks_uses_correct_one(tmp_path: Path) -> None:
    """When there are multiple server blocks, the citegraph route must go
    into the hetzner-api one, not the other.example.com one."""
    conf = tmp_path / "site.conf"
    conf.write_text(NGINX_CONF_MULTIPLE_SERVERS)
    proc = run_script(conf)
    assert proc.returncode == 0, proc.stderr
    text = conf.read_text()
    assert text.count("location /citegraph/ {") == 1
    # The citegraph insertion must be after the hetzner-api server_name,
    # not after the other.example.com one
    other_idx = text.index("server_name other.example.com")
    hetzner_idx = text.index("server_name hetzner-api.duckdns.org")
    citegraph_idx = text.index("location /citegraph/")
    assert citegraph_idx > hetzner_idx
    # And the other.example.com server must NOT contain citegraph
    other_block_end = text.index("server_name hetzner-api.duckdns.org")
    assert "citegraph" not in text[:other_block_end]


def test_missing_penora_anchor_fails(tmp_path: Path) -> None:
    conf = tmp_path / "site.conf"
    original = NGINX_CONF_NO_PENORA
    conf.write_text(original)
    proc = run_script(conf)
    assert proc.returncode == 2
    assert "penora" in proc.stderr.lower()
    # Config must remain unchanged on failure
    assert conf.read_text() == original


def test_missing_config_file_fails(tmp_path: Path) -> None:
    proc = run_script(tmp_path / "does-not-exist.conf")
    assert proc.returncode == 1


def test_missing_hetzner_server_fails(tmp_path: Path) -> None:
    conf = tmp_path / "site.conf"
    conf.write_text("server { listen 80; server_name other.example.com; }\n")
    proc = run_script(conf)
    assert proc.returncode == 2
    assert "hetzner-api" in proc.stderr.lower()
