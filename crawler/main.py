import datetime
import shutil
import subprocess
from PyPDF2 import PdfFileReader

from io import StringIO
from pathlib import Path
import pandas as pd

import psycopg2 as pg
import tabula
import re

from src.requests_helpers import requests_retry_session
from src.db_helpers import check_if_table_exists, check_if_date_exists_in_zip_table, get_latest_date_from_zip_table, \
    copy_from_stringio

COVID_BY_ZIP_URL = r"https://www.sandiegocounty.gov/content/dam/sdc/hhsa/programs/phs/Epidemiology/COVID-19%20Summary%20of%20Cases%20by%20Zip%20Code.pdf"
SQL_TABLE_NAME = 'cases_by_zip'
MAX_DOWNLOADS = 10


def extract_pdf(root: Path):
    for path in root.glob('*'):
        if path.suffix == '.pdf':
            return path
        else:
            return extract_pdf(path)


if __name__ == '__main__':
    connection = pg.connect(dbname='postgres',
                            user='postgres',
                            host='localhost',
                            port=5432,
                            password='sdcovid')
    with connection as conn:
        if not check_if_table_exists(conn, SQL_TABLE_NAME):
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

    data_dir = Path(__file__).parent.joinpath('./data')
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir()

    with connection as conn:
        latest_date = get_latest_date_from_zip_table(conn)
    today = datetime.datetime.now()

    from_datestr = latest_date.strftime('%Y%m%d')
    to_datestr = today.strftime('%Y%m%d')

    res = subprocess.run([
        'waybackpack',
        '--list',
        '--from-date', from_datestr,
        '--to-date', to_datestr,
        '--user-agent', 'waybackpack-1up+sdcounty@posteo.net',
        COVID_BY_ZIP_URL
    ], capture_output=True)
    urls = res.stdout.decode().split()
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

    with connection as conn:
        for nx, timestamp_dir in enumerate(data_dir.glob('*')):
            if nx == MAX_DOWNLOADS:
                break
            pdf_file = extract_pdf(timestamp_dir)
            header_data = PdfFileReader(open(pdf_file, 'rb')).getPage(0).extractText()
            data_raw = tabula.read_pdf(pdf_file, lattice=True, multiple_tables=False).to_csv()
            try:
                start_row = ['Case Count' in x for x in data_raw.split('\n')].index(True)
            except ValueError:
                start_row = ['Zip Code,Count' in x for x in data_raw.split('\n')].index(True)
            data = pd.read_csv(StringIO('\n'.join(data_raw.split('\n')[start_row:])))
            print(data.head(3))
            if '1' in data.columns:
                data = data.drop(columns=['1'])
            if 'Rate per 100,000*' in data.columns:
                data = data.drop(columns=['Rate per 100,000*'])

            date_token = re.findall(r'Data through ([0-9]+)/([0-9]+)/([0-9]+)', header_data)[0]
            date = datetime.datetime(year=int(date_token[2]), month=int(date_token[0]), day=int(date_token[1]))

            if check_if_date_exists_in_zip_table(conn, date):
                print('Date {} already exists in table.'.format(date))
                shutil.rmtree(timestamp_dir)
                continue
            tbl_start_row = 0


            def get_zip_cols(start, end):
                col_data = data.iloc[tbl_start_row:, start:end]
                col_data.columns = ['zip', 'cases']
                try:
                    first_non_zip_nx = [re.match(r'[0-9]+', str(x)) is not None for x in col_data['zip']].index(False)
                    col_data = col_data.iloc[:first_non_zip_nx, :]
                except ValueError:
                    pass
                col_data = col_data.astype({'zip': int, 'cases': float})
                col_data.insert(0, 'date', date)
                return col_data


            zip_columns = []
            for col_pairs in range(int(data.shape[1] / 2)):
                zip_columns.append(get_zip_cols(col_pairs * 2, (col_pairs + 1) * 2))
            zip_data = pd.concat(zip_columns, axis=0).reset_index(drop=True)
            print(zip_data.head(2))
            ret_code = copy_from_stringio(conn, zip_data, SQL_TABLE_NAME)  #

            shutil.rmtree(timestamp_dir)
            print('Added data from {} to database.'.format(date))

    print('done')
