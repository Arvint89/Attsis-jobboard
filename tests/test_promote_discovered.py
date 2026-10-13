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


def test_country_is_not_an_hq_city():
    # JB-90: StackAdapt's pool rows said "United States" -> stored as its HQ "city"
    pool = [{"company": "StackAdapt", "location_near": "United States", "industry": "other"}]
    e = pd.build_entry({"name": "StackAdapt", "sample": "https://job-boards.greenhouse.io/stackadapt/jobs/1"},
                       {"platform": "greenhouse", "slug": "stackadapt"}, pool)
    assert e["city"] == ""
    pool = [{"company": "Giatec", "location_near": "Ottawa, ON", "industry": "other"}]
    e = pd.build_entry({"name": "Giatec", "sample": "https://giatecscientific.bamboohr.com/careers/1"},
                       {"platform": "bamboohr", "slug": "giatecscientific"}, pool)
    assert e["city"] == "Ottawa"


def test_region_is_not_an_hq_city():
    # JB-90 dry run: StackAdapt -> "Alberta", Texada -> "ON" (from "Alberta, Canada" / "ON, CA")
    assert pd.city_from_jobs([{"location": "Alberta, Canada"}, {"location": "Alberta, Canada"}, {"location": "Toronto, ON"}]) == "Toronto"
    assert pd.city_from_jobs([{"location": "ON, CA"}]) == ""
    assert pd.city_from_jobs([{"location": "Texas, US"}, {"location": "United States, Remote"}]) == ""


def test_bare_remote_is_neutral_in_the_canada_share():
    # JB-90: Business Wire (San Francisco) passed only because 2 bare "Remote" jobs count as Canada
    assert pd.canada_share([{"location": "Remote"}, {"location": "Remote"}, {"location": "San Francisco, CA/Hybrid"}]) == 0.0
    # RateHub: 9 Remote + 2 Toronto -> 100% of the jobs that name a place
    assert pd.canada_share([{"location": "Remote"}] * 9 + [{"location": "Toronto, ON, Canada"}] * 2) == 1.0
    assert pd.canada_share([{"location": "Remote - Canada"}, {"location": "n/a"}, {"location": "2 Locations"}]) == 1.0
    assert pd.canada_share([{"location": "Remote"}]) == 0.0      # nothing named -> not evidence of Canada
