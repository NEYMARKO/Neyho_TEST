# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

# <UserAuthConfigSnippet>
import base64
from configparser import SectionProxy
from azure.identity.aio import ClientSecretCredential
from msgraph import GraphServiceClient
from msgraph.generated.users.item.user_item_request_builder import UserItemRequestBuilder
from msgraph.generated.users.users_request_builder import UsersRequestBuilder
from msgraph.generated.users.item.mail_folders.item.messages.messages_request_builder import (
    MessagesRequestBuilder)
from msgraph.generated.users.item.send_mail.send_mail_post_request_body import (
    SendMailPostRequestBody)
from msgraph.generated.models.message import Message
from msgraph.generated.models.item_body import ItemBody
from msgraph.generated.models.body_type import BodyType
from msgraph.generated.models.recipient import Recipient
from msgraph.generated.models.email_address import EmailAddress
from kiota_abstractions.base_request_configuration import RequestConfiguration

from bs4 import BeautifulSoup
import os
import json
import re 

DOWNLOAD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ATTS_DOWNLOAD')

def file_valid(attachment):
    # return attachment.additional_data.get("@odata.type") == "#microsoft.graph.fileAttachment" and \
    # (attachment.name.endswith("pdf") or attachment.name.endswith("xlsx"))
    return attachment.odata_type == "#microsoft.graph.fileAttachment" and \
    attachment.name.endswith("pdf") or attachment.name.endswith("xlsx")

def save_attachment(attachments):
    # print("ENTERED SAVE ATTACHMENT")
    for a in attachments.value:
        # print(f"Attachment: {a.name}")
        # content_bytes = a.content_bytes
        # odata_type = a.odata_type
        # print(f"{odata_type=}")
        # print(f"{a=}")
        # print(f"{content_bytes}")
        # json_data = json.loads(a)
        # print(f"{json_data=}")
        if a.content_bytes and file_valid(a):
            file_bytes = base64.b64decode(a.content_bytes)
            with open(f"ATTS_DOWNLOAD/{a.name}", "wb") as f:
                f.write(file_bytes)
                f.close()
            print(f"Saved: {a.name}")

def clean_body(body : str) -> str:
    # print(f"DIRTY BODY: {body}")
    soup = BeautifulSoup(body, "html.parser")

    for img in soup.find_all("img"):
        img.decompose()

    for sig in soup.find_all(attrs={"class": re.compile(r"signature|footer", re.I)}):
        sig.decompose()

    text = soup.get_text(separator="\n").strip()
    return re.sub('From?(.*?)Subject:', '', text, flags=re.DOTALL).strip()

class Mail:
    def __init__(self, message):
        self.body = re.sub(r'\<[^>]*\>', '', message.body.content)
        self.sender = message.sender,
        self.subject = message.subject,
        self.attachments = [],

class Graph:
    settings: SectionProxy
    client_credential: ClientSecretCredential
    app_client: GraphServiceClient

    def __init__(self, config: SectionProxy):
        self.settings = config
        client_id = self.settings['clientId']
        tenant_id = self.settings['tenantId']
        client_secret = self.settings['clientSecret']

        self.client_credential = ClientSecretCredential(tenant_id, client_id, client_secret)
        self.app_client = GraphServiceClient(self.client_credential)
# </UserAuthConfigSnippet>

    async def get_app_only_token(self):
        graph_scope = 'https://graph.microsoft.com/.default'
        access_token = await self.client_credential.get_token(graph_scope)
        return access_token.token
    
    # <GetUserTokenSnippet>
    async def get_user_token(self):
        graph_scopes = self.settings['graphUserScopes']
        access_token = self.device_code_credential.get_token(graph_scopes)
        return access_token.token
    # </GetUserTokenSnippet>

    # <GetUserSnippet>
    async def get_user(self):
        # Only request specific properties using $select
        query_params = UserItemRequestBuilder.UserItemRequestBuilderGetQueryParameters(
            select=['displayName', 'mail', 'userPrincipalName']
        )

        request_config = UserItemRequestBuilder.UserItemRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )

        user = await self.app_client.me.get(request_configuration=request_config)
        return user
    # </GetUserSnippet>

    # <GetInboxSnippet>
    async def get_inbox(self):
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            # Only request specific properties
            select=['from', 'isRead', 'receivedDateTime', 'subject', 'id'],
            # Get at most 25 results
            top=25,
            # Sort by received time, newest first
            orderby=['receivedDateTime DESC']
        )
        request_config = MessagesRequestBuilder.MessagesRequestBuilderGetRequestConfiguration(
            query_parameters= query_params
        )

        messages = await self.app_client.me.mail_folders.by_mail_folder_id('inbox').messages.get(
                request_configuration=request_config)
        return messages
    # </GetInboxSnippet>

    async def get_mails(self, recipient_id):
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            select = ['sender', 'subject', 'hasAttachments', 'body'],
            top = 1,
            orderby=['receivedDateTime DESC']
        )
        request_configuration = RequestConfiguration(
            query_parameters=query_params
        )
        # request_configuration.headers.add("Prefer", f"outlook.body-content-type=\"text\"")
        messages = await self.app_client.users.by_user_id(recipient_id).mail_folders.\
        by_mail_folder_id('inbox').messages.get(
            request_configuration
        )
        return messages

    async def download_attachments(self, messages, recipient_id): 
        for message in messages.value:
            # print(f"SUBJECT: {message.subject}\n\t\t{re.sub(r'\<[^>]*\>', '', message.body.content)}")
            print(f"{clean_body(message.body.content)}")
            attachments = await self.app_client.users.by_user_id(recipient_id).mail_folders.\
                by_mail_folder_id('inbox').messages.by_message_id(message.id).attachments.get()
            save_attachment(attachments)
        return

    async def get_users(self):
        query_params = UsersRequestBuilder.UsersRequestBuilderGetQueryParameters(
            select = ['displayName', 'id', 'mail'],
            top = 25,
            orderby= ['displayName']
        )
        request_config = UsersRequestBuilder.UsersRequestBuilderGetRequestConfiguration(
            query_parameters=query_params
        )
        users = await self.app_client.users.get(request_configuration=request_config)
        return users
    # <SendMailSnippet>
    async def send_mail(self, subject: str, body: str, recipient: str):
        message = Message()
        message.subject = subject

        message.body = ItemBody()
        message.body.content_type = BodyType.Text
        message.body.content = body

        to_recipient = Recipient()
        to_recipient.email_address = EmailAddress()
        to_recipient.email_address.address = recipient
        message.to_recipients = []
        message.to_recipients.append(to_recipient)

        request_body = SendMailPostRequestBody()
        request_body.message = message

        await self.app_client.me.send_mail.post(body=request_body)
    # </SendMailSnippet>

    async def close(self):
        await self.client_credential.close()

