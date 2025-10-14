import asyncio
import configparser
import requests

endpoint_url = "https://api.productive.io/api/v2"

dropdown_ids_map = {
        "sektor":
        {
            "field_id": "8028", "value_name": "Ostalo", "value_id": "27775"
        },
        "regija":
        {
            "field_id": "11727", "value_name": "Zagreb", "value_id": "40131"
        },
        "kanal": 
        {
            "field_id": "11793", "value_name": "WEB", "value_id": "40318"
        },
        "status":
        {
            "field_id": "11795", "value_name": "Deals", "value_id": "40321"
        },
        "prihodi":
        {
            "field_id": "11797", "value_name": "< 2mn ", "value_id": "40323",     
        },
        "usluga": {
            "field_id": "34302", "value_name": "Računovodstvo", "value_id": "111117"
        },
        "Broj usluga": {
            "field_id": "75463", "value_name": "Jedna usluga", "value_id": "257767"
        },
    }

deals_map = {
    "usluga":
    {
        "field_id": "9410", "value_name": "Računovodstvo", "value_id": "32690"
    },
    "kanal":
    {
        "field_id": "11948", "value_name": "WEB", "value_id": "40797"
    },

}

def create_company(company_info : dict, headers : dict) -> str:
    
    body = {
        "data": {
            "type": "companies",
            "attributes": {
                "name": f'{company_info.get('name')}',
                "default_currency": f'{company_info.get('default_currency')}',
                "billing_name": f'{company_info.get('full_name')}',
                "vat": f'{company_info.get('tax_id')}',
                "custom_fields": {
                    "8028": "27775",
                    "11727": "40131",
                    "11793": "40318",
                    "11795": "40321",
                    "11797": "40323",
                    "34302": ["111117"],
                    "75463": "257767"
                },
            }
        }
    }
    response = requests.post(f'{endpoint_url}/companies', headers=headers, json=body).json()
    print(f'Company creation response:\n{response}')
    return response.get('data', {}).get('id', '')

def create_person(first_name : str, last_name : str, email : str, company_id : str, headers: dict) -> str:

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
    response = requests.post(f'{endpoint_url}/people', headers=headers, json=body).json()
    print(f'Person creation response:\n{response}')
    return response.get('data', {}).get('id', '')

def create_deal(user_id : str, company_id : str, deal_name : str, headers : dict) -> None:
    print(f"User id: {user_id}, company id: {company_id}")
    body = {
        "data": {
            "type": "deals",
            "attributes": {
                "name": deal_name,
                # "date": "2025-10-14",
                # "date": "2025-10-14T00:00:00Z",
                "date": "2025-10-14T00:00:00+00:00",
                "deal_type_id": 2,
                "deal_status_id": 150458,
                "probability": 50,
                "currency": "EUR",
                # "deal_status_id": 1,
                "budget": False,
                "custom_fields": {
                    "9410": ["32690"],
                    "11948": "40797"
                },
                "responsible": user_id,
                "company_id": company_id
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
    # print(body)
    response = requests.post(f'{endpoint_url}/deals', headers=headers, json=body).json()
    print(f'Deal creation response:\n{response}')
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
    # response = requests.get(f'{endpoint_url}/custom_fields/75463?include=options', headers)
    # response = requests.get(f'{endpoint_url}/people', headers)
    # print(response.json())
    
    # company_id = create_company(company_info=company_info, headers=headers)
    company_id = "1170610"
    
    # company_id = 1170573
    # print(f"Company id: {company_id}")
    
    # person_id = create_person("TEST_NEYHOmarko", "TEST_NEYHOprso", "TEST_NEYHO@neyho.com", company_id, headers)
    user_id = "232675"
    # user_id = "65816"

    # response = requests.get(f'{endpoint_url}/people', headers)
    # print(response.json())

    create_deal(user_id, company_id, 'RAC_' + company_info.get('full_name', ''), headers)
    # link_person_to_company(person_id, company_id, headers)
    # person_id = 1083219
    # create_contact(person_id, "neyho5@neyho.com", headers)
    # response = requests.get(f'{endpoint_url}/custom_fields/11948?include=options', headers)
    # response = requests.get(f'{endpoint_url}/contact_entries/3536716?include=person,company', headers)
    # print(response.json())

    # print("About to send")
    # print("Sent")
    # print(f"Response: {response.json()}")
    # if response.status_code == 200:
    #     print(response.json())

asyncio.run(main())