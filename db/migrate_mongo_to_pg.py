import pymongo
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone

MONGO_URL    = "mongodb://mongo:ZqBgzncvgHgbHapAdslyYogiUhxgYWKs@shuttle.proxy.rlwy.net:24709"
MONGO_DB     = "algorecords"
MONGO_COL    = "TMS"

DATABASE_URL = "postgresql://postgres:rpwhtKVvffybMqtZvszgOvNzeBSIcRva@mainline.proxy.rlwy.net:55828/railway"

INSERT_SQL = """
    INSERT INTO algo_record (time, account, env, algo, checkbox, symbol, share, price, realize, fees)
    VALUES (%(time)s, %(account)s, %(env)s, %(algo)s, %(checkbox)s, %(symbol)s, %(share)s, %(price)s, %(realize)s, %(fees)s)
    ON CONFLICT DO NOTHING
"""

def parse_time(raw) -> datetime:
    if isinstance(raw, datetime):
        return raw if raw.tzinfo else raw.replace(tzinfo=timezone.utc)
    if isinstance(raw, dict) and "$date" in raw:
        s = raw["$date"]
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    raise ValueError(f"Unknown time format: {raw!r}")

def migrate():
    mongo  = pymongo.MongoClient(MONGO_URL)
    col    = mongo[MONGO_DB][MONGO_COL]
    total  = col.count_documents({})
    print(f"Found {total} records in MongoDB.")

    pg = psycopg2.connect(DATABASE_URL)
    pg.autocommit = False

    inserted = 0
    skipped  = 0
    batch    = []
    BATCH_SIZE = 500

    def flush(batch):
        with pg.cursor() as cur:
            psycopg2.extras.execute_batch(cur, INSERT_SQL, batch)
        pg.commit()

    for doc in col.find({}):
        try:
            row = {
                "time":     parse_time(doc["time"]),
                "account":  doc.get("account", ""),
                "env":      doc.get("env", ""),
                "algo":     doc.get("algo", ""),
                "checkbox": doc.get("checkbox"),
                "symbol":   doc.get("symbol", ""),
                "share":    int(doc.get("share", 0)),
                "price":    float(doc.get("price", 0)),
                "realize":  float(doc.get("realize", 0)),
                "fees":     float(doc.get("fees", 0)),
            }
            batch.append(row)
            inserted += 1
        except Exception as e:
            print(f"  Skipping {doc.get('_id')}: {e}")
            skipped += 1

        if len(batch) >= BATCH_SIZE:
            flush(batch)
            batch.clear()
            print(f"  {inserted} inserted so far...")

    if batch:
        flush(batch)

    pg.close()
    mongo.close()
    print(f"\nDone. Inserted: {inserted}, Skipped: {skipped}")

if __name__ == "__main__":
    migrate()
