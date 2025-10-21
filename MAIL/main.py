# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import asyncio
import configparser
from msgraph.generated.models.o_data_errors.o_data_error import ODataError
from graph_marko import Graph

from time import sleep
# RECIPIENTS_LIST = ["05ff32cc-49a4-48ae-a4a6-808e8864e71b", "b247c66a-2651-4ff9-a6a1-858a24f30387"]
RECIPIENTS_LIST = ["b247c66a-2651-4ff9-a6a1-858a24f30387"]
# RECIPIENTS_LIST = ["05ff32cc-49a4-48ae-a4a6-808e8864e71b"]


#  File "C:\Users\MarkoProsenjak\Desktop\Neyho\Neyho_TEST\MAIL\.venv\Lib\site-packages\httpx\_transports\default.py", line 118, in map_httpcore_exceptions
    # raise mapped_exc(message) from exc
# httpx.ReadTimeout  --- puko internet

###
#   File "C:\Users\MarkoProsenjak\Desktop\Neyho\Neyho_TEST\MAIL\graph_marko.py", line 133, in download_attachments
#     save_attachment(attachments)
#     ~~~~~~~~~~~~~~~^^^^^^^^^^^^^
#   File "C:\Users\MarkoProsenjak\Desktop\Neyho\Neyho_TEST\MAIL\graph_marko.py", line 34, in save_attachment
#     if a.content_bytes and file_valid(a):
#AttributeError: 'ItemAttachment' object has no attribute 'content_bytes'. Did you mean: 'content_type'? --- mail u mailu

#   File "C:\Users\MarkoProsenjak\Desktop\Neyho\Neyho_TEST\MAIL\.venv\Lib\site-packages\kiota_http\httpx_request_adapter.py", line 573, in throw_failed_responses       
#     raise exc
# msgraph.generated.models.o_data_errors.o_data_error.ODataError:
#         APIError
#         Code: 404
#         message: None
#         error: MainError(additional_data={}, code='ErrorItemNotFound', details=None, inner_error=None, message='The specified object was not found in the store., The process failed to get the correct properties.', target=None)


async def display_access_token(graph: Graph) -> None:
    token = await graph.get_app_only_token()
    print(f"App-only token: {token}")
    return

def write_to_cfg(file_name : str, config : configparser, section_name : str) -> None:
    with open(file_name, 'w') as config_file:
       config.write(config_file)
    print(f"Updated delta link to value: {config[section_name].get('delta_value')}")

async def main():
    print('Python Graph Tutorial\n')

    config = configparser.ConfigParser()
    config.read(['config.cfg', 'config.dev.cfg'])
    print(config.sections())

    azure_settings = config['azure']
    graph: Graph = Graph(azure_settings)
    
    token = None
    delta_link = None
    while True:
        if not token:
            token = await graph.get_app_only_token()
        for recipient_id in RECIPIENTS_LIST:
            section_name = f'delta.{recipient_id}'
            if config.has_section(section_name):
                delta_link = config[section_name].get('delta_value', '')
            all_messages = []
            response = await graph.get_mails(recipient_id=recipient_id, delta_url=delta_link)
            all_messages.extend(response.value)
            next_link = response.odata_next_link
            while(next_link):
                response = await graph.get_mails(recipient_id=recipient_id, delta_url=next_link)
                all_messages.extend(response.value)
                next_link = response.odata_next_link
            await graph.download_attachments(messages=all_messages, recipient_id=recipient_id)
            if not config.has_section(section_name):
                config.add_section(section_name)
            config[section_name]['delta_value'] = response.odata_delta_link
            if len(all_messages) > 0:
                write_to_cfg('config.cfg', config, section_name)
        print("\n" * 2)
        print("-*-" * 50)
        sleep(5)
        
    await graph.close()
    return

async def greet_user(graph: Graph):
    user = await graph.get_user()
    if user:
        print('Hello,', user.display_name)
        # For Work/school accounts, email is in mail property
        # Personal accounts, email is in userPrincipalName
        print('Email:', user.mail or user.user_principal_name, '\n')

async def list_inbox(graph: Graph):
    # message_page = await graph.get_inbox()
    await graph.download_attachments()

# <SendMailSnippet>
async def send_mail(graph: Graph):
    # Send mail to the signed-in user
    # Get the user for their email address
    user = await graph.get_user()
    if user:
        user_email = user.mail or user.user_principal_name

        await graph.send_mail('Testing Microsoft Graph', 'Hello world!', user_email or '')
        print('Mail sent.\n')

asyncio.run(main())
