# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

# <ProgramSnippet>
import asyncio
import configparser
from msgraph.generated.models.o_data_errors.o_data_error import ODataError
from graph_marko import Graph

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
    try: 
        # await display_access_token(graph=graph)
        # await greet_user(graph)
        print(f"USERS: {graph.app_client.users}")
        await graph.download_attachments()
    finally:
        await graph.close()
    return
    # await list_inbox(graph=graph)
# </ProgramSnippet>

# <GreetUserSnippet>
async def greet_user(graph: Graph):
    user = await graph.get_user()
    if user:
        print('Hello,', user.display_name)
        # For Work/school accounts, email is in mail property
        # Personal accounts, email is in userPrincipalName
        print('Email:', user.mail or user.user_principal_name, '\n')
# </GreetUserSnippet>

# <ListInboxSnippet>
async def list_inbox(graph: Graph):
    # message_page = await graph.get_inbox()
    await graph.download_attachments()
# </ListInboxSnippet>

# <SendMailSnippet>
async def send_mail(graph: Graph):
    # Send mail to the signed-in user
    # Get the user for their email address
    user = await graph.get_user()
    if user:
        user_email = user.mail or user.user_principal_name

        await graph.send_mail('Testing Microsoft Graph', 'Hello world!', user_email or '')
        print('Mail sent.\n')
# </SendMailSnippet>

# <MakeGraphCallSnippet>
async def make_graph_call(graph: Graph):
    await graph.make_graph_call()
# </MakeGraphCallSnippet>

# Run main
asyncio.run(main())
