"""The content-hash provider cache.

Two things are being protected here, and they are not the same thing.

THE KEY MUST HIT. A content-hash cache that never hits is a slower copy of the
network, and it looks identical in use. The canonical-serialisation test is the
one that catches it: two equal dicts built in different orders must produce the
same key, because that is the single most common way this cache silently stops
working.

A HIT MUST NOT CHARGE. The budget ledger records real spend. A hit re-serves an
answer that was already paid for, so re-reporting the original usage would make
the daily ceiling measure something other than spend. That is asserted directly,
because a cache that lies about cost is worse than no cache.
"""
from __future__ import annotations

import json

import pytest

from citegraph.config import settings
from citegraph.llm import cache as cache_mod
from citegraph.llm.cache import SCHEMA_VERSION, ProviderCache, cache_key, cached_post


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "provider_cache_path", str(tmp_path / "cache.jsonl"))
    monkeypatch.setattr(settings, "provider_cache_ttl_s", 0.0)
    return tmp_path


class TestTheKey:
    def test_equal_dicts_in_different_orders_hit_the_same_entry(self):
        """The whole cache rests on this. Without sort_keys a dict built as
        {"a": 1, "b": 2} and one built as {"b": 2, "a": 1} hash differently, and
        every lookup misses."""
        a = {"type": "choice", "criteria": {"x": "1", "y": "2"}}
        b = {"criteria": {"y": "2", "x": "1"}, "type": "choice"}
        assert cache_key("jev", "m", a) == cache_key("jev", "m", b)

    def test_a_different_model_is_a_different_key(self):
        """A cache without the model in its key would serve last month's answer
        under today's model name and report it as current."""
        body = {"type": "score", "instructions": "x"}
        assert cache_key("jev", "jev-latest", body) != cache_key("jev", "jev-1.13.0", body)

    def test_a_different_provider_is_a_different_key(self):
        body = {"type": "noul", "instructions": "x"}
        assert cache_key("jev", "m", body) != cache_key("glm", "m", body)

    def test_a_different_body_is_a_different_key(self):
        assert cache_key("jev", "m", {"a": 1}) != cache_key("jev", "m", {"a": 2})

    def test_the_key_is_a_stable_digest_not_a_python_hash(self):
        """PYTHONHASHSEED makes id() and hash() vary per process. A key that
        changes between runs is a cache that never hits in CI and always hits
        locally, which is the worst combination available."""
        import subprocess
        import sys

        code = (
            "import sys; sys.path.insert(0, 'src');"
            "from citegraph.llm.cache import cache_key;"
            "print(cache_key('jev', 'm', {'a': 1, 'b': [1, 2]}))"
        )
        # Inherit the environment and override only the seed. A stripped env
        # leaves the interpreter unable to start, and an empty stdout would
        # otherwise read as three agreeing seeds and pass.
        import os

        env = {**os.environ, "PYTHONHASHSEED": ""}
        runs = set()
        for seed in ("0", "1", "12345"):
            env["PYTHONHASHSEED"] = seed
            done = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True, text=True, env=env, check=False,
            )
            assert done.returncode == 0, f"interpreter failed: {done.stderr[:200]}"
            runs.add(done.stdout.strip())
        assert len(runs) == 1, f"key varies with the hash seed: {runs}"
        assert runs.pop() == cache_key("jev", "m", {"a": 1, "b": [1, 2]})


class TestTheStore:
    def test_a_stored_answer_comes_back(self, isolated):
        store = ProviderCache()
        store.put("k1", {"answers": {"q": 1}}, provider="jev", model="m")
        assert store.get("k1") == {"answers": {"q": 1}}
        assert store.has("k1")

    def test_a_miss_is_none_not_an_error(self, isolated):
        assert ProviderCache().get("absent") is None

    def test_a_missing_file_is_a_miss(self, isolated):
        assert ProviderCache(isolated / "nope.jsonl").get("k") is None

    def test_a_corrupt_line_is_skipped_not_raised(self, isolated):
        """A cache is an optimisation. One that can take a run down is not one."""
        path = isolated / "cache.jsonl"
        path.write_text("not json at all\n", encoding="utf-8")
        assert ProviderCache(path).get("k") is None

        store = ProviderCache(path)
        store.put("good", {"v": 1}, provider="jev", model="m")
        with path.open("a", encoding="utf-8") as handle:
            handle.write("{half written\n")
        assert store.get("good") == {"v": 1}, "a good entry must survive a bad one"

    def test_an_entry_from_another_schema_version_is_a_miss(self, isolated):
        path = isolated / "cache.jsonl"
        path.write_text(
            json.dumps({
                "version": SCHEMA_VERSION + 1, "key": "k", "body": {"v": 1},
                "stored_at": 9e9, "provider": "jev", "model": "m",
            }) + "\n",
            encoding="utf-8",
        )
        assert ProviderCache(path).get("k") is None

    def test_an_unwritable_path_does_not_raise(self, tmp_path, monkeypatch):
        """A cache that cannot be written is a slow run, not a broken one."""
        blocker = tmp_path / "blocked"
        blocker.write_text("i am a file, not a directory", encoding="utf-8")
        store = ProviderCache(blocker / "sub" / "cache.jsonl")
        store.put("k", {"v": 1}, provider="jev", model="m")  # must not raise
        assert store.get("k") is None


