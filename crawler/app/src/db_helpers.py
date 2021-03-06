import os
from io import StringIO
from pathlib import Path
from typing import Dict

import pandas as pd
import psycopg2


def get_db_credentials() -> Dict[str, str]:
    defaults = {
        'DB_HOST': 'localhost',
        'DB_NAME': 'postgres',
        'DB_USER': 'postgres',
        'DB_PASSWORD': 'sdcovid'
    }

    for var_name in defaults.keys():
        try:
            defaults[var_name] = os.environ[var_name].strip()
        except KeyError:
            pass
    return defaults


def seed_table(conn):
    print('Seeding table...', end='')
    seed_file = Path(__file__).parent.joinpath('../data/cases_by_zip_snapshot.csv')
    data = pd.read_csv(seed_file, header=None)
    data.columns = ['date', 'zip', 'cases']
    data.index = data['date']
    from main import SQL_TABLE_NAME
    ret_code = copy_from_stringio(conn, data, SQL_TABLE_NAME)
    print('done')


def check_if_table_exists(conn, table_name):
    with conn.cursor() as cur:
        cur.execute("""
             SELECT EXISTS (
               SELECT FROM information_schema.tables
               WHERE table_name = '{}'
            );
        """.format(table_name))
        exists = cur.fetchone()[0]
    return exists


def check_if_date_exists_in_zip_table(conn, date):
    with conn.cursor() as cur:
        cur.execute("SELECT EXISTS (SELECT 1 FROM cases_by_zip WHERE date = Date(\'{}\'));".format(date))
        exists = cur.fetchone()[0]
    return exists


def get_latest_date_from_zip_table(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT date FROM cases_by_zip ORDER BY date DESC LIMIT 1")
        latest = cur.fetchone()
    if not latest:
        return None
    else:
        return pd.to_datetime(latest[0])


def copy_from_stringio(conn, df, table):
    """
    Here we are going save the dataframe in memory
    and use copy_from() to copy it to the table

    Copied from https://naysan.ca/2020/06/21/pandas-to-postgresql-using-psycopg2-copy_from/
    """
    # save dataframe to an in memory buffer
    buffer = StringIO()
    df.to_csv(buffer, index=False, header=False)
    buffer.seek(0)

    with conn.cursor() as cursor:
        try:
            cursor.copy_from(buffer, table, sep=",")
            conn.commit()
        except (Exception, psycopg2.DatabaseError) as error:

            print("Error: %s" % error)
            conn.rollback()
            cursor.close()
            return 1
    return 0
