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


def test_canada_share_uses_the_fetched_board_not_the_pool():
    # JB-87: Carbon Engineering had 0 roles in the current pool, so the old pool-based share was 0%
    # and a Squamish, BC company was held back as "foreign". Use the live-fetched jobs instead.
    fetched = [{"location": "Squamish, BC, Canada"}, {"location": "Squamish, BC, Canada"}, {"location": "Houston, TX"}]
    assert pd.canada_share(fetched) == 0.67
    assert pd.canada_share([]) == 0.0
    assert pd.canada_share([{"location": "Bangalore, India"}]) == 0.0


def test_report_name_per_platform():
    assert pd.report_name("2026-10-12", None) == "PROMOTION_2026-10-12.md"
    assert pd.report_name("2026-10-12", "jazzhr") == "PROMOTION_2026-10-12_jazzhr.md"


def test_city_falls_back_to_the_fetched_board():
    fetched = [{"location": "Squamish, BC, Canada"}, {"location": "Squamish, BC, Canada"}, {"location": "Remote"}]
    assert pd.city_from_jobs(fetched) == "Squamish"
    assert pd.city_from_jobs([{"location": "Remote"}, {"location": "Multiple Countries"}]) == ""
