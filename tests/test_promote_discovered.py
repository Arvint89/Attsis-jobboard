"""JB-86 promote_discovered: parent-board rejection + alert parsing (no network)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import promote_discovered as pd  # noqa: E402


def test_slug_matches_company():
    assert pd.name_matches_slug("Avidbots", "avidbots")
    assert pd.name_matches_slug("7shifts", "7shifts")
    assert pd.name_matches_slug("Magnet Forensics", "magnetforensics")
    assert pd.name_matches_slug("CoLab Software", "colabsoftware")
    assert pd.name_matches_slug("FISPAN", "fispan")


def test_parent_or_acquirer_boards_rejected():
    # ✅ real cases from live AUTO-PROMOTE samples (2026-10-09)
    assert not pd.name_matches_slug("Clearpath Robotics", "rockwellautomation")
    assert not pd.name_matches_slug("Algolux", "torcrobotics")
    assert not pd.name_matches_slug("Canalyst", "alphasense")
    assert not pd.name_matches_slug("InitLive Inc.", "bloomerang")
    assert not pd.name_matches_slug("Finn AI", "glia")


def test_parse_alerts():
    a = ["AUTO-PROMOTE: 'Avidbots' seen in 12 sweeps via bamboohr (via Communitech) -- add to engine/companies.json "
         "(sample: https://avidbots.bamboohr.com/careers/878)", "roles kept fell 10 -> 1 (>30%)"]
    r = pd.parse_alerts(a)
    assert r == [{"name": "Avidbots", "sweeps": 12, "via": "bamboohr (via Communitech)",
                  "sample": "https://avidbots.bamboohr.com/careers/878"}]
