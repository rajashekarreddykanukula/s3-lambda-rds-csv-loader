# S3 → Lambda → RDS CSV Loader

A serverless data pipeline on AWS. When a CSV file is uploaded to the
`incoming/` folder of an S3 bucket, an S3 event triggers a Python Lambda
function that reads the file and upserts the rows into an RDS MySQL table.

## Architecture
S3 (incoming/*.csv) → Lambda (Python 3.13 + pymysql layer) → RDS MySQL

## Tech stack
AWS S3, AWS Lambda, Amazon RDS (MySQL), Python, boto3, PyMySQL

## Project files
- `lambda_function.py` – Lambda handler
- `sql/create_table.sql` – database and table creation
- `sample/countries_sample.csv` – example input

## Setup
1. Create the RDS MySQL instance and run `sql/create_table.sql`.
2. Create a Lambda function (Python 3.13) and attach a `pymysql` layer.
3. Set environment variables: `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`.
4. Attach `AmazonS3ReadOnlyAccess` to the Lambda execution role.
5. Add an S3 trigger: prefix `incoming/`, suffix `.csv`.
6. Upload a CSV and check the CloudWatch logs.

## CSV format
Columns: `CountryName, CountryCode, BirthRate, InternetUsers, IncomeGroup`.
Header matching ignores case, spaces and underscores.

## Behavior
- Re-uploading a file updates existing rows (upsert on `country_code`).
- Non-CSV files are skipped.
- Credentials are read from environment variables, never stored in code.
