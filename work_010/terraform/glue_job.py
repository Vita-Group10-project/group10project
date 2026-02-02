import sys
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.utils import getResolvedOptions
from awsglue.job import Job

from pyspark.sql.functions import (
    col, trim, lower, when, concat, concat_ws, lit,
    regexp_replace, to_date, initcap, split, create_map
)
from pyspark.sql.types import DoubleType, IntegerType

# =====================================================
# GLUE CONTEXT (EXECUTION ENGINE ONLY)
# =====================================================
sc = SparkContext.getOrCreate()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

spark.conf.set("spark.sql.parquet.datetimeRebaseModeInWrite", "LEGACY")
spark.conf.set("spark.sql.parquet.int96RebaseModeInWrite", "LEGACY")

# =====================================================
# PARAMETERS (FLOW CONTROLS THIS, NOT THE SCRIPT)
# =====================================================
args = getResolvedOptions(
    sys.argv,
    ["JOB_NAME", "INPUT_PATH", "OUTPUT_PATH"]
)

job = Job(glueContext)
job.init(args["JOB_NAME"], args)

INPUT_PATH = args["INPUT_PATH"]     # RAW ZONE (S3)
OUTPUT_PATH = args["OUTPUT_PATH"]   # CLEAN / ENRICHED ZONE (S3)

# =====================================================
# READ RAW DATA (BRONZE)
# =====================================================
if INPUT_PATH.lower().endswith(".csv"):
    df = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "false")
        .csv(INPUT_PATH)
    )
else:
    df = spark.read.parquet(INPUT_PATH)

# =====================================================
# DROP UNNECESSARY COLUMNS (DATA REDUCTION)
# =====================================================
cols_to_drop_early = [
    "Change_Type",
    "Teaching_Hospital_CCN",
    "Covered_Recipient_NPI",
    "Covered_Recipient_Name_Suffix",
    "Recipient_Primary_Business_Street_Address_Line1",
    "Recipient_Primary_Business_Street_Address_Line2",
    "Recipient_Zip_Code",
    "Recipient_Province",
    "Recipient_Postal_Code"
]

df = df.drop(*[c for c in cols_to_drop_early if c in df.columns])

# =====================================================
# COLUMN NAME STANDARDIZATION
# =====================================================
df = df.select([
    col(c).alias(c[0].upper() + c[1:])
    for c in df.columns
])

# =====================================================
# NULL NORMALIZATION
# =====================================================
NULL_LIKE = ["", " ", "NA", "N/A", "NULL", "null"]

def normalize_null(c):
    return when(trim(col(c)).isin(NULL_LIKE), None).otherwise(col(c))

for c in df.columns:
    df = df.withColumn(c, normalize_null(c))

# =====================================================
# BUSINESS TRANSFORMATIONS
# =====================================================

# Full Name
df = df.withColumn(
    "Covered_Recipient_Full_Name",
    concat_ws(
        " ",
        trim(col("Covered_Recipient_First_Name")),
        trim(col("Covered_Recipient_Last_Name"))
    )
).drop(
    "Covered_Recipient_First_Name",
    "Covered_Recipient_Middle_Name",
    "Covered_Recipient_Last_Name"
)

# Unique Recipient ID
df = df.withColumn(
    "Recipient_Unique_ID",
    when(
        col("Teaching_Hospital_ID").isNotNull(),
        concat(lit("HOSP_"), col("Teaching_Hospital_ID"))
    ).otherwise(
        concat(lit("PROF_"), col("Covered_Recipient_Profile_ID"))
    )
).drop(
    "Teaching_Hospital_ID",
    "Covered_Recipient_Profile_ID"
)

# Amount & Date fixes
df = df.withColumn(
    "Total_Amount_of_Payment_USDollars",
    regexp_replace(col("Total_Amount_of_Payment_USDollars"), "[$,]", "")
    .cast(DoubleType())
)

df = df.withColumn(
    "Date_of_Payment",
    to_date(col("Date_of_Payment"), "MM/dd/yyyy")
)

# Specialty extraction
df = df.withColumn(
    "Specialty_Main",
    trim(split(col("Covered_Recipient_Specialty_1"), "\\|")[1])
).drop("Covered_Recipient_Specialty_1")

# =====================================================
# FINAL DATA QUALITY FILTER
# =====================================================
df_final = df.dropna(subset=[
    "Name_of_Drug_or_Biological_or_Device_or_Medical_Supply_1",
    "Product_Category_or_Therapeutic_Area_1",
    "Indicate_Drug_or_Biological_or_Device_or_Medical_Supply_1"
])

# =====================================================
# WRITE CLEAN DATA (SILVER)
# =====================================================
(
    df_final
        .write
        .mode("overwrite")
        .parquet(OUTPUT_PATH)
)

job.commit()
