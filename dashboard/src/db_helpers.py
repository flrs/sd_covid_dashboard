import os
from time import sleep
from typing import Tuple, Any, Dict, Optional

import pandas as pd
import psycopg2 as pg


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


def get_db_connection():
    retries = 0
    db_credentials = get_db_credentials()
    while True:
        try:
            connection = pg.connect(dbname=db_credentials['DB_NAME'],
                                    user=db_credentials['DB_USER'],
                                    host=db_credentials['DB_HOST'],
                                    port=5432,
                                    password=db_credentials['DB_PASSWORD'])
        except pg.OperationalError as e:
            sleep(10)
            if retries == 10:
                raise ConnectionError('Could not connect to database.')
            retries += 1
        else:
            break
    return connection


def get_cases_by_date(date=None) -> Tuple[pd.Series, Any]:
    conn = get_db_connection()
    if not date:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT date, zip, cases 
            FROM cases_by_zip 
            WHERE date = (
                SELECT date FROM cases_by_zip 
                ORDER BY date DESC 
                LIMIT 1)
            """)
            res = cur.fetchall()
            date = res[0][0]
            res = [r[1:] for r in res]
    else:
        date = pd.to_datetime(date)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT zip, cases FROM cases_by_zip 
                WHERE date = Date('{}')
            """.format(str(date)))
            res = cur.fetchall()
    res = pd.Series([r[1] for r in res], index=[r[0] for r in res])
    res.name = 'cases'
    res.index.name = 'zip'
    return res, date


def get_cases_per_week_by_zip(zip: Optional[int]=None) -> pd.DataFrame:
    conn = get_db_connection()
    with conn.cursor() as cur:
        if not zip:
                cur.execute("""
                    SELECT
                        date_trunc('week', date) as week,
                        zip,
                        MAX(cases)-MIN(cases)
                    FROM cases_by_zip
                    GROUP BY week, zip
                    ORDER BY week, zip
                """)
        else:
            cur.execute("""
                SELECT
                    date_trunc('week', date) as week,
                    zip,
                    MAX(cases)-MIN(cases)
                FROM cases_by_zip
                WHERE zip == {}
                GROUP BY week, zip
                ORDER BY week, zip
            """.format(zip))
        res = cur.fetchall()
    res = pd.DataFrame(res, columns= ['date', 'zip', 'cases'])
    return res

def get_cases_by_week() -> pd.DataFrame:
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            WITH cases_per_zip_per_week AS (SELECT
                date_trunc('week', date) as week,
                zip,
                MAX(cases)-MIN(cases) as cases
            FROM cases_by_zip
            GROUP BY week, zip)
            SELECT
                week,
                SUM(cases),
                STDDEV(cases)
            FROM cases_per_zip_per_week
            GROUP BY week
            ORDER BY week
            """)
        res = cur.fetchall()
    res = pd.DataFrame(res, columns=['date', 'cases', 'cases_stddev'])
    return res


def get_cases_by_dow() -> pd.DataFrame:
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("""
            WITH cases_per_dow AS (
                WITH cases_per_date AS (
                SELECT
                    date,
                    SUM(cases) as case_sum
                FROM cases_by_zip
                GROUP BY date
                ORDER BY date)
                SELECT extract(DOW FROM date)                        as dow,
                       case_sum - lag(case_sum) OVER (ORDER BY date) as cases
                FROM cases_per_date
            )
            SELECT
                dow,
                SUM(cases)/COUNT(cases) as all_cases
            FROM cases_per_dow
            GROUP BY dow
            ORDER BY dow
            """)
        res = cur.fetchall()
    res = pd.DataFrame(res, columns=['dow', 'cases'])
    return res
