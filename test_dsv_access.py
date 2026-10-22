# -*- coding: utf-8 -*-
"""
Created on Mon Dec  1 11:19:33 2025
Help: https://docs.python.org/3/library/functions.html

@User: DPP
@author: Dean Petersen
@Contact: dpp@idealcombi.dk
"""

import requests
import json
from typing import Optional, Dict, Any


class DSVAPIClient:
    """
    Python client for DSV API
    Handles authentication and shipment tracking operations
    """
    
    def __init__(self, client_id: str, client_secret: str, 
                 access_subscription_key: str, tracking_subscription_key: str):
        """
        Initialize the DSV API client
        
        Args:
            client_id: Your API username (client_id)
            client_secret: Your API password (client_secret)
            access_subscription_key: DSV subscription key for OAuth endpoints
            tracking_subscription_key: DSV subscription key for tracking endpoints
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_subscription_key = access_subscription_key
        self.tracking_subscription_key = tracking_subscription_key
        
        self.base_url = "https://api.dsv.com/my"
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
    
    def get_access_token(self) -> Dict[str, Any]:
        """
        Get access token using client credentials grant type
        
        Returns:
            dict: Response containing access_token and refresh_token
        """
        url = f"{self.base_url}/oauth/v1/token"
        
        headers = {
            "DSV-Subscription-Key": self.access_subscription_key
        }
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data.get("access_token")
        self.refresh_token = token_data.get("refresh_token")
        
        return token_data
    
    def refresh_access_token(self) -> Dict[str, Any]:
        """
        Refresh the access token using the refresh token
        
        Returns:
            dict: Response containing new access_token and refresh_token
        """
        if not self.refresh_token:
            raise ValueError("No refresh token available. Please authenticate first.")
        
        url = f"{self.base_url}/oauth/v1/token"
        
        headers = {
            "DSV-Subscription-Key": self.access_subscription_key
        }
        
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data.get("access_token")
        self.refresh_token = token_data.get("refresh_token")
        
        return token_data
    
    def get_shipment_list(self, statuses: list = None, transports: list = None) -> Dict[str, Any]:
        """
        Retrieve a list of shipments for a specific period, transport mode or shipment status
        
        Args:
            statuses: List of shipment statuses (e.g., ["IN_PROGRESS"])
            transports: List of transport modes (e.g., ["ROAD"])
        
        Returns:
            dict: Response containing shipment list
        """
        if not self.access_token:
            raise ValueError("Not authenticated. Please call get_access_token() first.")
        
        url = f"{self.base_url}/tracking/v2/shipments/list"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "DSV-Subscription-Key": self.tracking_subscription_key,
            "Content-Type": "application/json"
        }
        
        # Default values from your Postman collection
        payload = {
            "statuses": statuses or ["IN_PROGRESS"],
            "transports": transports or ["ROAD"]
        }
        
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        return response.json()


# Example usage
if __name__ == "__main__":
    # Initialize the client with your credentials
    # Replace these with your actual values from the DSV API environment
    client = DSVAPIClient(
        client_id="api.dsv@idealcombi.com",
        client_secret="VKmu?8J@G$",
        access_subscription_key="dda22d620714439cb381169047fbef93",
        tracking_subscription_key="1282689ddc594f40aa0529d6cdc7ac64"
    )
    
    try:
        # Step 1: Authenticate and get access token
        print("Authenticating...")
        auth_response = client.get_access_token()
        print("✓ Authentication successful")
        print(f"Access Token: {client.access_token[:20]}...")
        
        # Step 2: Get shipment list
        print("\nFetching shipment list...")
        shipments = client.get_shipment_list(
            statuses=["IN_PROGRESS"],
            transports=["ROAD"]
        )
        print("✓ Retrieved shipments")
        print(json.dumps(shipments, indent=2))
        
        # Optional: Refresh token example
        # print("\nRefreshing access token...")
        # refresh_response = client.refresh_access_token()
        # print(f"✓ Token refreshed")
        
    except requests.exceptions.HTTPError as e:
        print(f"✗ HTTP Error: {e}")
        print(f"Response: {e.response.text}")
    except Exception as e:
        print(f"✗ Error: {e}")