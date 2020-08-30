from pathlib import Path
from typing import Optional

import pandas as pd

ROOT = Path(__file__).parent.parent
REPO_LINK = 'https://github.com/flrs/sd_covid_dashboard'


def _read_optional_env_file(file_name: str) -> Optional[str]:
    path = ROOT.joinpath('./data/{}'.format(file_name))
    data = None
    if path.exists():
        with open(str(path), 'r') as file:
            data = file.read()
    return data


def get_commit_hash() -> Optional[str]:
    return _read_optional_env_file('commit_hash.txt')


def get_commit_url() -> Optional[str]:
    hash = get_commit_hash()
    if not hash:
        return
    else:
        return '/'.join([REPO_LINK, 'tree', hash])


def get_commit_msg() -> Optional[str]:
    return _read_optional_env_file('commit_msg.txt')


def get_deploy_date() -> Optional[pd.datetime]:
    date = _read_optional_env_file('deploy_date.txt')
    if date:
        return pd.to_datetime(date)
