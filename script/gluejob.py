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
# GLUE CONTEXT
# =====================================================
sc = SparkContext.getOrCreate()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

# =====================================================
# JOB PARAMETERS (OPTIONAL BUT RECOMMENDED)
# =====================================================
args = getResolvedOptions(sys.argv, ["JOB_NAME", "BRONZE_INPUT_PATH", "SILVER_OUTPUT_PATH"])

job = Job(glueContext)
job.init(args["JOB_NAME"], args)
# =====================================================
# PATHS (S3)
# =====================================================
BRONZE_INPUT_PATH = args["BRONZE_INPUT_PATH"]
SILVER_OUTPUT_PATH = args["SILVER_OUTPUT_PATH"]

print("SOURCE PATH :", BRONZE_INPUT_PATH)
print("TARGET PATH :", SILVER_OUTPUT_PATH)

# =====================================================
# READ BRONZE (CSV OR PARQUET)
# =====================================================
if BRONZE_INPUT_PATH.lower().endswith(".csv"):
    df = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "true")
        .option("multiLine", "true")
        .option("escape", "\"")
        .csv(BRONZE_INPUT_PATH)
    )
else:
    df = spark.read.parquet(BRONZE_INPUT_PATH)
# =====================================================
# DROP EARLY NOISE COLUMNS
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
    "Recipient_Postal_Code",

    "Covered_Recipient_Primary_Type_2",
    "Covered_Recipient_Primary_Type_3",
    "Covered_Recipient_Primary_Type_4",
    "Covered_Recipient_Primary_Type_5",
    "Covered_Recipient_Primary_Type_6",

    "Covered_Recipient_Specialty_2",
    "Covered_Recipient_Specialty_3",
    "Covered_Recipient_Specialty_4",
    "Covered_Recipient_Specialty_5",
    "Covered_Recipient_Specialty_6",

    "Covered_Recipient_License_State_code1",
    "Covered_Recipient_License_State_code2",
    "Covered_Recipient_License_State_code3",
    "Covered_Recipient_License_State_code4",
    "Covered_Recipient_License_State_code5",

    "Submitting_Applicable_Manufacturer_or_Applicable_GPO_Name",
    "City_of_Travel",
    "State_of_Travel",
    "Country_of_Travel",
    "Physician_Ownership_Indicator",
    "Third_Party_Payment_Recipient_Indicator",
    "Name_of_Third_Party_Entity_Receiving_Payment_or_Transfer_of_Value",
    "Charity_Indicator",
    "Third_Party_Equals_Covered_Recipient_Indicator",
    "Contextual_Information",
    "Delay_in_Publication_Indicator",
    "Dispute_Status_for_Publication",
    "Related_Product_Indicator",

    "Associated_Drug_or_Biological_NDC_1",
    "Associated_Device_or_Medical_Supply_PDI_1",
    "Associated_Drug_or_Biological_NDC_2",
    "Associated_Device_or_Medical_Supply_PDI_2",
    "Associated_Drug_or_Biological_NDC_3",
    "Associated_Device_or_Medical_Supply_PDI_3",
    "Associated_Drug_or_Biological_NDC_4",
    "Associated_Device_or_Medical_Supply_PDI_4",
    "Associated_Drug_or_Biological_NDC_5",
    "Associated_Device_or_Medical_Supply_PDI_5",

    "Covered_or_Noncovered_Indicator_2",
    "Indicate_Drug_or_Biological_or_Device_or_Medical_Supply_2",
    "Product_Category_or_Therapeutic_Area_2",
    "Name_of_Drug_or_Biological_or_Device_or_Medical_Supply_2",

    "Covered_or_Noncovered_Indicator_3",
    "Indicate_Drug_or_Biological_or_Device_or_Medical_Supply_3",
    "Product_Category_or_Therapeutic_Area_3",
    "Name_of_Drug_or_Biological_or_Device_or_Medical_Supply_3",

    "Covered_or_Noncovered_Indicator_4",
    "Indicate_Drug_or_Biological_or_Device_or_Medical_Supply_4",
    "Product_Category_or_Therapeutic_Area_4",
    "Name_of_Drug_or_Biological_or_Device_or_Medical_Supply_4",

    "Covered_or_Noncovered_Indicator_5",
    "Indicate_Drug_or_Biological_or_Device_or_Medical_Supply_5",
    "Product_Category_or_Therapeutic_Area_5",
    "Name_of_Drug_or_Biological_or_Device_or_Medical_Supply_5",
]

