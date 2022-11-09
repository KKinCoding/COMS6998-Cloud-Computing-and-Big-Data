import json
import boto3
import time
import os
import logging
from datetime import datetime
from opensearchpy import OpenSearch, RequestsHttpConnection

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

def detect_labels(photo, bucket):
    
    """
    Use Rekognition to detect a new photo's label in S3 bucket
    """

    client=boto3.client('rekognition', region_name="us-east-1")
    
    response = client.detect_labels(Image={'S3Object':{'Bucket':bucket,'Name':photo}}, MaxLabels=10, MinConfidence=90)
        
    labels = [label['Name'].lower() for label in response['Labels']]

    print('Detected labels for {} is {}'.format(photo, labels)) 

    return labels

def upload_opensearch(key, arr1):
    
    """
    Store photo's metadata to OpenSearch
    """    
    
    host = 'search-photos-4w7hm643oqieshwdue4n5ic5pq.us-east-1.es.amazonaws.com'
    port = 443
    auth = ('master', 'fallCOMS6998!@#')
    
    # Create the client with SSL/TLS enabled, but hostname verification disabled.
    client = OpenSearch(
        hosts = [{'host': host, 'port': port}],
        http_compress = True, # enables gzip compression for request bodies
        http_auth = auth,
        use_ssl = True,
        verify_certs = True,
        connection_class=RequestsHttpConnection
        
    )
    
    # Add a document to the index. (index would be created automatically)
    response = client.index(
        index = 'photos',
        body = json.dumps(arr1).encode('utf-8'),
        id = key,
        refresh = True
    )
    print('----')
    print(response)
    return response
    
    

def lambda_handler(event, context):
    
    """
    Main handler
    """
    
    # set the default time zone
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    
    # Get S3 bucket and key from the event
    s3 = boto3.client('s3')
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']


    # Get detection labels from Rekognition
    labels = detect_labels(key, bucket)
    print('------')
    print(labels)

    logger.debug("Labels detected: " + ', '.join(labels))
    
    # Retrieve S3 metadata
    try:
        metadata = s3.headObject(Bucket = bucket, Key = key)
        custom_labels = metadata['ResponseMetadata']['HTTPHeaders']['x-amz-meta-customlabels']
        logger.info(custom_labels)
        if custom_labels:
            labels += [l.strip().lower() for l in custom_labels.split(',')]

    except Exception as e:
        logger.debug("No custom labels.")
    
    # Create a JSON array with the labels
    arr1 = {
        "objectKey": key,
        "bucket": bucket,
        "createdTimestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "labels": labels
    }
    
    # Store the JSON object in OpenSearch
    opensearch_response = upload_opensearch(key, arr1)
    
    logger.info(opensearch_response)

    
    #return {
    #    'statusCode': 200,
    #    'body': json.dumps('Finished indexing photos.')
    #}
    
    return {
        'statusCode': 200,
        'body': json.dumps('Finished indexing photos.'),
        'headers': {
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS, GET, PUT, POST',
        }
    }
