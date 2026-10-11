import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
RAW = os.path.join(HERE, "fixtures", "raw_mini")
SNAPSHOT = os.path.join(RAW, "团队快照", "team_snapshot_20261005.json")
NEWS = os.path.join(RAW, "news-data")


def run(args):
    proc = subprocess.run(
        [sys.executable, *args],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc


@pytest.fixture(scope="module")
def outputs(tmp_path_factory):
    out = tmp_path_factory.mktemp("pipeline")
    data_dir = out / "result"
    run([
        "scripts/import_snapshot.py",
        "--snapshot", SNAPSHOT,
        "--news-data", NEWS,
        "--output", str(data_dir),
        "--location-query", "off",
    ])
    run(["scripts/validate_snapshot.py", "--data", str(data_dir / "data.json"),
         "--output", str(data_dir / "validation")])
    run(["scripts/build_map.py", "--data", str(data_dir / "data.json"),
         "--output", str(data_dir / "map")])
    site = data_dir / "site" / "data.json"
    run(["pipeline/site/build_site_data.py", "--input", str(data_dir / "data.json"),
         "--output", str(site)])
    return data_dir, site


def test_import_validate_map_and_site_exit_zero(outputs):
    data_dir, site = outputs
    assert (data_dir / "data.json").is_file()
    assert (data_dir / "validation" / "validation_report.json").is_file()
    assert (data_dir / "map").is_dir()
    assert site.is_file()


def test_site_data_is_slim_and_has_frontend_shape(outputs):
    _, site = outputs
    with open(site, encoding="utf-8") as handle:
        doc = json.load(handle)
    assert set(doc) == {"metadata", "teams", "tables"}
    assert len(doc["teams"]) == len(doc["tables"]["teams"]) > 0
    assert doc["tables"]["evidence"], "fixture should carry news evidence"
    assert all(len(row.get("summary", "")) <= 200 for row in doc["tables"]["evidence"])
    assert site.stat().st_size < 40 * 1024 * 1024
