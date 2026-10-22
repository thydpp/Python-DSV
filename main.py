"""
Created on Mon Dec  1 12:58:59 2025
Help: https://docs.python.org/3/library/functions.html

@User: dpp
@author: Dean Petersen
@Contact: dpp@idealcombi.dk
Integration between DSV and HubSpot Deals. using encrypted credentials for DSV API access with OAuth 2.0 
and encrypted subscription keys.
logfile is created with timestamp in filename.
"""

import json
import re
import time
import datetime
import logging
import sys
from hubspot.crm.deals import BatchInputSimplePublicObjectBatchInputUpsert, ApiException
from hubspot import HubSpot
from urllib3.util.retry import Retry
from dsv_access import DSVAPIClient
import os

# Ensure logs directory exists
os.makedirs(r"C:\LOGFILES\PYTHON\HUBSPOT-DSV-LIST", exist_ok=True)

# Configure logging to write to both file and console
log_filename = fr"C:\LOGFILES\PYTHON\HUBSPOT-DSV-LIST\dsv_hubspot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler(sys.stdout)
    ]
)

# Custom print function that also logs
def log_print(message):
    """Print to console and write to log file"""
    print(message)
    logging.info(message)

logging.info("=" * 60)
logging.info("DSV to HubSpot Integration - Starting")
logging.info("=" * 60)

retry = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=(429, 502, 504, 503, 521, 522, 523, 524, 525, 526),
)

# Initialize DSV API client from encrypted credentials
credentials = {
    "client_id": os.getenv("DSV_CLIENT_ID"),
    "client_secret": os.getenv("DSV_CLIENT_SECRET"),
    "access_subscription_key": os.getenv("DSV_PROD_ACCESS_KEY"),
    "tracking_subscription_key": os.getenv("DSV_PROD_TRACKING_KEY")
}

# Create DSV client from environment variable credentials
logging.info("Initializing DSV API client...")
dsv_client = DSVAPIClient(**credentials)
logging.info("DSV API client initialized successfully")

def get_shipments_list(filter_params):
    """
    Get shipments list using the DSV API client
    
    Args:
        filter_params: Dictionary with statuses and/or transports filters
        
    Returns:
        List of shipments from DSV API
    """
    return dsv_client.get_shipment_list(
        statuses=filter_params.get('statuses'),
        transports=filter_params.get('transports')
    )

# Get shipments
filter_params = {
    "transports": ["ROAD"]
}

shipments = get_shipments_list(filter_params)
log_print(f"Retrieved {len(shipments)} shipments from DSV API")
logging.debug(f"Shipments data: {json.dumps(shipments, indent=2)}")


def extract_shipper_references(shipments):
    shipper_references = []
    for shipment in shipments:
        booking_id = shipment.get('bookingId')
        references = shipment.get('references', [])
        for reference in references:
            if reference.get('type') == 'SHIPPER_REFERENCE':
                values = re.split(r'[-,;:\s]', reference.get('value', ''))
                for value in values:
                    if len(value.strip()) == 6:
                        shipper_references.append({
                            'properties':{'dsv_booking_id': booking_id,},
                            'id': value.strip(),
                            'idProperty' : 'axsalesid'
                        })
    return shipper_references

# Example usage
processing_list = extract_shipper_references(shipments)
log_print(f"Extracted {len(processing_list)} shipper references")
logging.debug(f"Processing list: {processing_list}")
def merge_duplicates(processing_list):
    merged_dict = {}
    for item in processing_list:
        item_id = item['id']
        if item_id in merged_dict:
            if merged_dict[item_id]['properties']['dsv_booking_id'] is None:
                merged_dict[item_id]['properties']['dsv_booking_id'] = item['properties']['dsv_booking_id']
            else:
                merged_dict[item_id]['properties']['dsv_booking_id'] += f", {item['properties']['dsv_booking_id']}"
        else:
            merged_dict[item_id] = item
    return list(merged_dict.values())

# Example usage
processing_list = merge_duplicates(processing_list)
log_print(f"Merged duplicates - Final count: {len(processing_list)} unique references")
logging.debug(f"Merged processing list: {processing_list}")

def update_deal_properties(inputs):
    
    # Check if there are any rows to be synced
    if len(inputs) > 0:
        # Log the current datetime and the number of rows to be synced
        log_print(f"{datetime.datetime.now()}: Number of rows to be synced: {len(inputs)}" )
        access_token = os.environ.get("HUBSPOT_ACCESS_TOKEN") #dpp: 17.12.25
        if not access_token:
            raise ValueError("HUBSPOT_ACCESS_TOKEN environment variable is not set")
        client = HubSpot(access_token=access_token, retry=retry)        

        # Function to split the list into chunks
        def chunk_list(data, chunk_size):
            for i in range(0, len(data), chunk_size):
                yield data[i:i + chunk_size]

        # Split the inputs into chunks of 100
        chunk_size = 100
        input_chunks = list(chunk_list(inputs, chunk_size))

        # Loop through the chunks and send them to HubSpot. 
        for chunk in input_chunks:
            log_print(f"Processing chunk {input_chunks.index(chunk) + 1}/{len(input_chunks)} with {len(chunk)} items")
            
            # Print each item in the chunk
            for item in chunk:
                log_print(f"  Item: {item}")
            
            http_info = None
            batch_input_simple_public_object_batch_input_upsert = BatchInputSimplePublicObjectBatchInputUpsert(inputs=chunk)
            try:
                api_response, status_code, http_info = client.crm.deals.batch_api.upsert_with_http_info(batch_input_simple_public_object_batch_input_upsert=batch_input_simple_public_object_batch_input_upsert)
                if status_code == 200:
                    log_print(f"{datetime.datetime.now()}: {input_chunks.index(chunk) + 1}/{len(input_chunks)} Success")
                else: 
                    log_print(f"{datetime.datetime.now()}: {input_chunks.index(chunk) + 1}/{len(input_chunks)} Failure")
                    logging.error(api_response)
            except ApiException as e:
                log_print(f"{datetime.datetime.now()}: {input_chunks.index(chunk) + 1}/{len(input_chunks)} Failure")
                logging.error("Exception when calling batch_api->upsert: %s\n" % e)
            # Check the rate limit and sleep 1s if necessary to avoid hitting the rate limit
            if http_info and http_info.get("x-hubspot-ratelimit-remaining") and int(http_info.get("x-hubspot-ratelimit-remaining")) < 50:
                time.sleep(1)

update_deal_properties(processing_list)