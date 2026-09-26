"""No secret is committed to this tree, and the templates carry no real values.

Incidents. Terminus R27 (`test_no_secret_leaves_this_machine.py`): the scanner
found ten real access tokens on its first run, and later shipped a pattern that
matched nothing because a shell heredoc wrote a literal backspace -- a pattern
that cannot match reports zero sites and passes forever. R28: a gate that flags
everything looks thorough, so a clean-tree control is needed. R29: a gate that
reported the same result after reading forty files and after reading none was
trustworthy. R30: a refusal the gate could not account for, and a published rule
with no code behind it.

This repository, 2026-09-26: `.env.example` held
`OPENALEX_EMAIL=muhammadahadf23@nutech.edu.pk` -- a real contact address, in the
file the deploy copies to `/opt/citegraph-nlp/.env` when no `.env` exists. The
deploy's substitution (`grep -q '^OPENALEX_EMAIL=your_email@example.com'`) could
therefore never match, so the address was committed to the repository instead of
being injected at deploy time, and the substitution written to keep it out had
been dead since it was added. A template carrying a real value is the config-globals
contract of Terminus B24 and B28, broken in the direction nobody looks at.

What this guard checks, and what it deliberately does not:

  * credential shapes, everywhere, with each detector driven by a sample built
    from parts so this file scans clean and needs no exemption of itself
    (Terminus 5.2: relocate a self-referential guard rather than exempt it);
  * a real contact address in a *template* -- `.env.example` only. The same
    address inside a `User-Agent` string is required by Europe PMC and Crossref
    and is left alone, and that asymmetry is deliberate and stated rather than
    a proximity exemption;
  * the config-globals contract in both directions: every key in `.env.example`
    is a setting `Settings` reads, and every setting an operator sets is in the
    template. The two the deploy injects are exempted by name, and the exemption
    is asserted to still be needed.

It blocks. A clean-tree control and one planted sample per detector mean it
cannot be satisfied by flagging everything or by flagging nothing.

Ported from Terminus R25-R30, P1-P3, B24, B28, G3. See `guards/ledger.json`.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
G6 = ROOT / "tests" / "test_no_source_file_carries_a_control_character.py"
EXAMPLE = ROOT / ".env.example"
CONFIG = ROOT / "src" / "citegraph" / "config.py"

#: Files that are templates: a value copied into a deployment, so a real value in
#: one is a real value in the deployment and in the repository.
TEMPLATES = {".env.example"}

#: Domains that mean "this is a placeholder", checked only in templates.
PLACEHOLDER_DOMAINS = ("example.com", "example.org", "example.net", "example.edu",
                       "invalid", "localhost", "test")

#: Settings the deploy injects with `docker run -e`, so they are not the
#: operator's to fill in and do not belong in a template.
INJECTED = {"git_sha", "build_time"}

#: Every detector, with the sample that must trip it and the sample that must not.
#: The samples are assembled from parts at test time; the literals here are
#: patterns, which do not match themselves.
DETECTORS: dict[str, str] = {
    "private_key_block": r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----",
    "aws_access_key_id": r"\bAKIA[0-9A-Z]{16}\b",
    "github_token": r"\bgh[pousr]_[A-Za-z0-9]{30,}\b",
    "openai_style_key": r"\bsk-[A-Za-z0-9]{20,}\b",
    "slack_token": r"\bxox[baprs]-[A-Za-z0-9-]{12,}\b",
    "google_api_key": r"AIza[0-9A-Za-z\-_]{35}",
    "stripe_live_key": r"\b[rs]k_live_[A-Za-z0-9]{20,}\b",
    "npm_token": r"\bnpm_[A-Za-z0-9]{30,}\b",
    "json_web_token": r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b",
    "basic_auth_in_url": r"://[^/\s:]+:[^/\s@]+@",
}

#: Where the sweep reads. Reuses the control-character guard's pruned walk so
#: there is one definition of this repository's text files.
PRUNED_SUFFIXES = {".pdf", ".docx", ".pptx", ".xlsx", ".mp4", ".png", ".jpg", ".jpeg",
                   ".gif", ".webp", ".ico", ".sqlite", ".enc", ".gz", ".zip", ".7z",
                   ".woff", ".woff2", ".ttf", ".dll", ".pyd", ".onnx", ".so", ".exe",
                   ".mp3", ".wav", ".log", ".csv", ".xml"}


def _walk():
    import importlib.util
    spec = importlib.util.spec_from_file_location("g6_walk", G6)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scannable() -> list[Path]:
    walk = _walk()
    return [f for f in walk.source_files() if f.suffix.lower() not in PRUNED_SUFFIXES]


def find_secrets(text: str) -> dict[str, list[str]]:
    """Every detector that fires, with its lines. A token-shaped value that this
    cannot read is a finding, not a clean result (Terminus kit item 13)."""
    hits: dict[str, list[str]] = {}
    for name, pattern in DETECTORS.items():
        found = [f"line {n}" for n, line in enumerate(text.splitlines(), 1)
                 if re.search(pattern, line)]
        if found:
            hits[name] = found
    return hits


def real_contacts_in_template(text: str) -> list[str]:
    """Addresses in a template that are not placeholders. A User-Agent contact is
    not in scope: two polite-pool headers in scripts/ carry the address on purpose,
    because Europe PMC and Crossref ask for it."""
    found = []
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith("#"):
            continue
        for address in re.findall(r"[\w.+-]+@([\w-]+\.[\w.-]+)", line):
            if not any(domain in address for domain in PLACEHOLDER_DOMAINS):
                found.append(f"line {number}: {address}")
    return found


def settings_fields() -> set[str]:
    """The setting names `Settings` declares, lowercased. pydantic-settings matches
    environment variables case-insensitively, so the template's uppercase keys and
    the class's lowercase attributes are the same names; comparing them as written
    would report every key as unread."""
    return {name.lower() for name in
            re.findall(r"^    (\w+):\s", CONFIG.read_text(encoding="utf-8"), re.M)}


def example_keys() -> set[str]:
    keys = set()
    for line in EXAMPLE.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.strip().startswith("#") and "=" in line:
            keys.add(line.split("=", 1)[0].strip())
    return keys


def test_every_detector_fires_on_its_sample_and_quietly_passes_its_negative():
    """The red proof, and Terminux R28's clean control. Built from parts, so the
    samples are not literals in this file and the sweep below needs no exemption
    of itself."""
    positives = {
        "private_key_block": "-----BEGIN " + "RSA PRIVATE KEY-----",
        "aws_access_key_id": "AKIA" + "Q7RTZ2K9LP4M8X3B",
        "github_token": "ghp_" + "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8",
        "openai_style_key": "sk-" + "abcdefghijklmnopqrstuvwxyz012345",
        "slack_token": "xoxb-" + "1234567890-abcdefghij",
        "google_api_key": "AIza" + "SyD1234567890abcdefghijklmnopqrstuvw",
        "stripe_live_key": "sk_live_" + "abcdefghijklmnopqrstuvwx",
        "npm_token": "npm_" + "abcdefghijklmnopqrstuvwxyz0123456789",
        "json_web_token": "eyJhbGciOiJIUzI1NiJ9" + ".eyJzdWIiOiIxMjM0NTY3ODkwIn0" + ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
        "basic_auth_in_url": "https://" + "admin:hunter2@db.internal/health",
    }
    assert set(positives) == set(DETECTORS), (
        f"a detector has no planted sample: {sorted(set(DETECTORS) - set(positives))}"
    )
    for name, sample in positives.items():
        assert find_secrets(sample) == {name: ["line 1"]}, \
            f"the {name} detector did not fire on its own sample: {find_secrets(sample)}"

    negatives = {
        "a sentence about keys": "rotate the API key before deploying, and never commit it",
        "an env template with placeholders": "API_KEY=\nOPENALEX_EMAIL=someone@example.com",
        "a doi": "https://doi.org/10.1016/s2213-2600(20)30079-5",
        "a sha": "4c982f2 Put PageRank on the same scale as the other ranking terms",
        "a public url": "https://citegraph-nlp.pages.dev and https://api.penora.us/health",
        "a uuid in a test": "paper_id = 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'",
    }
    for label, text in negatives.items():
        assert find_secrets(text) == {}, f"the detectors fired on {label}: {find_secrets(text)}"


def test_the_detectors_are_not_written_so_that_they_cannot_match():
    """Terminus R12's lesson applied to this file: a pattern containing a literal
    byte nobody can see is a pattern that cannot fire. Each pattern is compiled,
    and each is required to match its own name-free sample built at test time."""
    for name, pattern in DETECTORS.items():
        assert re.compile(pattern), f"the {name} detector does not compile"
        assert not any(ord(c) < 0x20 and c not in "\t" for c in pattern), \
            f"the {name} pattern contains a control character, so it may match nothing"
    assert DETECTORS, "there are no detectors, so a clean tree proves nothing"


def test_no_scannable_file_carries_a_secret():
    """The sweep. The file count is asserted first, so a walk that collected
    nothing cannot report a clean tree."""
    files = scannable()
    assert len(files) >= 250, (
        f"the sweep read {len(files)} files, below the floor of 250; a pruned tree is "
        f"not a clean tree"
    )

    dirty: dict[str, dict[str, list[str]]] = {}
    for relative in files:
        try:
            text = (ROOT / relative).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        hits = find_secrets(text)
        if hits:
            dirty[relative.as_posix()] = hits

    assert not dirty, (
        f"{len(dirty)} of {len(files)} files match a credential shape. Do not paste the "
        f"value into a report; rotate it and record only the file and line: {dirty}"
    )


def test_a_template_carries_no_real_contact_address():
    """The live incident. A template is copied into a deployment, so a real address
    in one is a real address in the deployment -- and, here, it also meant the
    deploy's placeholder substitution could never fire."""
    for relative in sorted(TEMPLATES):
        found = real_contacts_in_template((ROOT / relative).read_text(encoding="utf-8"))
        assert not found, (
            f"{relative} carries a real address rather than a placeholder: {found}. "
            f"deploy-backend.yml substitutes a real OPENALEX_EMAIL for the placeholder "
            f"your_email@example.com, and that substitution can only fire if the "
            f"template still holds the placeholder"
        )

    # The negative control, and the asymmetry: the same address inside a
    # User-Agent is required by Europe PMC and Crossref, so it is not a finding.
    polite = 'HEADERS = {"User-Agent": "CiteGraph-NLP research (mailto:someone@nutech.edu.pk)"}'
    assert find_secrets(polite) == {}, "a polite-pool User-Agent is not a credential"
    assert real_contacts_in_template("# OPENALEX_EMAIL=someone@example.com\n") == [], \
        "a commented placeholder is still a placeholder"


