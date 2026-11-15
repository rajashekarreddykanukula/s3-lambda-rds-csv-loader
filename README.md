# S3 → Lambda → RDS CSV Loader

A serverless data pipeline on AWS. When a CSV file is uploaded to the
`incoming/` folder of an S3 bucket, an S3 event triggers a Python Lambda
function that reads the file and upserts the rows into an RDS MySQL table.

## Architecture
S3 (incoming/*.csv) → Lambda (Python 3.13 + pymysql layer) → RDS MySQL

## Tech stack
AWS S3, AWS Lambda, Amazon RDS (MySQL), Python, boto3, PyMySQL

## Project files
- `lambda_function.py` – Lambda handler (handles S3 trigger events and manual test events)
- `requirements.txt` – Python dependency used to build the layer
- `sql/create_table.sql` – database and table creation
- `sample/countries_sample.csv` – example input
- `config/s3-notification.json` – S3 trigger definition (optional, for CLI setup)

## Setup

### 1. Database
Create an RDS MySQL instance (default VPC, **Public access: Yes** for MySQL Workbench).
Run `sql/create_table.sql` to create the `world_data` database and the
`country_indicators` table.

### 2. Build the pymysql Lambda layer
Lambda's Python runtime includes boto3 but not PyMySQL, so it is packaged as a layer.
PyMySQL is pure Python, so the same layer works on any Python 3.x runtime.

1. Open **AWS CloudShell** (`>_` icon). Its region must match the Lambda's region,
   or the layer won't appear in the Lambda console.
2. Run:
   ```bash
   mkdir -p python
   pip install -r requirements.txt -t python/
   zip -r pymysql-layer.zip python
   aws lambda publish-layer-version \
     --layer-name pymysql \
     --zip-file fileb://pymysql-layer.zip \
     --compatible-runtimes python3.13
   ```
   The folder must be named `python/`; Lambda only looks for libraries there.
3. Confirm the output contains `LayerVersionArn`.

### 3. Create the Lambda function
- Runtime: **Python 3.13**
- Layers → Add a layer → Custom layers → `pymysql` (latest version)
- Configuration → General: **Timeout 60 s**, Memory 256 MB
- Paste `lambda_function.py` and click **Deploy**

### 4. Environment variables
| Key | Value |
|---|---|
| `DB_HOST` | RDS endpoint (`<instance>.<id>.<region>.rds.amazonaws.com`) |
| `DB_USER` | master username |
| `DB_PASSWORD` | master password |
| `DB_NAME` | `world_data` |

Never commit real values.

### 5. Permissions
Attach `AmazonS3ReadOnlyAccess` to the Lambda execution role.

### 6. Networking (practice setup)
- Lambda runs **outside a VPC**, so it reaches S3 with no extra setup.
- Lambda reaches RDS over its public endpoint, so the RDS security group needs an
  inbound rule for MySQL/Aurora, port 3306. Allow **My IP** for Workbench.
  Lambda has no fixed IP, so this setup also needed `0.0.0.0/0`, which exposes the
  database. Use it only briefly, with a strong password, and remove it afterwards.
- **Production alternative:** attach Lambda to the VPC with the same security group
  as RDS (self-referencing rule), and add an **S3 Gateway endpoint**, because a
  VPC-attached Lambda has no internet access.

### 7. S3 trigger
Lambda → Add trigger → S3:
- Bucket: your bucket
- Event type: All object create events (`s3:ObjectCreated:*`)
- Prefix: `incoming/`
- Suffix: `.csv`

CLI alternative (replace the placeholders):
```bash
aws lambda add-permission \
  --function-name <FUNCTION_NAME> \
  --statement-id s3-invoke \
  --action lambda:InvokeFunction \
  --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::<BUCKET_NAME>

aws s3api put-bucket-notification-configuration \
  --bucket <BUCKET_NAME> \
  --notification-configuration file://config/s3-notification.json
```
Do not write output files back to the same bucket and prefix, or the trigger will loop.

## CSV format
Columns: `CountryName, CountryCode, BirthRate, InternetUsers, IncomeGroup`.
Header matching ignores case, spaces and underscores.

## Testing
**Manual test event** (Lambda → Test):
```json
{"bucket": "<BUCKET_NAME>", "key": "incoming/awsdata.csv"}
```
**Real trigger:** upload a *new* CSV to `incoming/` (the trigger fires only on new
uploads), wait about 10 seconds, then check CloudWatch logs for
`Loaded N rows from s3://...` and run
`SELECT COUNT(*) FROM world_data.country_indicators;`.

## Behavior
- Re-uploading a file updates existing rows (upsert on `country_code`).
- Non-CSV files are skipped.
- Credentials are read from environment variables, never stored in code.

## Troubleshooting
| Error | Cause / fix |
|---|---|
| `No module named 'pymysql'` | Layer not attached, or layer runtime doesn't match the function |
| Layer not listed in Lambda | CloudShell and Lambda are in different regions |
| `Can't connect to MySQL server (timed out)` | Security group doesn't allow Lambda's traffic on 3306, or RDS isn't publicly accessible |
| Task timed out reading S3 | Lambda is in a VPC without an S3 Gateway endpoint |
| `KeyError: 'bucket'` | Old code still deployed, or test event format doesn't match the code. Click **Deploy** |
| `CSV is missing columns` | CSV headers don't map to the expected columns |
| Workbench error 1175 on DELETE | Safe update mode. Use `TRUNCATE TABLE` or `SET SQL_SAFE_UPDATES = 0;` |
| Trigger doesn't fire | Prefix/suffix mismatch, or file was already in the bucket (only new uploads fire) |

## Cleanup
Remove the `0.0.0.0/0` rule from the RDS security group and delete the RDS
instance when finished, to avoid charges.
