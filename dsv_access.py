"""
Credential Encryption Utility
Run this script once to encrypt your DSV API credentials

Created on Mon Dec  1 12:58:59 2025
Help: https://docs.python.org/3/library/functions.html

@User: dpp
@author: Dean Petersen
@Contact: dpp@idealcombi.dk
    # ========================================
    # SETUP: Get encryption password from system environment variable
    # ========================================
    # Set system environment variable (persistent, Machine level):
    # [System.Environment]::SetEnvironmentVariable('DSV_ENCRYPTION_PASSWORD', 'your_password', 'Machine')
    # Note: Requires Administrator privileges
    # Or use Windows System Properties > Environment Variables (System variables section)    
"""
import requests
import json
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import sys


class CredentialDecryptor:
    """
    Handles decryption of encrypted credentials
    Use encrypt_credentials.py to generate encrypted credentials
    """
    
    @staticmethod
    def derive_key_from_password(password: str) -> bytes:
        """
        Derive a proper Fernet key from a user password
        Must use the same salt and parameters as encryption
        
        Args:
            password: User's password string
        
        Returns:
            bytes: 32-byte Fernet-compatible key
        """
        # Must match the salt used in encrypt_credentials.py
        salt = b'dsv_api_salt_2025'
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    @staticmethod
    def decrypt_credential(encrypted_credential: str, key: bytes) -> str:
        """
        Decrypt a credential string
        
        Args:
            encrypted_credential: The encrypted credential
            key: Encryption key used for encryption
        
        Returns:
            str: Decrypted credential
        """
        cipher = Fernet(key)
        decrypted = cipher.decrypt(encrypted_credential.encode())
        return decrypted.decode()


