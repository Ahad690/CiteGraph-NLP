"""The key an operator sets must be the key the code reads.

This is its own file because it is its own class of bug: an alias mismatch does
not raise, it reads as a missing key, and a missing key is indistinguishable
from "not configured yet". So the failure mode is a capability that is silently
off rather than an error.

The name under test is the one the VENDOR documents. A person following
TypeSafe's setup page sets TYPESAFE_API_KEY; if the code reads JEV_API_KEY, the
feature simply never turns on and nothing says why.
"""
from __future__ import annotations

import pytest

from citegraph.config import Settings

FAKE = "not-a-real-key" + "0" * 20


class TestItReadsTheVendorVariableName:
    def test_typesafe_api_key_populates_the_jev_key(self, monkeypatch):
        """The documented name is the one that has to work."""
        monkeypatch.setenv("TYPESAFE_API_KEY", FAKE)
        assert Settings().jev_api_key == FAKE

    def test_the_vendor_name_does_not_leak_into_a_serialised_config(self, monkeypatch):
        """Reading by an alias must not change what model_dump emits, or a
        config echoed into a log or a response would carry the field name
        rather than the environment name the operator set."""
        monkeypatch.setenv("TYPESAFE_API_KEY", FAKE)
        assert "jev_api_key" in Settings().model_dump()

    def test_the_field_name_still_works_in_process(self):
        """populate_by_name. Without it, adding the alias above would have
        broken every Settings(jev_api_key=...) caller and every test."""
        assert Settings(jev_api_key=FAKE).jev_api_key == FAKE

    def test_absent_key_is_none_rather_than_an_error(self, monkeypatch):
        """Not configured is a normal state, not a crash. A deployment with no
        key must behave exactly as it did before the provider existed."""
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
        monkeypatch.delenv("JEV_API_KEY", raising=False)
        assert Settings().jev_api_key is None


class TestItStaysOffWithoutAKey:
    def test_enabled_but_unkeyed_leaves_the_field_empty(self, monkeypatch):
        """enable_jev=true with no key must not raise at config time. The
        capability is gated on the KEY, not only on the flag."""
        monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
        monkeypatch.delenv("JEV_API_KEY", raising=False)
        config = Settings(enable_jev=True)
        assert config.enable_jev is True
        assert not config.jev_api_key

    @pytest.mark.parametrize("flag", ["enable_jev", "enable_glm"])
    def test_both_providers_default_off(self, monkeypatch, flag):
        for name in ("TYPESAFE_API_KEY", "GLM_API_KEY"):
            monkeypatch.delenv(name, raising=False)
        config = Settings()
        assert getattr(config, flag) is False, f"{flag} must ship off"
