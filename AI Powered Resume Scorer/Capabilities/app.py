from chalice import Chalice, Response
import requests
import base64
import os
import boto3
from datetime import datetime
from chalicelib import file_service, text_processing, aws_services

app = Chalice(app_name='resume-scorer-api')
app.debug = True
app.api.cors = True

COGNITO_DOMAIN = "https://resumescorer.auth.ca-central-1.amazoncognito.com"#os.environ.get("COGNITO_DOMAIN")
CLIENT_ID = "5mlk71q819mk4t55si16fa4mns"#os.environ.get("CLIENT_ID")
CLIENT_SECRET = "1t7r0ojt75k973hao0sp0htqmo3b0u3g2st4ntpd7rl87n0mdtla"#os.environ.get("CLIENT_SECRET")
APP_URI = "http://localhost:8080/"

bucket_name = 'files-301301102'
user_email = ""

@app.route('/')
def index():
    return {'message': 'Welcome to the Resume Scorer API Milan'}

@app.route('/login', methods=['GET'] , cors = True)
def login():
    APP_URI = "http://localhost:8080/landing.html"
    # Redirect to Cognito login URL
    login_url = f"{COGNITO_DOMAIN}/login?client_id={CLIENT_ID}&response_type=code&scope=email+openid&redirect_uri={APP_URI}"
    return {'login_url': login_url}

@app.route('/logout', methods=['GET'])
def logout():
    # Redirect to Cognito logout URL
    logout_url = f"{COGNITO_DOMAIN}/logout?client_id={CLIENT_ID}&logout_uri={APP_URI}"
    return {'logout_url': logout_url}

@app.route('/upload', methods=['POST'], content_types=['multipart/form-data'])
def upload_file():
    request = app.current_request
    file = request.raw_body 
    #file_name = "uploaded_resume.pdf" 
    
    # Generate a unique file name. For example, appending a timestamp to the original file name
    original_file_name = "uploaded_resume.pdf" 
    file_extension = os.path.splitext(original_file_name)[1]
    file_name = f"{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}{file_extension}"

    success, message = file_service.upload_file_to_s3(file, file_name, bucket_name)
    if success:
        extract_text = aws_services.extract_text_from_document(bucket_name, file_name)
        return {'message': 'File uploaded successfully', 'resume_text': extract_text}
    else:
        return Response(body={'message': message}, status_code=401)

@app.route('/analyze', methods=['POST'])
def analyze_text():
    request = app.current_request
    body = request.json_body
    resume_text = body.get('resume_text', '')
    job_description = body.get('job_description', '')
    user_email = body.get('user_email', '')
    user_type = body.get('user_type', '')

    score, missing_words, entities = None, [], []

    if user_type in ["recruiter", "premium", "normal"]:
        score = text_processing.calculate_cosine_similarity(resume_text, job_description)

    if user_type in ["recruiter", "premium"]:
        missing_words = text_processing.get_missing_words_suggestions(resume_text, job_description)
        
    if user_type == "recruiter":
        entities = aws_services.detect_pii_entities(resume_text[:250])

    extracted_entities = []
    for entity in entities:
        begin_offset = entity['BeginOffset']
        end_offset = entity['EndOffset']
        # Extract the text segment based on the offsets
        text_segment = resume_text[begin_offset:end_offset]
        # Add the modified entity dictionary to the list
        extracted_entities.append({
            'Type': entity['Type'],
            'Score': entity['Score'],
            'Text': text_segment
        })

    response_data = {
        'score': score,
        'entities': extracted_entities,
        'missing_words': missing_words
    }
    print(user_email)
    if user_email:  # Ensure we have the user's email
        dynamodb = boto3.client('dynamodb', region_name='ca-central-1')
        table_name = 'user'

        # Update the user's account type in the DynamoDB table
        dynamodb.update_item(
            TableName=table_name,
            Key={'email': {'S': user_email}},
            UpdateExpression='SET account_type = :type',
            ExpressionAttributeValues={':type': {'S': user_type}}
        )

    return response_data

@app.route('/get_token')
def get_token():
    auth_code = app.current_request.query_params.get('code')
    print(auth_code)
    if auth_code:
        APP_URI = "http://localhost:8080/landing.html"
        token_url = f"{COGNITO_DOMAIN}/oauth2/token"
        client_secret_string = f"{CLIENT_ID}:{CLIENT_SECRET}"
        client_secret_encoded = str(
            base64.b64encode(client_secret_string.encode("utf-8")), "utf-8"
        )

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {client_secret_encoded}",
        }
        body = {
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "code": auth_code,
            "redirect_uri": APP_URI,
        }
        token_response = requests.post(token_url, headers=headers, data=body)
        if token_response.ok:
            token_data = token_response.json()
            access_token = token_data.get('access_token')
            user_email = get_user_info(access_token)["email"]

            dynamodb = boto3.client('dynamodb',region_name='ca-central-1')
            table_name = 'user'

            # Check if the user exists
            response = dynamodb.get_item(
                TableName=table_name,
                Key={
                    'email': {'S': user_email}
                }
            )
            user_type = ""  # Default to an empty string if not found
            if 'Item' in response:
                # If user exists, retrieve the `user_type`
                user_type = response['Item']['account_type']['S']
            else:
                # If user does not exist, add them to DynamoDB
                item = {
                    'email': {'S': user_email},
                    'account_type': {'S': ''},  # Set a default user type as needed
                    'created_on': {'S': datetime.utcnow().isoformat()}
                }
                dynamodb.put_item(TableName=table_name, Item=item)
                user_type = item['account_type']['S']  # Use the default user type for the new user
                print("New user added to DynamoDB.")

            return Response(body={'message': 'Token processed successfully', 'access_token': access_token, 'user_email': user_email, 'user_type': user_type}, status_code=200)
        else:
            print("Error fetching token:", token_response.text)
            return Response(body={"error": "Failed to get access token, check server logs for more details."}, status_code=token_response.status_code)
    else:
        return Response(body={"error": "Authorization code not found"}, status_code=400)

@app.route('/total_users', methods=['GET'])
def total_users():
    # Create a DynamoDB resource
    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table('user')

    # Perform a scan operation on the table
    response = table.scan(Select='COUNT')
    total_count = response['Count']

    # Return the total count in the response
    return {'totalUsers': total_count}

def get_user_info(access_token):
    """
    Gets user info from aws cognito server.

    Args:
        access_token: string access token from the aws cognito user pool
        retrieved using the access code.

    Returns:
        userinfo_response: json object.
    """
    print("HIIII")
    userinfo_url = f"{COGNITO_DOMAIN}/oauth2/userInfo"
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "Authorization": f"Bearer {access_token}",
    }

    userinfo_response = requests.get(userinfo_url, headers=headers)

    return userinfo_response.json()