class DSVAPIClient:
    """
    Python client for DSV API
    Handles authentication and shipment tracking operations
    """
    
    def __init__(self, client_id: str, client_secret: str, 
                 access_subscription_key: str, tracking_subscription_key: str,
                 auto_authenticate: bool = True):
        """
        Initialize the DSV API client
        
        Args:
            client_id: Your API username (client_id)
            client_secret: Your API password (client_secret)
            access_subscription_key: DSV subscription key for OAuth endpoints
            tracking_subscription_key: DSV subscription key for tracking endpoints
            auto_authenticate: Automatically get access token on initialization (default: True)
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_subscription_key = access_subscription_key
        self.tracking_subscription_key = tracking_subscription_key
        
        self.base_url = "https://api.dsv.com/my"
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        
        if auto_authenticate:
            self.get_access_token()
    
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


def create_client_from_encrypted_credentials(
    encrypted_credentials: Dict[str, str],
    password: Optional[str] = None,
    auto_authenticate: bool = True
) -> DSVAPIClient:
    """
    Create a DSVAPIClient from encrypted credentials.
    
    Args:
        encrypted_credentials: Dictionary with encrypted credentials
            {'client_id': '...', 'client_secret': '...', 
             'access_subscription_key': '...', 'tracking_subscription_key': '...'}
        password: Encryption password. If None, reads from DSV_ENCRYPTION_PASSWORD env var
        auto_authenticate: Automatically get access token on initialization (default: True)
    
    Returns:
        DSVAPIClient: Initialized API client
        
    Example:
        from test_dsv_access import create_client_from_encrypted_credentials
        
        encrypted_creds = {
            'client_id': 'gAAAAABm...',
            'client_secret': 'gAAAAABm...',
            'access_subscription_key': 'gAAAAABm...',
            'tracking_subscription_key': 'gAAAAABm...'
        }
        
        client = create_client_from_encrypted_credentials(encrypted_creds)
        shipments = client.get_shipment_list(statuses=["IN_PROGRESS"], transports=["ROAD"])
    """
    if password is None:
        password = os.getenv('DSV_ENCRYPTION_PASSWORD')
        if not password:
            raise ValueError(
                "Password not provided and DSV_ENCRYPTION_PASSWORD environment variable not set. "
                "Either pass password parameter or set the environment variable."
            )
    
    decryptor = CredentialDecryptor()
    encryption_key = decryptor.derive_key_from_password(password)
    
    # Decrypt all credentials
    client_id = decryptor.decrypt_credential(encrypted_credentials['client_id'], encryption_key)
    client_secret = decryptor.decrypt_credential(encrypted_credentials['client_secret'], encryption_key)
    access_subscription_key = decryptor.decrypt_credential(
        encrypted_credentials['access_subscription_key'], encryption_key
    )
    tracking_subscription_key = decryptor.decrypt_credential(
        encrypted_credentials['tracking_subscription_key'], encryption_key
    )
    
    return DSVAPIClient(
        client_id=client_id,
        client_secret=client_secret,
        access_subscription_key=access_subscription_key,
        tracking_subscription_key=tracking_subscription_key,
        auto_authenticate=auto_authenticate
    )


# Example usage
if __name__ == "__main__":
    # ========================================
    # SETUP: Get encryption password from system environment variable
    # ========================================
    # Set system environment variable (persistent, Machine level):
    # [System.Environment]::SetEnvironmentVariable('DSV_ENCRYPTION_PASSWORD', 'your_password', 'Machine')
    # Note: Requires Administrator privileges
    # Or use Windows System Properties > Environment Variables (System variables section)
    
    print("DSV API Client - Decrypting Credentials")
    print("=" * 60)
    
    password = os.getenv('DSV_ENCRYPTION_PASSWORD')
    
    if not password:
        print("\n✗ Error: System environment variable DSV_ENCRYPTION_PASSWORD is not set")
        print("\nTo set it permanently (Machine level - requires Administrator):")
        print("[System.Environment]::SetEnvironmentVariable('DSV_ENCRYPTION_PASSWORD', 'your_password', 'Machine')")
        print("\nOr set it via: Control Panel > System > Advanced system settings > Environment Variables")
        print("Add it under 'System variables' (not User variables)")
        exit(1)
    
    print("✓ Using password from system environment variable DSV_ENCRYPTION_PASSWORD")
    
    decryptor = CredentialDecryptor()
    encryption_key = decryptor.derive_key_from_password(password)
    
    # Your encrypted credentials (replace with your actual encrypted values)
    encrypted_credentials = {
        "client_id": "gAAAAABpLX61Hrbkub6YhRviwDsh1b2i_jigoTvIaJeXMm2cZIJpctRjMl9h9invjC4H-VJ_D0-AhAs6Owkrg1gbDK8eOO15gRp8VkUeAJHPnSOIwy4i99U=",
        "client_secret": "gAAAAABpLX61nYEulQsykYheROQzSZ4MJJvhfT71Gvo-Enrw2CshMVIFiZok0DIyi2WrsltASLomKoC5MgImH0hpeUaAconrsw==",
        "access_subscription_key": "gAAAAABpLX61OjF3xaVxZTB46sBMjsDSkAmd-vbc6_6Wc5aa4NBObh7_RZlAglUklfRW8kQ4UqRkC-65v13wMXy6XGt41B1vZEgfKsVzUWEkCD4rit485x69XYeqlF4fz8al5hlCrUQL",
        "tracking_subscription_key": "gAAAAABpLX61zRluwJeArxgBkCFoqBGRIYSU9wxWNT9n25-_OI7tkwMnNQaOYTOxha33trxcdxzHPfNFtRnCbs_-VW0SA4X6NiWeRH-gbuPZLP9l8SRI_ccJWpEf-tuBQFKeWFXpFTWA"
    }
    
    # Decrypt credentials
    try:
        client_id = decryptor.decrypt_credential(encrypted_credentials['client_id'], encryption_key)
        client_secret = decryptor.decrypt_credential(encrypted_credentials['client_secret'], encryption_key)
        access_subscription_key = decryptor.decrypt_credential(encrypted_credentials['access_subscription_key'], encryption_key)
        tracking_subscription_key = decryptor.decrypt_credential(encrypted_credentials['tracking_subscription_key'], encryption_key)
        
        print("✓ Credentials decrypted successfully")
        print("=" * 60)
        print()
        
        # Initialize the client with decrypted credentials
        client = DSVAPIClient(
            client_id=client_id,
            client_secret=client_secret,
            access_subscription_key=access_subscription_key,
            tracking_subscription_key=tracking_subscription_key
        )
        
        # Step 1: Authenticate and get access token
        print("Authenticating...")
        auth_response = client.get_access_token()
        print(f"✓ Authentication successful")
        print(f"Access Token: {client.access_token[:20]}...")
        print("\nClient is ready to use. Call client.get_shipment_list() to fetch shipments.")
        
    except requests.exceptions.HTTPError as e:
        print(f"✗ HTTP Error: {e}")
        print(f"Response: {e.response.text}")
    except Exception as e:
        print(f"✗ Error: {e}")