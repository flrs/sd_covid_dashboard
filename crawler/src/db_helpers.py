from io import StringIO

import pandas as pd
import psycopg2


def check_if_table_exists(conn, table_name):
    with conn.cursor() as cur:
        cur.execute("""
             SELECT EXISTS (
               SELECT FROM information_schema.tables
               WHERE table_name = '{}'
            );
        """.format(table_name))
        exists = cur.fetchone()
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