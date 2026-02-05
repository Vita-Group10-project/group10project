import json
import boto3
import time

athena = boto3.client("athena")

# -------------------------
# CONFIG
# -------------------------
DATABASE = "reporting_zone"

SOURCE_DATABASE = "reporting_zone"
SOURCE_TABLE = "open_payments_curated"

DEST_DATABASE = "reporting_zone"
DEST_TABLE = "open_payments_demo_report"

# Athena query output location (query logs/results)
ATHENA_RESULTS = "s3://reporting-zone-00/iceberg_table_from_lambda/athena-results/"

# ✅ Iceberg managed table location (this worked for you)
ICEBERG_LOCATION = "s3://reporting-zone-00/iceberg_table_from_lambda/open_payments_demo_report/"


# -------------------------
# HELPERS
# -------------------------
def run_query(sql: str):
    resp = athena.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": DATABASE},
        ResultConfiguration={"OutputLocation": ATHENA_RESULTS},
    )
    return resp["QueryExecutionId"]


def wait_for_query(qid: str, poll_seconds=2, timeout_seconds=900):
    start = time.time()
    while True:
        resp = athena.get_query_execution(QueryExecutionId=qid)
        state = resp["QueryExecution"]["Status"]["State"]

        if state in ["SUCCEEDED", "FAILED", "CANCELLED"]:
            return resp

        if time.time() - start > timeout_seconds:
            raise TimeoutError(f"Athena query timed out: {qid}")

        time.sleep(poll_seconds)


def iceberg_table_exists():
    check_sql = f"SHOW TABLES IN {DEST_DATABASE} LIKE '{DEST_TABLE}';"
    qid = run_query(check_sql)
    result = wait_for_query(qid)

    state = result["QueryExecution"]["Status"]["State"]
    if state != "SUCCEEDED":
        return False

    rows = athena.get_query_results(QueryExecutionId=qid)
    # If table exists, it will return at least 2 rows (header + table name)
    return len(rows["ResultSet"]["Rows"]) > 1


# -------------------------
# LAMBDA HANDLER
# -------------------------
def lambda_handler(event, context):
    print("✅ Lambda Triggered!")
    print("Event:", json.dumps(event))

    # ✅ Safe guard: If Iceberg table already exists, exit without doing anything
    if iceberg_table_exists():
        print(f"✅ Iceberg table already exists: {DEST_DATABASE}.{DEST_TABLE} — skipping CTAS.")
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Iceberg table already exists. Skipping creation.",
                "table": f"{DEST_DATABASE}.{DEST_TABLE}"
            })
        }

    # ✅ Create Iceberg table using CTAS (Managed + explicit location)
    ctas_sql = f"""
    CREATE TABLE {DEST_DATABASE}.{DEST_TABLE}
    WITH (
      table_type = 'ICEBERG',
      is_external = false,
      location = '{ICEBERG_LOCATION}',
      format = 'PARQUET',
      write_compression = 'SNAPPY',
      partitioning = ARRAY['program_year']
    )
    AS
    SELECT
        covered_recipient_type,
        teaching_hospital_name,
        recipient_city,
        recipient_country,
        recipient_category,
        manufacturer_payment_id,
        manufacturer_payment_name,
        manufacturer_payment_country,
        total_amount_of_payment_usdollars,
        date_of_payment,
        number_of_payments_included_in_total_amount,
        form_of_payment,
        nature_of_payment,
        record_id,
        covered_or_noncovered_indicator,
        medical_product_type,
        product_category,
        medical_product_name,
        program_year,
        covered_recipient_full_name,
        recipient_unique_id,
        recipient_state_final,
        specialty_main,
        manufacturer_name_base,
        manufacturer_payment_state
    FROM {SOURCE_DATABASE}.{SOURCE_TABLE};
    """

    print("✅ Submitting Athena CTAS query...")
    qid = run_query(ctas_sql)
    print("✅ QueryExecutionId:", qid)

    result = wait_for_query(qid)
    state = result["QueryExecution"]["Status"]["State"]
    reason = result["QueryExecution"]["Status"].get("StateChangeReason", "")

    print("✅ Athena Query Final State:", state)
    if reason:
        print("ℹ️ Reason:", reason)

    if state != "SUCCEEDED":
        raise Exception(f"CTAS failed: {reason}")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Iceberg table created successfully",
            "query_execution_id": qid,
            "source_table": f"{SOURCE_DATABASE}.{SOURCE_TABLE}",
            "destination_table": f"{DEST_DATABASE}.{DEST_TABLE}",
            "iceberg_location": ICEBERG_LOCATION
        })
    }