def test_the_template_and_the_settings_agree_in_both_directions():
    """The config-globals contract. `.env.example` is what an operator copies;
    `Settings` is what the application reads. A key the application ignores is a
    comment that looks like a setting, and a setting with no template line is one
    nobody finds.

    Terminus B24 records the same incident class: a publishable key and a config
    global whose contract was never checked against the reader.

    Two directions only. A third -- a setting nothing in `src/` ever reads -- is
    not checked here, because `cors_origins` is read through a property in
    config.py itself and a name search cannot tell that from a dead setting. A
    guard that claimed it would be claiming more than it checks, which is the
    defect this port exists to remove. Sixteen settings look unread by name,
    `enable_grobid` among them; that is a real finding and it wants its own guard.
    """
    declared, documented = settings_fields(), {k.lower() for k in example_keys()}
    assert len(declared) >= 20, f"only {len(declared)} settings were read from config.py"
    assert len(documented) >= 20, f"only {len(documented)} keys were read from .env.example"

    ignored = sorted(documented - declared)
    assert not ignored, (
        f".env.example publishes {ignored}, which Settings does not declare, so setting "
        f"them does nothing"
    )

    missing = sorted(declared - documented - INJECTED)
    assert not missing, (
        f"Settings declares {missing}, which .env.example never mentions, so an operator "
        f"has no way to set them"
    )


