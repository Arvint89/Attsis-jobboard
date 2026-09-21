"""JB-6: salary extraction from description text + pay-period sanity."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "engine"))
import pytest
import facets
import sources

CASES = [
    ("The base salary range for this role is $100,000 - $150,000 USD.", "$100,000\u2013$150,000 USD/year"),
    ("Compensation: CAD 95,000 to 120,000 per year", "$95,000\u2013$120,000 CAD/year"),
    ("Salary: $120K\u2013$140K", "$120,000\u2013$140,000/year"),
    ("Pay: $32.50 - $38 per hour", "$32.50\u2013$38/hour"),
    ("Salary range: $85,000", "$85,000/year"),
    ("The pay range is $150,000\u2013$220,000 CAD annually", "$150,000\u2013$220,000 CAD/year"),
    ("We raised $5,000,000 in funding.", ""),
    ("401k matching and $2,000 learning budget", ""),
    ("Series B of $40M led by X. Salary is competitive.", ""),
    ("", ""),
]


@pytest.mark.parametrize("text,expected", CASES)
def test_salary_from_text(text, expected):
    assert facets.salary_from_text(text) == expected


def test_getro_hourly_period_that_is_really_annual():
    # GHD on Communitech: 10,238,100 cents "per hour" is obviously a yearly figure
    job = {"compensation_public": True, "compensation_amount_min_cents": 10238100,
           "compensation_amount_max_cents": 15238100, "compensation_currency": "CAD",
           "compensation_period": "hour"}
    assert sources._salary(job).endswith("CAD/year")


def test_getro_real_hourly_stays_hourly():
    job = {"compensation_public": True, "compensation_amount_min_cents": 5500,
           "compensation_amount_max_cents": 5800, "compensation_currency": "CAD",
           "compensation_period": "hour"}
    assert sources._salary(job) == "$55\u2013$58 CAD/hour"
