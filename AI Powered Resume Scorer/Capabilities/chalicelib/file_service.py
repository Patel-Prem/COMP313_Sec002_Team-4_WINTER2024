import boto3
from botocore.exceptions import NoCredentialsError

def upload_file_to_s3(file, file_name, bucket_name):
    s3 = boto3.client('s3')
    try:
        s3.put_object(Bucket=bucket_name, Key=file_name, Body=file)
        print("File uploaded successfully")
        return True, 'File uploaded successfully'
    except NoCredentialsError:
        return False, 'AWS credentials not found'
