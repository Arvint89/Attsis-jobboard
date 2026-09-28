"""Tests for engine/skills_db.py -- the canonical titles + skills DB (JB-50).

Contract:
- load_db returns {"skills": [...], "titles": [...]} shape.
- resolve_skills / resolve_titles do whole-token matching (no substring hits).
- Aliases fold up to canonical.
- Real data/skills.json meets the acceptance thresholds (>=500 skills,
  >=500 titles).
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import skills_db as sdb  # noqa: E402


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LIVE_DB = os.path.join(REPO_ROOT, "data", "skills.json")


def _mini_db(tmp_path):
    p = os.path.join(tmp_path, "skills.json")
    payload = {
        "skills": [
            {"canonical": "C++", "aliases": ["cpp", "c plus plus", "c/c++"], "category": "language"},
            {"canonical": "FPGA", "aliases": ["field programmable gate array"], "category": "hardware"},
            {"canonical": "signal integrity", "aliases": ["si analysis"], "category": "hardware"},
        ],
        "titles": [
            {"canonical": "hardware engineer", "aliases": ["hw engineer"], "category": "hardware"},
            {"canonical": "firmware engineer", "aliases": ["firmware developer"], "category": "embedded"},
        ],
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    sdb.load_db.cache_clear()
    sdb._compiled_index.cache_clear()
    return p


# --- happy path ---------------------------------------------------------------

def test_resolve_skills_hits_canonical_via_alias(tmp_path):
    p = _mini_db(tmp_path)
    hits = sdb.resolve_skills("We use CPP daily for firmware.", path=p)
    assert "C++" in hits


def test_resolve_skills_hits_multi_word_phrase(tmp_path):
    p = _mini_db(tmp_path)
    hits = sdb.resolve_skills("Deep experience in signal integrity analysis.", path=p)
    assert "signal integrity" in hits


def test_resolve_titles_hits_alias_form(tmp_path):
    p = _mini_db(tmp_path)
    hits = sdb.resolve_titles("Job title: HW Engineer II", path=p)
    assert "hardware engineer" in hits


# --- boundary safety ----------------------------------------------------------

def test_resolve_no_substring_false_positive(tmp_path):
    """'CPP' as substring inside 'CPPFLAGS' or 'ScrappedPP' must NOT match C++."""
    p = _mini_db(tmp_path)
    hits = sdb.resolve_skills("Set CPPFLAGS to compile.", path=p)
    assert "C++" not in hits


def test_resolve_empty_text(tmp_path):
    p = _mini_db(tmp_path)
    assert sdb.resolve_skills("", path=p) == []
    assert sdb.resolve_titles("", path=p) == []


def test_resolve_missing_db_returns_empty(tmp_path):
    """A missing DB file must not crash callers -- feature degrades gracefully."""
    sdb.load_db.cache_clear()
    sdb._compiled_index.cache_clear()
    missing = os.path.join(tmp_path, "does_not_exist.json")
    assert sdb.resolve_skills("anything at all", path=missing) == []


# --- acceptance thresholds against the shipped DB -----------------------------

def test_live_db_has_at_least_500_skills():
    sdb.load_db.cache_clear()
    sdb._compiled_index.cache_clear()
    s = sdb.stats(LIVE_DB)
    assert s["skills"] >= 500, f"skills count {s['skills']} below 500 threshold"


def test_live_db_has_at_least_500_titles():
    sdb.load_db.cache_clear()
    sdb._compiled_index.cache_clear()
    s = sdb.stats(LIVE_DB)
    assert s["titles"] >= 500, f"titles count {s['titles']} below 500 threshold"


def test_live_db_wellknown_skills_present():
    """Sanity-check that canonical skills from common CVs are in the shipped DB."""
    sdb.load_db.cache_clear()
    sdb._compiled_index.cache_clear()
    text = "Python, JavaScript, Docker, Kubernetes, PostgreSQL, React, AWS, TensorFlow, Git."
    hits = set(sdb.resolve_skills(text, path=LIVE_DB))
    # Expect at least most of the well-known items to resolve.
    expected_min = {"Python", "JavaScript", "Docker", "Kubernetes", "React", "AWS", "Git"}
    missing = expected_min - hits
    assert not missing, f"live DB missing common skills: {missing}"


def test_live_db_hardware_skills_present():
    sdb.load_db.cache_clear()
    sdb._compiled_index.cache_clear()
    text = "FPGA design in Verilog with Vivado, signal integrity on PCB, altium schematic capture."
    hits = set(sdb.resolve_skills(text, path=LIVE_DB))
    expected_min = {"FPGA", "Verilog", "Vivado", "signal integrity", "PCB", "Altium"}
    missing = expected_min - hits
    assert not missing, f"live DB missing hardware skills: {missing}"


def test_live_db_wellknown_titles_present():
    sdb.load_db.cache_clear()
    sdb._compiled_index.cache_clear()
    text = "Roles: Software Engineer, Data Scientist, DevOps Engineer, Hardware Engineer."
    hits = set(sdb.resolve_titles(text, path=LIVE_DB))
    expected_min = {"software engineer", "data scientist", "devops engineer", "hardware engineer"}
    missing = expected_min - hits
    assert not missing, f"live DB missing common titles: {missing}"


# --- resolve() wrapper --------------------------------------------------------

def test_resolve_returns_dict_shape(tmp_path):
    p = _mini_db(tmp_path)
    out = sdb.resolve("firmware developer with FPGA and CPP experience", path=p)
    assert set(out.keys()) == {"skills", "titles"}
    assert "FPGA" in out["skills"] and "C++" in out["skills"]
    assert "firmware engineer" in out["titles"]


# --- JB-51: multi-word skill matching -----------------------------------------

def test_live_db_has_high_speed_design():
    """JB-51: 'high-speed design' (and its space variant) must resolve."""
    sdb.load_db.cache_clear()
    sdb._compiled_index.cache_clear()
    hyphen_hits = set(sdb.resolve_skills("Extensive high-speed design experience.", path=LIVE_DB))
    space_hits = set(sdb.resolve_skills("Extensive high speed design experience.", path=LIVE_DB))
    assert "high-speed design" in hyphen_hits
    assert "high-speed design" in space_hits


def test_live_db_multi_word_ml_concepts_present():
    """JB-51: common ML bigrams/trigrams resolve from a realistic JD sentence."""
    sdb.load_db.cache_clear()
    sdb._compiled_index.cache_clear()
    text = (
        "We build machine learning systems using deep learning, natural language "
        "processing, and computer vision, with strong data engineering and time "
        "series anomaly detection."
    )
    hits = set(sdb.resolve_skills(text, path=LIVE_DB))
    expected = {
        "machine learning", "deep learning", "natural language processing",
        "computer vision", "data engineering", "time series", "anomaly detection",
    }
    missing = expected - hits
    assert not missing, f"live DB missing ML multi-word skills: {missing}"


def test_live_db_multi_word_hardware_concepts_present():
    """JB-51: hardware/embedded multi-word phrases resolve."""
    sdb.load_db.cache_clear()
    sdb._compiled_index.cache_clear()
    text = (
        "Design power electronics with high-speed design, model predictive "
        "control, control systems, and embedded software for real-time systems."
    )
    hits = set(sdb.resolve_skills(text, path=LIVE_DB))
    expected = {
        "power electronics", "high-speed design", "model predictive control",
        "control systems", "embedded software", "real-time systems",
    }
    missing = expected - hits
    assert not missing, f"live DB missing hardware multi-word skills: {missing}"


def test_multi_word_no_partial_phrase_match(tmp_path):
    """'signal integrity' must not match 'signal' alone, nor 'integrity' alone."""
    p = _mini_db(tmp_path)
    only_first = sdb.resolve_skills("We look for signal experience.", path=p)
    only_second = sdb.resolve_skills("Integrity is important here.", path=p)
    assert "signal integrity" not in only_first
    assert "signal integrity" not in only_second


def test_multi_word_boundary_safe(tmp_path):
    """Multi-word skill must not match inside a longer compound token."""
    p = os.path.join(tmp_path, "skills.json")
    payload = {
        "skills": [
            {"canonical": "data pipeline", "aliases": [], "category": "multi_word_concepts"},
        ],
        "titles": [],
    }
    with open(p, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    sdb.load_db.cache_clear()
    sdb._compiled_index.cache_clear()
    # Should match with normal boundaries...
    assert "data pipeline" in sdb.resolve_skills("Own the data pipeline.", path=p)
    # ...but NOT when either token is glued to a longer word (metadata-pipeline should fail).
    assert "data pipeline" not in sdb.resolve_skills("Metadata pipelineXY runs nightly.", path=p)
