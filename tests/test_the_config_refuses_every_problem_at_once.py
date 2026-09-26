"""The configuration collects every problem and refuses once.

Incidents, 2026-09-26, found by reading the deploy rather than by a failure.

  * `ENABLE_GROBID` defaulted to true, and no GROBID service runs in the container
    this ships in. deploy-backend.yml carried `set_env_key ENABLE_GROBID false`
    with the comment "No GROBID service runs on this box" -- a workaround for a
    default that was simply wrong, re-applied on every deploy.
  * `ENABLE_NEO4J` starts happily with no `NEO4J_PASSWORD`, and Neo4j's own default
    password is `neo4j`, so the profile that is off by default is one env var away
    from being on and open.
  * `APP_ENV=production` with no `API_KEY` serves every `/api` route to the
    internet. `api_key` is `None` by default and `warn_if_unauthenticated()` logs a
    line, which is not a refusal.
  * `CORS_ORIGINS` accepts `*`, which the middleware comment already calls out as
    wrong, in a field with no validation.

Terminus B1 is the shape of the fix: a boot that reports one fault per restart
never reaches the ones after it. `Settings.problems()` gathers them all;
`refuse_if_misconfigured()` decides once. B3 supplies the hidden default, B6 the
cross-setting invariants, B7 the refusal rather than a fallback, P12 the sentinels
on the traversal limits.

The two severities matter and are tested separately: `fatal` refuses to start,
`report` starts and says so. A guard that refused on everything would be turned
off within a week, and one that refused on nothing would be the status quo.

Ported from Terminus B1, B3, B6, B7, B8, B15, P12, C11. See `guards/ledger.json`.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "src" / "citegraph" / "config.py"

FATAL = "fatal"
REPORT = "report"


def _module():
    """config.py imported fresh, so the Settings class is this file's reading of
    it and not something cached by another test's import."""
    spec = importlib.util.spec_from_file_location("config_under_inspection", CONFIG)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(spec.name, None)
    return module


def settings(**overrides):
    """A Settings built from overrides alone. The ambient environment and any .env
    on this machine are deliberately not consulted: a guard whose expectations
    depend on the operator's shell is a guard that passes for the wrong reason."""
    module = _module()
    return module.Settings(_env_file=None, **overrides)


def fatal_texts(**overrides) -> list[str]:
    return [text for severity, text in settings(**overrides).problems() if severity == FATAL]


def report_texts(**overrides) -> list[str]:
    return [text for severity, text in settings(**overrides).problems() if severity == REPORT]


def test_a_correct_configuration_has_no_problems_at_all():
    """The negative control. If a well-formed development and a well-formed
    production both produced findings, the guard would be noise and would be muted."""
    assert settings(app_env="development").problems() == [], \
        f"a default development configuration reported {settings(app_env='development').problems()}"

    good = settings(app_env="production", api_key="k" * 32,
                    cors_origins="https://citegraph-nlp.pages.dev",
                    openalex_email="someone@example.org")
    assert good.problems() == [], f"a correct production configuration reported {good.problems()}"


def test_production_with_no_api_key_refuses():
    """The open-API case. `warn_if_unauthenticated()` logs a line about this; a log
    line is not a refusal."""
    problems = fatal_texts(app_env="production", api_key="",
                           cors_origins="https://citegraph-nlp.pages.dev")
    assert any("API_KEY is empty" in text for text in problems), \
        f"production with no API_KEY did not refuse: {problems}"


def test_production_with_a_wildcard_cors_origin_refuses():
    found = fatal_texts(app_env="production", api_key="k" * 32, cors_origins="*")
    assert any("'*'" in text for text in found), \
        f"a wildcard CORS origin in production did not refuse: {found}"


def test_neo4j_enabled_without_a_password_refuses_and_a_placeholder_refuses_too():
    """Terminus B24: a repo-committed fallback key is obfuscation. `neo4j` is the
    vendor's own default password."""
    missing = fatal_texts(app_env="production", api_key="k" * 32, enable_neo4j=True,
                          neo4j_password="")
    assert any("NEO4J_PASSWORD is empty" in text for text in missing), \
        f"neo4j with no password did not refuse: {missing}"

    for placeholder in ("neo4j", "password", "changeme", "Your_password"):
        found = fatal_texts(app_env="production", api_key="k" * 32, enable_neo4j=True,
                            neo4j_password=placeholder)
        assert any("placeholder" in text or "vendor default" in text for text in found), \
            f"the placeholder password {placeholder!r} was accepted while neo4j was on: {found}"

    # ...and is only a warning while the profile is off. A developer whose .env
    # still carries the template's `NEO4J_PASSWORD=password` with neo4j disabled
    # is not misconfigured, and refusing there broke this suite on 2026-09-26.
    idle = report_texts(enable_neo4j=False, neo4j_password="password")
    assert any("placeholder" in text for text in idle), \
        f"an unused placeholder password was not reported: {idle}"
    assert fatal_texts(enable_neo4j=False, neo4j_password="password") == [], \
        "an unused placeholder password refused to start"


