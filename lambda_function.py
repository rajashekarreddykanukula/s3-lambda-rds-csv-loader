import csv
import io
import os
import urllib.parse
import boto3
import pymysql

s3 = boto3.client("s3")

HEADER_MAP = {
    "country_code": "country_code", "countrycode": "country_code", "code": "country_code",
    "country_name": "country_name", "countryname": "country_name", "country": "country_name",
    "birth_rate": "birth_rate", "birthrate": "birth_rate", "birthrate": "birth_rate",
    "internet_users": "internet_users", "internetusers": "internet_users", "internetusers": "internet_users",
    "income_group": "income_group", "incomegroup": "income_group", "incomegroup": "income_group",
}

def to_decimal(value):
    value = (value or "").strip()
    return float(value) if value else None

def get_connection():
    return pymysql.connect(
        host=os.environ["DB_HOST"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        connect_timeout=10,
        charset="utf8mb4",
    )

def get_files(event):
    """Return a list of (bucket, key) from either a manual test event or an S3 trigger event."""
    if "Records" in event:  # S3 trigger
        return [
            (r["s3"]["bucket"]["name"],
             urllib.parse.unquote_plus(r["s3"]["object"]["key"]))
            for r in event["Records"]
        ]
    return [(event["bucket"], event["key"])]  # manual test

def load_csv(bucket, key):
    obj = s3.get_object(Bucket=bucket, Key=key)
    text = obj["Body"].read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    mapping = {h: HEADER_MAP[h.strip().lower()]
               for h in reader.fieldnames if h.strip().lower() in HEADER_MAP}
    missing = {"country_code", "country_name"} - set(mapping.values())
    if missing:
        raise ValueError(f"CSV is missing columns: {missing}. Found: {reader.fieldnames}")

    rows = []
    for r in reader:
        d = {mapping[h]: r[h] for h in mapping}
        code = (d.get("country_code") or "").strip()
        if not code:
            continue
        rows.append((
            code[:3],
            (d.get("country_name") or "").strip(),
            to_decimal(d.get("birth_rate")),
            to_decimal(d.get("internet_users")),
            (d.get("income_group") or "").strip() or None,
        ))
    return rows

SQL = """
    INSERT INTO country_indicators
        (country_code, country_name, birth_rate, internet_users, income_group)
    VALUES (%s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        country_name = VALUES(country_name),
        birth_rate = VALUES(birth_rate),
        internet_users = VALUES(internet_users),
        income_group = VALUES(income_group)
"""

def lambda_handler(event, context):
    conn = get_connection()
    total = 0
    try:
        for bucket, key in get_files(event):
            if not key.lower().endswith(".csv"):
                print(f"Skipping non-CSV file: {key}")
                continue
            rows = load_csv(bucket, key)
            with conn.cursor() as cur:
                cur.executemany(SQL, rows)
            conn.commit()
            total += len(rows)
            print(f"Loaded {len(rows)} rows from s3://{bucket}/{key}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return {"statusCode": 200, "rows_processed": total}
