import asyncio
import configparser
import requests
from datetime import datetime

endpoint_url = "https://api.productive.io/api/v2"

def create_company(company_info : dict, custom_fields: dict, headers : dict) -> str:
    
    body = {
        "data": {
            "type": "companies",
            "attributes": {
                "name": f'{company_info.get('name')}',
                "default_currency": f'{company_info.get('default_currency')}',
                "billing_name": f'{company_info.get('full_name')}',
                "vat": f'{company_info.get('tax_id')}',
                "custom_fields": custom_fields,
                "contact": {
                    "phones": [
                        {
                            "name": "Contact phone",
                            "phone": company_info.get('phone_number')
                        }
                    ]
                }
            }
        }
    }
    response = requests.post(f'{endpoint_url}/companies', headers=headers, json=body)
    if response.status_code not in range(200, 299):
        print(f'Company creation response:\n{response.json()}')
    return response.json().get('data', {}).get('id', '')

def create_person(first_name : str, last_name : str, email : str, company_id : str, headers: dict) -> None:

    body = {
        "data": {
            "type": "people",
            "attributes": {
                "first_name": first_name,
                "last_name": last_name,
                "email": email
            },
            "relationships": {
                "company": {
                    "data": {
                        "type": "companies",
                        "id": company_id
                    }
                }
            }
        }
    }
    response = requests.post(f'{endpoint_url}/people', headers=headers, json=body)
    if response.status_code not in range(200, 299):
        print(f'Person creation response:\n{response.json()}')
    return

def create_deal(user_id : str, company_id : str, deal_name : str, custom_fields : dict, headers : dict) -> None:
    body = {
        "data": {
            "type": "deals",
            "attributes": {
                "name": deal_name,
                "date": datetime.today().strftime('%Y-%m-%d'),
                "deal_type_id": 2,
                "deal_status_id": 150458,
                "probability": 50,
                "currency": "EUR",
                "budget": False,
                "custom_fields": custom_fields,
            },
            "relationships": {
                "company": {
                    "data": {
                        "type": "compaines",
                        "id": company_id
                    }
                },
                "responsible": {
                    "data": {
                        "type": "users",
                        "id": user_id
                    }
                }
            }
        }
    }
    response = requests.post(f'{endpoint_url}/deals', headers=headers, json=body)
    if response.status_code not in range(200, 299):
        print(f'Deal creation response:\n{response.json()}')
    return

async def main():

    config = configparser.ConfigParser()
    config.read(['config.cfg', 'config.dev.cfg'])

    token = config['auth_token']['token']
    organization_id = config['auth_token']['organization_id']

    headers = {'X-Auth-Token': f'{token}',
               'X-Organization-Id': f'{organization_id}',
        'Content-Type': 'application/vnd.api+json'}

    company_custom_fields = dict(zip(
        list(config['company_custom_fields_ids'].values()), list(config['company_custom_values_ids'].values())))
    company_custom_fields[config['company_custom_fields_ids']['usluga_id']] = [config['company_custom_values_ids']['usluga_id']]

    company_info = {'name': 'TestNeyho.d.o.o', 'default_currency': 'EUR',
                    'full_name': 'TestNeyho.d.o.o', 'tax_id': 11223344556, "phone_number": "+385990100203"
                    }

    company_id = create_company(company_info, company_custom_fields, headers)
    
    create_person("TEST_NEYHOmarkoFirstName", "TEST_NEYHOprsoLastName", "TEST_NEYHO_new2@neyho.com", company_id, headers)

    deal_custom_fields = dict(zip(
        list(config['deal_custom_fields_ids'].values()), list(config['deal_custom_values_ids'].values())))
    deal_custom_fields[config['deal_custom_fields_ids']['usluga_id']] = [config['deal_custom_values_ids']['usluga_id']]

    owner_id = config['deal_owner']['deal_owner_id']
    create_deal(owner_id, company_id, 'RAC_' + company_info.get('full_name', ''), deal_custom_fields, headers)


asyncio.run(main())