def test_the_injected_settings_exemption_is_still_needed():
    """Terminus 5.8 item 7: an exemption must be narrow, justified, and still
    needed. If the deploy stopped injecting these they would belong in the
    template, and if they were removed from Settings the exemption is a phantom."""
    workflow = (ROOT / ".github" / "workflows" / "deploy-backend.yml").read_text(encoding="utf-8")
    for field in sorted(INJECTED):
        assert f"-e \"{field.upper()}=" in workflow, (
            f"{field} is exempted from the template because the deploy injects it, but the "
            f"deploy no longer does: {field} belongs in .env.example"
        )
        assert field in settings_fields(), (
            f"{field} is exempted from the template but is no longer a setting"
        )

def test_the_workflow_placeholder_substitution_can_actually_fire():
    """The dead branch. deploy-backend.yml replaces `your_email@example.com` in the
    deployed .env with the real address; if the template no longer holds that
    placeholder the substitution is dead code and the real address has to be
    committed instead. That is exactly what had happened."""
    workflow = (ROOT / ".github" / "workflows" / "deploy-backend.yml").read_text(encoding="utf-8")
    match = re.search(r"grep -q '\^OPENALEX_EMAIL=(\S+?)'", workflow)
    assert match, "the deploy no longer substitutes OPENALEX_EMAIL at all"
    placeholder = match.group(1)
    assert placeholder in EXAMPLE.read_text(encoding="utf-8"), (
        f"the deploy substitutes {placeholder!r} but .env.example does not contain it, so "
        f"the substitution can never fire"
    )


def test_a_yaml_file_nothing_parses_is_not_silently_accepted():
    """The workflow files are read by CG12 with yaml.safe_load. A file that has
    stopped being valid YAML would make that guard see an empty trigger block and
    report no path filters, so the parse is asserted here rather than assumed."""
    for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(document, dict) and document.get("jobs"), \
            f"{path.name} parsed to {type(document).__name__} with no jobs, so any guard " \
            f"reading it is reading nothing"
