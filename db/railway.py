import psycopg2
import os

DATABASE_URL = "postgresql://postgres:rpwhtKVvffybMqtZvszgOvNzeBSIcRva@mainline.proxy.rlwy.net:55828/railway"

SQL_FILE = os.path.join(os.path.dirname(__file__), "002_algo_record_table.sql")

def push():
    with open(SQL_FILE, "r") as f:
        sql = f.read()

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.close()
    print("Done.")

if __name__ == "__main__":
    push()
