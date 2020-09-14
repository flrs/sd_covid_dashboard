from functools import lru_cache
from pathlib import Path
import pandas as pd
import numpy as np


@lru_cache
def get_population_per_zip():
    demos = pd.read_excel(Path(__file__).parent.joinpath('../data/estimate_2019_zip_1600028105323.xlsx'),
                          sheet_name='Population')

    population_per_zip = demos[demos['YEAR'] == 2019].groupby('ZIP')['POPULATION'].sum()
    return population_per_zip


def add_cases_per_100k_col(data_with_zip: pd.DataFrame) -> pd.DataFrame:
    data = data_with_zip.copy()

    bad_zips = [92092, 92168]  # These are PO boxes
    for zip_ in data['zip']:
        if len(data[(data['zip'] == zip_)]) == 1:
            if np.all(data[(data['zip'] == zip_)]['cases'] == 0.0):
                bad_zips.append(zip_)
    data = data[~data['zip'].isin(bad_zips)]

    population_per_zip = get_population_per_zip()
    data['population'] = [population_per_zip[zip_] for zip_ in data['zip']]
    data['cases_per_100k'] = data['cases'] / (data['population'] / 100000)
    data = data.drop(columns=['population'])
    return data