existing_cols_to_drop = [c for c in cols_to_drop_early if c in df.columns]
df = df.drop(*existing_cols_to_drop)

# =====================================================
# CAPITALIZE FIRST LETTER OF ALL COLUMN NAMES
# =====================================================
def capitalize_first_letter(col_name: str) -> str:
    if not col_name:
        return col_name
    return col_name[0].upper() + col_name[1:]

df = df.select([
    col(c).alias(capitalize_first_letter(c))
    for c in df.columns
])

us_state_map = {
    "AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado",
    "CT":"Connecticut","DE":"Delaware","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho",
    "IL":"Illinois","IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana",
    "ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota",
    "MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada",
    "NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York","NC":"North Carolina",
    "ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon","PA":"Pennsylvania",
    "RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota","TN":"Tennessee","TX":"Texas",
    "UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington","WV":"West Virginia",
    "WI":"Wisconsin","WY":"Wyoming","DC":"District of Columbia","PR":"Puerto Rico"
}

mapping_expr = create_map(
    *[lit(x) for kv in us_state_map.items() for x in kv]
)

# =====================================================
# NORMALIZE FAKE NULLS → REAL NULLS
# =====================================================
NULL_LIKE = ["", " ", "NA", "N/A", "NULL", "null"]

def normalize_null(column_name):
    return when(
        trim(col(column_name)).isin(NULL_LIKE),
        None
    ).otherwise(col(column_name))

critical_cols = [
    "Name_of_Drug_or_Biological_or_Device_or_Medical_Supply_1",
    "Product_Category_or_Therapeutic_Area_1",
    "Indicate_Drug_or_Biological_or_Device_or_Medical_Supply_1",
    "Covered_Recipient_First_Name",
    "Covered_Recipient_Last_Name",
    "Covered_Recipient_Specialty_1",
    "Recipient_City"
]

for c in critical_cols:
    if c in df.columns:
        df = df.withColumn(c, normalize_null(c))

# =====================================================
# PHYSICIAN FULL NAME
# =====================================================
df = (
    df.withColumn(
        "Covered_Recipient_Full_Name",
        concat_ws(
            " ",
            trim(col("Covered_Recipient_First_Name")),
            trim(col("Covered_Recipient_Last_Name"))
        )
    )
    .drop(
        "Covered_Recipient_First_Name",
        "Covered_Recipient_Middle_Name",
        "Covered_Recipient_Last_Name"
    )
)

# =====================================================
# CREATE UNIQUE RECIPIENT ID
# =====================================================
df = df.withColumn(
    "Recipient_Unique_ID",
    when(
        col("Teaching_Hospital_ID").isNotNull(),
        concat(lit("HOSP_"), col("Teaching_Hospital_ID"))
    ).otherwise(
        concat(lit("PROF_"), col("Covered_Recipient_Profile_ID"))
    )
)

# 🔥 DROP SOURCE IDS IMMEDIATELY (EXPLICIT & GUARANTEED)
df = df.drop(
    "Teaching_Hospital_ID",
    "Covered_Recipient_Profile_ID"
)

# =====================================================
# FILL HOSPITAL NAME
# =====================================================
df = df.withColumn(
    "Teaching_Hospital_Name",
    when(
        col("Teaching_Hospital_Name").isNull(),
        lit("Not a Hospital")
    ).otherwise(col("Teaching_Hospital_Name"))
)

