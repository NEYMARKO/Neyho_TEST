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
    # delta_link = "https://graph.microsoft.com/v1.0/users/b247c66a-2651-4ff9-a6a1-858a24f30387/mailFolders('inbox')/messages/delta?$deltatoken=rOXIXEHGV-4NmbPgJNYAPD06A6JFWLlafepI_1Zd28PoUY51AElZ2CvNWFM94zfykbxIwpbp7NnTJS7Dx6viWVmVW9eVr5rIJTDx8cYURLeCxxSKMQRMqE_syJWvmnoJkCezLM3RZ4r7eHkNm4wOzQVVo_JZx91HGbkohai-anaGCnmfLR5xJiGar8K_3-EG.6x9CO2Zf-F_05ZksvN4smTFhxkwaCUwFMdKnO2K0BdA"
    # delta_link = "https://graph.microsoft.com/v1.0/users/b247c66a-2651-4ff9-a6a1-858a24f30387/mailFolders('inbox')/messages/delta?$deltatoken=rOXIXEHGV-4NmbPgJNYAPLpWZR-uRNwmg1Nyk8iuzzF8g7z3kcp9CEkprHfC7BZCtQ7yxWCxjEKxb_tu7VhbU3mlcf_99s_G00Dv6lsljJnQQdWsQI-4NHZBCjBgcoq6QAIwBdU1XUuCblq2ohbx7qgRuR8XRS5SwD6VUou1xi2aIiY3m664A-ONw8I4py5v.y5-mnvhep3ELmLUTTfH2Ew4BaYBSDI6RPApV_rzqbOo"
    delta_link = "https://graph.microsoft.com/v1.0/users/b247c66a-2651-4ff9-a6a1-858a24f30387/mailFolders('inbox')/messages/delta?$deltatoken=GpfmEUfGTQLKhYJrytuF2ojdptZhXElRlhw_qDYO9ACxNqVz-4Dymf2y6qgJxG7FnipVDsiewXPjK--TCxdP13jvdp_Y-rmxrp_L_-hXfRZQ8vzhP1oTeWsnn-AWH6KQZXpZNt-e_n45PVj6Uxagoc2RDSRy540emJl429gb3gG2w7ZhE-wLTYgOHpx32T4s.LsHuBxpthRNwsIZJXSEv6QxPjIiIdddgND8LPShwcKE"
    # delta_link = None
    # messages = await graph.get_mails(recipient_id=recipient_id)
    # next_link = messages.odata_next_link
    # if not next_link:
    #     delta_link = messages.odata_delta_link

    for recipient_id in RECIPIENTS_LIST:
        all_messages = []
        response = await graph.get_mails(recipient_id=recipient_id, delta_url=delta_link)
        all_messages.extend(response.value)
        next_link = response.odata_next_link
        # print(f"NEXT LINK: {next_link}")
        while(next_link):
            response = await graph.get_mails(recipient_id=recipient_id, delta_url=next_link)
            # print(f"{response=}")
            all_messages.extend(response.value)
            next_link = response.odata_next_link
        # print(f"{messages=}")
        # print(f"{messages=}")
        await graph.download_attachments(messages=all_messages, recipient_id=recipient_id)
        delta_link = response.odata_delta_link
    print(f"Delta link: {delta_link}")
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
        
    await graph.close()
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
