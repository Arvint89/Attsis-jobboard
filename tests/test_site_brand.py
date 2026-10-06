"""JB-173 webpage rename to Attsis Job Board.

Static checks that site/index.html ships with 'Attsis Job Board' in the
<title>, the h1 (both the initial markup and the JS templates that
rebuild it after a CV loads), and the welcome h2. Tenant override is
intentionally NOT changed — when a tenant JSON sets `name`, the brand
stays white-label (e.g. 'LEDC · Job Board')."""
import os

INDEX = os.path.join(os.path.dirname(__file__), "..", "site", "index.html")


def _read():
    with open(INDEX, encoding="utf-8") as f:
        return f.read()


def test_title_tag_is_attsis_job_board():
    assert "<title>Attsis Job Board</title>" in _read()


def test_h1_default_markup_is_attsis_job_board():
    html = _read()
    assert '<h1 id="h1"><b>Attsis Job Board</b></h1>' in html


def test_welcome_h2_is_attsis_job_board():
    assert "Welcome to Attsis Job Board" in _read()


def test_js_h1_templates_use_attsis_job_board():
    # Two templates rebuild #h1 after a profile loads; both must say
    # 'Attsis Job Board' so the brand survives a CV load on the default view.
    html = _read()
    assert html.count("Attsis Job Board</b>`") >= 2, (
        "both JS templates (`${who?who+' · ':''}Attsis Job Board`) must be renamed"
    )


def test_tenant_override_still_uses_tenant_name_only():
    # White-label invariant: when a tenant is active, operator brand hides.
    # applyTenantBrand() should display `${name} · Job Board`, NOT
    # `${name} · Attsis Job Board`.
    html = _read()
    assert "`<b>${name} \\u00b7 Job Board</b>`" in html, (
        "tenant mode must keep 'Job Board' (not 'Attsis Job Board') so the "
        "operator brand doesn't leak into white-label views"
    )