# =====================================================
# FILL PRIMARY TYPE
# =====================================================
df = df.withColumn(
    "Covered_Recipient_Primary_Type_1",
    when(
        col("Covered_Recipient_Primary_Type_1").isNull(),
        lit("Hospital")
    ).otherwise(col("Covered_Recipient_Primary_Type_1"))
)


# =====================================================
# DATA TYPE FIXES
# =====================================================
df = df.withColumn(
    "Total_Amount_of_Payment_USDollars",
    regexp_replace(
        col("Total_Amount_of_Payment_USDollars"),
        "[$,]",
        ""
    ).cast(DoubleType())
)

df = df.withColumn(
    "Number_of_Payments_Included_in_Total_Amount",
    col("Number_of_Payments_Included_in_Total_Amount").cast(IntegerType())
)

df = df.withColumn(
    "Date_of_Payment",
    to_date(col("Date_of_Payment"), "MM/dd/yyyy")
)



# =====================================================
# CITY & SPECIALTY
# =====================================================

df = df.withColumn(
    "Recipient_State_Final",
    when(
        trim(col("Recipient_Country")) == "United States",
        mapping_expr.getItem(trim(col("Recipient_State")))
    ).otherwise(trim(col("Recipient_Country")))
)

df = df.drop("Recipient_State")

df = df.withColumn(
    "Recipient_City",
    initcap(trim(col("Recipient_City")))
)

df = df.withColumn(
    "Specialty_Main",
    trim(split(col("Covered_Recipient_Specialty_1"), "\\|")[1])
).drop("Covered_Recipient_Specialty_1")

df = df.dropna(subset=["Specialty_Main"])

# =====================================================
# MANUFACTURER NORMALIZATION
# =====================================================

df = df.withColumn(
    "manufacturer_name_base",
    lower(trim(col("Applicable_Manufacturer_or_Applicable_GPO_Making_Payment_Name")))
)

df = df.withColumn(
    "manufacturer_name_base",
    regexp_replace(col("manufacturer_name_base"), "[\\.,&()]", " ")
)

df = df.withColumn(
    "manufacturer_name_base",
    regexp_replace(
        col("manufacturer_name_base"),
        "\\b(inc|llc|ltd|corp|company|co|gmbh|plc|sa|private|pvt)\\b",
        ""
    )
)

df = df.withColumn(
    "manufacturer_name_base",
    trim(regexp_replace(col("manufacturer_name_base"), "\\s+", " "))
)

df = df.withColumn(
    "manufacturer_name_base",
    initcap(col("manufacturer_name_base"))
)

df = df.withColumnRenamed(
    "manufacturer_name_base",
    "Manufacturer_name_base"
)

# =====================================================
# MANUFACTURER STATE NORMALIZATION
# =====================================================


# Executor-safe Spark map expression

df = df.withColumn(
    "Applicable_Manufacturer_or_Applicable_GPO_Making_Payment_State_Full",
    when(
        trim(col("Applicable_Manufacturer_or_Applicable_GPO_Making_Payment_Country")) == "United States",
        mapping_expr.getItem(
            trim(col("Applicable_Manufacturer_or_Applicable_GPO_Making_Payment_State"))
        )
    ).otherwise(
        col("Applicable_Manufacturer_or_Applicable_GPO_Making_Payment_State")
    )
)

df = df.drop("Applicable_Manufacturer_or_Applicable_GPO_Making_Payment_State")

# =====================================================
# FINAL QUALITY FILTER (NO NULL ROWS)
# =====================================================
df_final = df.dropna(
    subset=[
        "Name_of_Drug_or_Biological_or_Device_or_Medical_Supply_1",
        "Product_Category_or_Therapeutic_Area_1",
        "Indicate_Drug_or_Biological_or_Device_or_Medical_Supply_1"
    ]
)

# =====================================================
# WRITE SILVER (CSV)
# =====================================================
(
    df_final
        .write
        .mode("append")        # or "override"
        .option("header", "true")
        .option("quoteAll", "true")
        .option("escape", "\"")
        .csv(SILVER_OUTPUT_PATH)
)
job.commit()
