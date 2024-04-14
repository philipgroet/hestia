
import psycopg2
from psycopg2.extras import RealDictCursor

from secrets import DB_DB, DB_HOST, DB_USER, DB_PASSWORD, DB_PORT


def query_db(query, params=[], fetchOne=False):
# TODO error handling
    db = psycopg2.connect(database=DB_DB,
                            host=DB_HOST,
                            user=DB_USER,
                            password=DB_PASSWORD,
                            port=DB_PORT)
    
    cursor = db.cursor(cursor_factory=RealDictCursor)
    cursor.execute(query, params)
    
    # Try, because not all queries will return data
    try:
        if fetchOne:
            result = cursor.fetchone()
        else:
            result = cursor.fetchall()
    except:
        result = None
    
    db.commit()
    cursor.close()
    db.close()
    
    return result