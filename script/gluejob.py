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

spark.conf.set("spark.sql.parquet.datetimeRebaseModeInWrite", "LEGACY")
spark.conf.set("spark.sql.parquet.int96RebaseModeInWrite", "LEGACY")
# =====================================================
# JOB PARAMETERS (OPTIONAL BUT RECOMMENDED)
# =====================================================
args = getResolvedOptions(sys.argv, ["JOB_NAME", "INPUT_PATH", "OUTPUT_PATH"])

job = Job(glueContext)
job.init(args["JOB_NAME"], args)
# =====================================================
# PATHS (S3)
# =====================================================
INPUT_PATH = "s3://raw-zone-00/direct/2026/02/03/data.csv"
OUTPUT_PATH = "s3://enriched-zone-00/transformed_1/"

# =====================================================
# READ BRONZE (CSV OR PARQUET)
# =====================================================
if INPUT_PATH.lower().endswith(".csv"):
    df = (
        spark.read
        .option("header", "true")
        .option("inferSchema", "false")
        .option("multiLine", "false")
        .option("escape", "\"")
        .csv(INPUT_PATH)
    )
else:
    df = spark.read.parquet(INPUT_PATH)
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
    "Payment_Publication_Date",

     

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

rename_map = {
    "Covered_Recipient_Type": "Covered_Recipient_Type",

    "Teaching_Hospital_Name": "Teaching_Hospital_Name",

    "Recipient_City": "Recipient_City",
    "Recipient_Country": "Recipient_Country",
    "Recipient_State_Final": "Recipient_State_Final",

    "Covered_Recipient_Primary_Type_1": "Recipient_Category",

    "Applicable_Manufacturer_or_Applicable_GPO_Making_Payment_ID": "Manufacturer_Payment_Id",
    "Applicable_Manufacturer_or_Applicable_GPO_Making_Payment_Name": "Manufacturer_Payment_Name",
    "Applicable_Manufacturer_or_Applicable_GPO_Making_Payment_Country": "Manufacturer_Payment_Country",
    "Applicable_Manufacturer_or_Applicable_GPO_Making_Payment_State_Full": "Manufacturer_Payment_State",

    "Manufacturer_name_base": "Manufacturer_Name_Base",

    "Total_Amount_of_Payment_USDollars": "Total_Amount_Of_Payment_Usdollars",
    "Number_of_Payments_Included_in_Total_Amount": "Number_Of_Payments_Included_In_Total_Amount",
    "Date_of_Payment": "Date_Of_Payment",

    "Form_of_Payment_or_Transfer_of_Value": "Form_Of_Payment",
    "Nature_of_Payment_or_Transfer_of_Value": "Nature_Of_Payment",

    "Covered_or_Noncovered_Indicator_1": "Covered_Or_Noncovered_Indicator",

    "Indicate_Drug_or_Biological_or_Device_or_Medical_Supply_1": "Medical_Product_Type",
    "Product_Category_or_Therapeutic_Area_1": "Product_Category",
    "Name_of_Drug_or_Biological_or_Device_or_Medical_Supply_1": "Medical_Product_Name",

    "Program_Year": "Program_Year",

    "Covered_Recipient_Full_Name": "Covered_Recipient_Full_Name",
    "Recipient_Unique_ID": "Recipient_Unique_Id",

    "Specialty_Main": "Specialty_Main",

    "Record_ID": "Record_Id"
}


for old, new in rename_map.items():
    if old in df_final.columns:
        df_final = df_final.withColumnRenamed(old, new)


# =====================================================
# WRITE SILVER (CSV)
# =====================================================
(
    df_final \
    .write \
    .mode("overwrite") \
    .option("header", "true") \
    .csv(OUTPUT_PATH)
)
job.commit()
