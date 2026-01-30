from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

bronze_path = "s3://ter-bronze-data-sahil/input/"
silver_path = "s3://ter-silver-data-sahil/output/"

df = spark.read.option("header", "true").csv(bronze_path)

# basic cleanup example
df_clean = df.dropDuplicates()

df_clean.write.mode("overwrite").parquet(silver_path)
