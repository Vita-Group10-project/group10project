#Data Ingestion
import sys
import urllib.request
import boto3
from datetime import datetime
from awsglue.utils import getResolvedOptions

args = getResolvedOptions(sys.argv, ['RAW_BUCKET', 'URL'])

RAW_BUCKET = args['RAW_BUCKET']
URL = args['URL']

s3 = boto3.client("s3")

def main():

    today = datetime.utcnow().strftime("%Y/%m/%d")
    key = f"direct/{today}/data.csv"

    local_file = "/tmp/data.csv"

    print("Downloading file...")
    urllib.request.urlretrieve(URL, local_file)

    print("Uploading multipart to S3...")

    s3.upload_file(
        local_file,     # local path
        RAW_BUCKET,     # bucket
        key             # s3 key
    )

    print("Upload successful")


if __name__ == "__main__":
    main()
