import asyncio
import configparser
import requests

endpoint_url = "https://api.productive.io/api/v2/deals"

async def main():

    print("Productive.io example")

    config = configparser.ConfigParser()
    config.read(['config.cfg', 'config.dev.cfg'])

    print(config.sections())

    token = config['auth_token']['token']
    organization_id = config['auth_token']['organization_id']

    print(token)

    headers = {'X-Auth-Token': f'{token}',
               'X-Organization-Id': f'{organization_id}',
        'Content-Type': 'application/vnd.api+json'}
    
    response = requests.get(endpoint_url, headers)

    print(f"Response: {response.json()}")
    if response.status_code == 200:
        print(response.json())

asyncio.run(main())