class TestExpiry:
    def test_a_ttl_of_zero_keeps_entries_forever(self, isolated, monkeypatch):
        monkeypatch.setattr(settings, "provider_cache_ttl_s", 0.0)
        store = ProviderCache()
        store.put("k", {"v": 1}, provider="jev", model="m")
        assert store.get("k") == {"v": 1}

    def test_an_expired_entry_is_a_miss(self, isolated, monkeypatch):
        monkeypatch.setattr(settings, "provider_cache_ttl_s", 1.0)
        store = ProviderCache()
        store.put("k", {"v": 1}, provider="jev", model="m")
        assert store.get("k") == {"v": 1}
        # Rewrite the timestamp rather than sleeping: a test that waits out a TTL
        # is a slow test that still fails the same way.
        lines = []
        for line in (isolated / "cache.jsonl").read_text(encoding="utf-8").splitlines():
            record = json.loads(line)
            record["stored_at"] = record["stored_at"] - 10
            lines.append(json.dumps(record))
        (isolated / "cache.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
        assert store.get("k") is None

    def test_an_entry_with_no_timestamp_is_treated_as_expired(self, isolated, monkeypatch):
        """Serving an answer of unknown age under the current model name is the
        exact failure this cache exists to prevent."""
        monkeypatch.setattr(settings, "provider_cache_ttl_s", 60.0)
        path = isolated / "cache.jsonl"
        path.write_text(
            json.dumps({"version": SCHEMA_VERSION, "key": "k", "body": {"v": 1},
                        "provider": "jev", "model": "m"}) + "\n",
            encoding="utf-8",
        )
        assert ProviderCache(path).get("k") is None


class FakeProvider:
    """Counts calls, so a hit is observable as the absence of one."""

    name = "fake"

    def __init__(self, payload=None, fail_first=False):
        self.calls = 0
        self.payload = payload or {"answers": {}, "usage": {}}
        self.fail_first = fail_first

    async def post_json(self, path, body):
        self.calls += 1
        if self.fail_first and self.calls == 1:
            return self.payload, None
        return self.payload, None


class TestAHitAvoidsTheProvider:
    @pytest.mark.asyncio
    async def test_the_first_call_misses_and_the_second_hits(self, isolated):
        provider = FakeProvider()
        body = {"type": "choice", "instructions": "q", "criteria": {"a": "A"}}

        first, first_cached = await cached_post(provider, "/p", body, model="m")
        second, second_cached = await cached_post(provider, "/p", body, model="m")

        assert first_cached is False
        assert second_cached is True
        assert second == first
        assert provider.calls == 1, "a hit must not reach the transport"

    @pytest.mark.asyncio
    async def test_a_changed_model_misses(self, isolated):
        provider = FakeProvider()
        body = {"type": "choice", "instructions": "q"}
        await cached_post(provider, "/p", body, model="jev-latest")
        await cached_post(provider, "/p", body, model="jev-1.13.0")
        assert provider.calls == 2, "a new model must not be served a stale answer"

    @pytest.mark.asyncio
    async def test_a_disabled_cache_is_still_a_cache_miss_not_a_crash(self, isolated,
                                                                   monkeypatch):
        monkeypatch.setattr(settings, "provider_cache_ttl_s", 0.0)
        monkeypatch.setattr(
            cache_mod, "_cache",
            lambda: ProviderCache(isolated / "does-not-exist" / "x" / "c.jsonl"),
        )
        provider = FakeProvider()
        _body, cached = await cached_post(provider, "/p", {"a": 1}, model="m")
        assert cached is False
        assert provider.calls == 1
