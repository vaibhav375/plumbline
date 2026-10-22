import pytest

pytestmark = pytest.mark.db


def test_wilson_lower_known_values(db):
    row = db.execute(
        "select wilson_lower(8, 10), wilson_lower(95, 100), wilson_lower(0, 0)"
    ).fetchone()
    assert row[0] == pytest.approx(0.490, abs=5e-4)
    assert row[1] == pytest.approx(0.888, abs=5e-4)
    assert row[2] is None
