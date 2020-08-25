import pandas as pd

from src.db_helpers import get_cases_by_date


def test_get_cases_by_date():
    res = get_cases_by_date(date='2020-06-30')
    assert isinstance(res, pd.Series)
    assert res.shape[0] > 1
