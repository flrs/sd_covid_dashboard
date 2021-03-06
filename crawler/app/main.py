import datetime
import warnings
from time import sleep
import shutil
import subprocess
import os

import psycopg2
from PyPDF2 import PdfFileReader

from io import StringIO
from pathlib import Path
import pandas as pd

import psycopg2 as pg
import tabula
import re
import os

from src.requests_helpers import requests_retry_session
from src.db_helpers import check_if_table_exists, check_if_date_exists_in_zip_table, get_latest_date_from_zip_table, \
    copy_from_stringio, seed_table

from src.db_helpers import get_db_credentials

COVID_BY_ZIP_URL = r"https://www.sandiegocounty.gov/content/dam/sdc/hhsa/programs/phs/Epidemiology/COVID-19%20Summary%20of%20Cases%20by%20Zip%20Code.pdf"
SQL_TABLE_NAME = 'cases_by_zip'
MAX_DOWNLOADS = 100
DEBUG_DATE_ONLY = None  # example: '2020-08-30' or None to disable
SEED_ONLY = True if 'SEED_ONLY' in os.environ else False


def extract_pdf(root: Path):
    for path in root.glob('*'):
        if path.suffix == '.pdf':
            return path
        else:
            return extract_pdf(path)


if __name__ == '__main__':
    retries = 0
    print('Trying to connect to database')
    db_credentials = get_db_credentials()
    while True:
        try:
            connection = pg.connect(dbname=db_credentials['DB_NAME'],
                                    user=db_credentials['DB_USER'],
                                    host=db_credentials['DB_HOST'],
                                    port=5432,
                                    password=db_credentials['DB_PASSWORD'])
        except psycopg2.OperationalError as e:
            sleep(10)
            if retries == 10:
                raise ConnectionError('Could not connect to database.')
            else:
                warnings.warn('Error when connecting to database: {}'.format(str(e)))
            retries += 1
        else:
            print('Connection successful.')
            break

    with connection as conn:
        print('Check if table exists...')
        if not check_if_table_exists(conn, SQL_TABLE_NAME):
            print('Creating table since it does not exist.')
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE cases_by_zip 
                        (
                            date date, 
                            zip integer, 
                            cases float,
                            PRIMARY KEY (date, zip)
                        );
                """)
                conn.commit()
            if 'INIT_DB' not in os.environ:
                seed_table(conn)
        else:
            print('Table exists.')
    print('Done checking table.')
    if SEED_ONLY:
        while True:
            sleep(60)

    data_dir = Path(__file__).parent.joinpath('./downloaded')
    skip_download = False
    if data_dir.exists():
        if 'INIT_DB' in os.environ and any(data_dir.iterdir()):
            skip_download = True
        else:
            shutil.rmtree(data_dir)
    data_dir.mkdir(exist_ok=True)

    with connection as conn:
        latest_date = get_latest_date_from_zip_table(conn)
    if not latest_date:
        latest_date = datetime.datetime(year=2018, month=1, day=1)
    today = datetime.datetime.now()
    if 'INIT_DB' in os.environ:
        print('Running crawler in INIT_DB mode, downloading all data except for the last 14 days.')
        today -= datetime.timedelta(days=14)

    if DEBUG_DATE_ONLY:
        print('DEBUG: Only downloading the following date: {}'.format(DEBUG_DATE_ONLY))
        latest_date = pd.to_datetime(DEBUG_DATE_ONLY)
        today = latest_date

    from_datestr = latest_date.strftime('%Y%m%d')
    to_datestr = today.strftime('%Y%m%d')

    if not skip_download:
        res = subprocess.run([
            'waybackpack',
            '--list',
            '--from-date', from_datestr,
            '--to-date', to_datestr,
            '--uniques-only',
            '--user-agent', 'waybackpack-1up+sdcounty@posteo.net',
            COVID_BY_ZIP_URL
        ], capture_output=True)
        urls = res.stdout.decode().split()
        if 'INIT_DB' not in os.environ:
            urls = urls[:min([MAX_DOWNLOADS, len(urls)])]
        print('Downloading {} files...'.format(len(urls)))

        for url in urls:
            try:
                print('Downloading {}'.format(url))
                response = requests_retry_session().get(url)
            except Exception as x:
                print('Download for {} failed:'.format(url), x.__class__.__name__)
                continue
            if response.status_code != 200:
                print('Download for {} failed with status code {}.'.format(url, response.status_code))
                continue
            target_dir = data_dir.joinpath('./{}'.format(re.findall(r'/web/([0-9]+)/', url)[0]))
            target_dir.mkdir()
            with open(data_dir.joinpath('./{}/download.pdf'.format(re.findall(r'/web/([0-9]+)/', url)[0])), 'wb') as file:
                file.write(response.content)
    else:
        print('Skipping download since files already exist in target folder.')

    with connection as conn:
        for timestamp_dir in sorted(data_dir.glob('*')):
            pdf_file = extract_pdf(timestamp_dir)
            header_data = PdfFileReader(open(pdf_file, 'rb')).getPage(0).extractText()
            data_raw = tabula.read_pdf(pdf_file, lattice=True, multiple_tables=False).to_csv()
            try:
                start_row = ['Case Count' in x for x in data_raw.split('\n')].index(True)
            except ValueError:
                start_row = ['Zip Code,Count' in x for x in data_raw.split('\n')].index(True)
            data = pd.read_csv(StringIO('\n'.join(data_raw.split('\n')[start_row:])))
            print(data.head(3))
            if data.shape[1] == 7:
                print('There was a problem with processing data in {}.'.format(timestamp_dir))
                shutil.rmtree(timestamp_dir)
                continue
            for x in range(10):
                if str(x) in data.columns:
                    data = data.drop(columns=[str(x)])
            if 'Rate per 100,000*' in data.columns:
                data = data.drop(columns=['Rate per 100,000*'])

            date_token = re.findall(r'Data through ([0-9]+)/([0-9]+)/([0-9]+)', header_data)[0]
            date = datetime.datetime(year=int(date_token[2]), month=int(date_token[0]), day=int(date_token[1]))

            if check_if_date_exists_in_zip_table(conn, date) and not DEBUG_DATE_ONLY:
                print('Date {} already exists in table.'.format(date))
                shutil.rmtree(timestamp_dir)
                continue
            tbl_start_row = 0


            def get_zip_cols(start, end):
                col_data = data.iloc[tbl_start_row:, start:end]
                col_data.columns = ['zip', 'cases']
                try:
                    non_zip_nxs = [nx for nx, x in enumerate(col_data['zip']) if re.match(r'[0-9]+', str(x)) is None]
                    if non_zip_nxs:
                        col_data = col_data.drop(index=non_zip_nxs)
                except ValueError:
                    pass
                col_data['cases'] = col_data['cases'].apply(lambda x: x.replace(',', '') if isinstance(x, str) else x)
                col_data = col_data.astype({'zip': int, 'cases': float})
                col_data.insert(0, 'date', date)
                return col_data

            zip_columns = []
            for col_pairs in range(int(data.shape[1] / 2)):
                zip_columns.append(get_zip_cols(col_pairs * 2, (col_pairs + 1) * 2))
            zip_data = pd.concat(zip_columns, axis=0).reset_index(drop=True)
            print(zip_data.head(2))
            ret_code = copy_from_stringio(conn, zip_data, SQL_TABLE_NAME)

            shutil.rmtree(timestamp_dir)
            print('Added data from {} to database.'.format(date))

        if 'INIT_DB' in os.environ:
            pd.read_sql('SELECT * FROM {}'.format(SQL_TABLE_NAME), conn)\
                .to_csv(Path(__file__).parent.joinpath('./data/cases_by_zip_snapshot.csv'), index=False, header=False)
    print('done')
