"""Tests for tools/statcan_cbc_download.py -- CBC ZIP fetch + cache (JB-57)."""
import io
import os
import sys
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import statcan_cbc_download as dl  # noqa: E402


# --- extract_csv_from_zip -----------------------------------------------------

def _build_zip(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in members.items():
            z.writestr(name, data)
    return buf.getvalue()


def test_extract_returns_data_csv_not_metadata():
    zip_bytes = _build_zip({
        "33101176.csv": b"REF_DATE,GEO,VALUE\n2026-06,London,1\n",
        "33101176_MetaData.csv": b"metadata",
    })
    csv = dl.extract_csv_from_zip(zip_bytes)
    assert b"REF_DATE" in csv
    assert b"metadata" not in csv


def test_extract_falls_back_to_only_csv():
    zip_bytes = _build_zip({"onlymeta.csv": b"metadata,columns\n"})
    csv = dl.extract_csv_from_zip(zip_bytes)
    assert csv.startswith(b"metadata,columns")


def test_extract_raises_when_no_csv_present():
    zip_bytes = _build_zip({"readme.txt": b"nothing"})
    try:
        dl.extract_csv_from_zip(zip_bytes)
    except ValueError as e:
        assert "no CSV" in str(e)
    else:
        raise AssertionError("expected ValueError when ZIP has no CSV")


# --- download (fetcher injected) ---------------------------------------------

def test_download_writes_cache_path(tmp_path):
    zip_bytes = _build_zip({"33101176.csv": b"REF_DATE,GEO,VALUE\n"})
    calls: list[str] = []

    def fake_fetch(url: str) -> bytes:
        calls.append(url)
        return zip_bytes

    out = dl.download(period="2026-06", fetcher=fake_fetch, cache_dir=str(tmp_path))
    assert os.path.exists(out)
    assert out.endswith(os.path.join("33101176_2026-06.csv"))
    with open(out, "rb") as f:
        assert f.read().startswith(b"REF_DATE")
    assert calls == [dl.ZIP_URL]


def test_cache_path_encodes_period(tmp_path):
    p = dl.cache_path(period="2024-12", cache_dir=str(tmp_path))
    assert p.endswith("33101176_2024-12.csv")
