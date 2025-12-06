import csv
from pathlib import Path

from afcs.range_tables import RangeTable
from afcs.equipment.m109a6 import EQUIPMENT as M109A6


def test_read_rows_trims_whitespace(tmp_path: Path):
    path = tmp_path / "sample.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["range", " mill", " diff100m", " eta"])
        writer.writerow(["1000", " 1200", " 3", " 40.5"])

    rows = list(RangeTable._read_rows(path))

    assert len(rows) == 1
    assert rows[0].range == 1000
    assert rows[0].mill == 1200
    assert rows[0].diff100m == 3
    assert rows[0].eta == 40.5


def test_range_rows_cache_not_exhausted():
    table_first = RangeTable(M109A6, "low", 1)

    assert table_first.rows

    table_second = RangeTable(M109A6, "low", 1)

    assert table_second.rows
    assert table_second.rows == table_first.rows
