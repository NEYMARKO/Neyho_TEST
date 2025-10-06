# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import asyncio
import configparser
from msgraph.generated.models.o_data_errors.o_data_error import ODataError
from graph_marko import Graph

from time import sleep
# RECIPIENTS_LIST = ["05ff32cc-49a4-48ae-a4a6-808e8864e71b", "b247c66a-2651-4ff9-a6a1-858a24f30387"]
RECIPIENTS_LIST = ["b247c66a-2651-4ff9-a6a1-858a24f30387"]

async def display_access_token(graph: Graph) -> None:
    token = await graph.get_app_only_token()
    print(f"App-only token: {token}")
    return

async def main():
    print('Python Graph Tutorial\n')

    config = configparser.ConfigParser()
    config.read(['config.cfg', 'config.dev.cfg'])
    print(config.sections())

    azure_settings = config['azure']
    
    graph: Graph = Graph(azure_settings)
    
    token = None
    m = None
    messages = None
    for recipient_id in RECIPIENTS_LIST:
                messages = await graph.get_mails(recipient_id=recipient_id)
                await graph.download_attachments(messages=messages, recipient_id=recipient_id)
                print("\n" * 2)
    # while True:
    #     if not token:
    #         token = await graph.get_app_only_token()
    #     try:
    #         for recipient_id in RECIPIENTS_LIST:
    #             messages = await graph.get_mails(recipient_id=recipient_id)
    #             await graph.download_attachments(messages=messages, recipient_id=recipient_id)
    #             print("\n" * 2)
    #     except Exception as e:
    #         print(f"Exception occured: {e}")
    #     print("\n" * 2)
    #     sleep(5)
        
    # await graph.close()
    # return

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