def test_grobid_pointing_at_localhost_is_reported_but_does_not_refuse():
    """The live incident. It is a `report` rather than a `fatal` on purpose: an
    operator who really does run GROBID on localhost should be able to, and a
    refusal here would be turned off rather than fixed."""
    found = report_texts(enable_grobid=True, grobid_url="http://localhost:8070")
    assert any("ENABLE_GROBID" in text for text in found), \
        f"GROBID aimed at localhost was not reported: {found}"
    assert fatal_texts(enable_grobid=True, grobid_url="http://localhost:8070") == [], \
        "a GROBID URL pointing at localhost refused to start, which is not this guard's call"

    remote = settings(enable_grobid=True, grobid_url="http://grobid:8070")
    assert not any("ENABLE_GROBID" in text for _, text in remote.problems()), \
        "a GROBID URL pointing at a real service was reported"


def test_grobid_is_off_by_default():
    """The default itself. It was True, which is why the deploy had to force it off
    on every run."""
    module = _module()
    assert module.Settings.model_fields["enable_grobid"].default is False, \
        "ENABLE_GROBID is on by default again, so the deploy's override is load-bearing"
    assert "set_env_key ENABLE_GROBID false" in \
        (ROOT / ".github" / "workflows" / "deploy-backend.yml").read_text(encoding="utf-8"), \
        "the deploy's ENABLE_GROBID override is gone; check the default is still right"


def test_every_problem_is_collected_before_anything_refuses():
    """Terminus B1: one restart per fault is how the second fault survives. A
    configuration wrong in four ways must report four, not one."""
    found = fatal_texts(app_env="production", api_key="", cors_origins="*",
                        enable_neo4j=True, neo4j_password="", default_max_total_papers=0)
    assert len(found) >= 4, f"four faults produced {len(found)}: {found}"
    assert any("API_KEY" in t for t in found)
    assert any("CORS_ORIGINS" in t for t in found)
    assert any("NEO4J_PASSWORD" in t for t in found)
    assert any("DEFAULT_MAX_TOTAL_PAPERS" in t for t in found)


def test_the_limits_are_sentinels_rather_than_silent_defaults():
    """Terminus P12. A depth of zero is not a shallow traversal, it is no traversal,
    and nobody would notice until a graph came back empty."""
    for field, value in (("default_backward_depth", 0), ("default_forward_depth", -1),
                         ("default_max_total_papers", 0)):
        found = fatal_texts(**{field: value})
        assert any(field.upper() in text for text in found), \
            f"{field}={value} was accepted: {found}"

    deep = settings(default_backward_depth=50)
    assert any("hops" in text for text in report_texts(default_backward_depth=50)), \
        "a fifty-hop default traversal was not reported"

    bad_weights = fatal_texts(weight_alpha=1.5)
    assert any("WEIGHT_ALPHA" in text for text in bad_weights), \
        f"a weight above 1 was accepted: {bad_weights}"


def test_an_unrecognised_environment_is_reported_rather_than_assumed():
    """Terminus B3: no hidden default. 'staging' is not development, and treating
    it as development is how an open API gets exposed."""
    found = report_texts(app_env="staging")
    assert any("APP_ENV" in text for text in found), f"APP_ENV=staging was not reported: {found}"
    assert fatal_texts(app_env="staging") == [], \
        "an unrecognised APP_ENV refused to start; it should be reported, because only " \
        "'production' is a claim about the internet"


def test_the_app_refuses_on_a_fatal_fault_and_starts_on_a_report_only_one():
    """The wiring, at the consumer rather than at the definition: the refusal has to
    happen where the app is built, or `problems()` is a method nobody calls."""
    source = (ROOT / "src" / "citegraph" / "api" / "main.py").read_text(encoding="utf-8")
    assert "settings.refuse_if_misconfigured()" in source, \
        "the app builds without asking the configuration whether it is safe to start"

    good = settings(app_env="production", api_key="k" * 32,
                    cors_origins="https://citegraph-nlp.pages.dev")
    good.refuse_if_misconfigured()  # must not raise

    with pytest.raises(SystemExit) as refusal:
        settings(app_env="production", api_key="").refuse_if_misconfigured()
    assert "REFUSING TO START" in str(refusal.value)
    assert "API_KEY" in str(refusal.value)
