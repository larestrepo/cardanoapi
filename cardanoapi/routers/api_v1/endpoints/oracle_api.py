from fastapi import APIRouter

router = APIRouter()

import requests
from requests.structures import CaseInsensitiveDict
import json
import os

@router.get("/price", 
                summary="Fetch price index data for pre-selected tokens",
                response_description="query tip"
                )
async def oracle_price():
    """Returns price index data"""

    BASE_URL = "https://api-mainnet-prod.minswap.org/coinmarketcap/v2/pairs"
    params = {
        'format': 'json'
    }
    headers = CaseInsensitiveDict()

    rawResult = requests.get(BASE_URL, headers=headers, params=params)
    data = json.loads(rawResult.content.decode('utf-8'))

    with open(os.getcwd() + '/db/token_list/token_registry.json', 'r') as file:
        token_registry = json.load(file)
    
    filter_data = {}
    token_registry_policy = list(token_registry.values())
    for policy in token_registry_policy:
        key_str = policy + '_lovelace'
        if key_str in data:
            filter_data[key_str] = data[key_str]
    
    return filter_data