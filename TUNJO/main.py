import asyncio
import configparser
import requests

endpoint_url = "https://api.productive.io/api/v2"

async def post_request(url : str, headers : dict[str]) -> None:
    return

# def create_custom_field()

def create_company(company_info : dict) -> None:
    
    body = {
        "data": {
            "type": "companies",
            "attributes": {
                "name": f'{company_info.get('name')}',
                "default_currency": f'{company_info.get('default_currency')}',
                "billing_name": f'{company_info.get('full_name')}',
                "vat": f'{company_info.get('tax_id')}',
                "custom_fields":
                    {

                    },
                "tag_list": [
                    "partner",
                    "priority"
                ],
                "buyer_reference": "BUYER123",
                "contact": {
                    "phones": [
                        {
                            "name": "Contact phone",
                            "phone": "(555) 123-4567"
                        }
                ],
                "emails": [
                    {
                        "name": "Email",
                        "email": "contact@exmaple.com"
                    }
                ],
                "websites": [
                    {
                        "name": "Official website",
                        "website": "example-website.com"
                    }
                ],
                "addresses": [
                        {
                            "name": "Headquarters",
                            "billing_address": "Main Street",
                            "city": "City",
                            "state": "State",
                            "zipcode": "11111",
                            "country": "Country"
                        }
                    ]
                }
            }
        }
    }
    return

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
    
    # response = requests.get(f'{endpoint_url}/custom_fields', headers)
    company_info = {'name': 'TestNeyho.d.o.o', 'default_currency': 'EUR',
                    'full_name': 'TestNeyho.d.o.o', 'tax_id': 11223344556,
                    }
    response = requests.get(f'{endpoint_url}/custom_fields/34302?include=options', headers)
    # create_company(company_info=company_info)
    print(f"Response: {response.json()}")
    # if response.status_code == 200:
    #     print(response.json())

asyncio.run(main())