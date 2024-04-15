import boto3
import time

def extract_text_from_document(bucket_name, document_key):
    textract = boto3.client('textract', region_name='us-east-1')
    response = textract.start_document_text_detection(
        DocumentLocation={'S3Object': {'Bucket': bucket_name, 'Name': document_key}})
    job_id = response['JobId']

    while True:
        job_status = textract.get_document_text_detection(JobId=job_id)
        status = job_status['JobStatus']
        if status in ['SUCCEEDED', 'FAILED']:
            break
        time.sleep(5)

    if status == 'SUCCEEDED':
        extracted_text = []
        for item in job_status.get('Blocks', []):
            if item['BlockType'] == 'LINE':
                extracted_text.append(item['Text'])
        return '\n'.join(extracted_text)
    else:
        return None

def detect_pii_entities(text):
    comprehend = boto3.client('comprehend')
    response = comprehend.detect_pii_entities(Text=text[:250], LanguageCode='en')
    return response['Entities']
