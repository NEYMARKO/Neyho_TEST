import asyncio
import configparser
import requests
from datetime import datetime
import json

endpoint_url = "https://api.productive.io/api/v2"
ASCII_CODE_A = 65
ASCII_CODE_Z = 90

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
        print(f'Error occured while creating company:\n{response.json()}')
        return -1
    print(f"Sucessfully created company: {company_info.get('full_name', '')} ")
    return response.json().get('data', {}).get('id', '')

def link_person_to_company(person_id : str, company_id : str, headers : dict) -> bool:
    if not person_id:
        return False
    body = {
        "data": {
            "type": "people",
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
    response = requests.patch(f'{endpoint_url}/people/{person_id}', headers=headers, json=body)
    if response.status_code not in range(200, 299):
        print(f"Problem linking person with id {person_id} to company with id {company_id}")
        print(f"FULL PROBLEM:\n{response.json()}")
        return False
    print("Person sucessfully linked to company")
    return True

def create_person(first_name : str, last_name : str, email : str, company_id : str, headers: dict) -> bool:
    response = requests.get(f'{endpoint_url}/people?filter[email][contains]={email}', headers).json()
    data = response.get('data', [])
    if data:
        appended_ascii_codes = []
        mail_ascii_value = len(data) - 1 + ASCII_CODE_A
        while mail_ascii_value > 0:
            appended_ascii_codes.append(mail_ascii_value % (ASCII_CODE_Z - ASCII_CODE_A))
            mail_ascii_value //= (ASCII_CODE_A - ASCII_CODE_Z)
        old_email = email
        email += ''.join(chr(ASCII_CODE_A + c) for c in appended_ascii_codes)
        print(f"Person with e-mail address: {old_email} already exists => modified to {email}")

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
        print(f'Error occured while creating person:\n{response.json()}')
        return False
    print(f"Sucessfully created user: {first_name} {last_name}")
    return True

def create_deal(user_id : str, company_id : str, deal_name : str, custom_fields : dict, service_id : str, project_id : str, headers : dict) -> bool:
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
                },
                "service": {
                    "data": {
                        "type": "services",
                        "id": service_id
                    }
                },
                "project": {
                    "data": {
                        "type": "projects",
                        "id": project_id
                    }
                }
            }
        }
    }
    response = requests.post(f'{endpoint_url}/deals', headers=headers, json=body)
    if response.status_code not in range(200, 299):
        print(f'Error occured while creating deal:\n{response.json()}')
        return False
    print(f"Sucessfully created deal: {deal_name}")
    return True

def create_project(name : str, project_manager_id : str, company_id : str, workflow_id : str, headers : dict) -> str:
    body = {
        "data": {
            "type": "projects",
            "attributes": {
                "name": name,
                "project_type_id": 2
            },
            "relationships": {
                "company": {
                    "data": {
                        "type": "companies",
                        "id": company_id
                    }
                },
                "project_manager": {
                    "data": {
                        "type": "people",
                        "id": project_manager_id
                    }
                },
                "workflow": {
                    "data": {
                        "type": "workflows",
                        "id": workflow_id
                    }
                }
            }
        }
    }
    response = requests.post(f'{endpoint_url}/projects', headers=headers, json=body)
    if response.status_code not in range(200, 299):
        print(f'Error occured while creating project:\n{response.json()}')
        return ""
    print(f"Sucessfully created project: {name}")
    return response.json().get('data', {}).get('id', '')

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

    company_info = {'name': 'TestNeyho.d.o.o_rac', 'default_currency': 'EUR',
                    'full_name': 'TestNeyho.d.o.o_rac', 'tax_id': 11223344556, "phone_number": "+385990100203"
                    }

    # response = requests.get(f'{endpoint_url}/custom_fields', headers)
    # response = requests.get(f'{endpoint_url}/custom_fields?filter[customizable_type]=Deals&include=options', headers)
    # response = requests.get(f'{endpoint_url}/services?include=service_type', headers)
    # response = requests.get(f'{endpoint_url}/projects?include=project_manager,company,workflow', headers)
    # response = requests.get(f'{endpoint_url}/deals?include=project', headers)
    # with open('deals_with_projects.json', 'w+', encoding='utf-8') as f:
    #     json.dump(response.json(), f, ensure_ascii=False, indent=4)
    company_id = create_company(company_info, company_custom_fields, headers)
    
    if not company_id:
        return
    created = create_person("TEST_NEYHO_rac", "TEST_NEYHO_surname", "TEST_NEYHO_rac@neyho.comR", company_id, headers)

    if not created:
        return
    
    deal_custom_fields = dict(zip(
        list(config['deal_custom_fields_ids'].values()), list(config['deal_custom_values_ids'].values())))
    deal_custom_fields[config['deal_custom_fields_ids']['usluga_id']] = [config['deal_custom_values_ids']['usluga_id']]

    project_manager_id = config['projects']['project_manager_id']
    default_workflow_id = config['projects']['default_workflow_id']   
    project_id = create_project('RAC_' + company_info.get('full_name', ''), project_manager_id, company_id, default_workflow_id, headers)

    if not project_id:
        return
    
    owner_id = config['deal_owner']['deal_owner_id']
    service_id = config['services']['rac_service_id']
    create_deal(owner_id, company_id, 'RAC_' + company_info.get('full_name', ''), deal_custom_fields, service_id, project_id, headers)
asyncio.run(main())