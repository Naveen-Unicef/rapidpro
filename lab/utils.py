from django.db import connection


def username_to_database(username):
    """
    Convert username to format accepted by database username.

    The database cannot accept username in email format, because that we change some characters:
    @ => __at__
    . => __dot__
    foo@bar.com => foo__at__bar__dot__com
    """
    return username.replace('@', '__at__').replace('.', '__dot__')


def database_user_exists(username):
    """
    Check if postgres database user exists.
    """
    with connection.cursor() as cursor:
        select_user_sql = "SELECT COUNT(*) FROM pg_catalog.pg_user WHERE usename = %s"
        cursor.execute(select_user_sql, [username, ])
        return cursor.fetchone()[0] > 0
