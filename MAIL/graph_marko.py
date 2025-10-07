# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

# <UserAuthConfigSnippet>
import base64
from configparser import SectionProxy
from azure.identity.aio import ClientSecretCredential
from msgraph import GraphServiceClient
from kiota_abstractions.request_information import RequestInformation
from kiota_abstractions.method import Method
from msgraph.generated.models.o_data_errors.o_data_error import ODataError

from msgraph.generated.users.item.mail_folders.item.messages.delta.delta_get_response import DeltaGetResponse
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

# from email_reply_parser import EmailReplyParser
from bs4 import BeautifulSoup
import os
import json
import re 
import requests

DOWNLOAD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ATTS_DOWNLOAD')

def file_valid(attachment):
    # return attachment.additional_data.get("@odata.type") == "#microsoft.graph.fileAttachment" and \
    # (attachment.name.endswith("pdf") or attachment.name.endswith("xlsx"))
    return attachment.odata_type == "#microsoft.graph.fileAttachment" and \
    attachment.name.endswith("pdf") or attachment.name.endswith("xlsx")

def save_attachment(attachments):
    for a in attachments.value:
        if a.content_bytes and file_valid(a):
            file_bytes = base64.b64decode(a.content_bytes)
            with open(f"ATTS_DOWNLOAD/{a.name}", "wb") as f:
                f.write(file_bytes)
                f.close()
            print(f"Saved: {a.name}")

def clean_body(body: str) -> str:
    soup = BeautifulSoup(body, "html.parser")

    # 1. Remove inline images (signatures, tracking pixels, etc.)
    for img in soup.find_all("img"):
        img.decompose()

    # 2. Remove signature/footer blocks if marked by class
    for sig in soup.find_all(attrs={"class": re.compile(r"signature|footer", re.I)}):
        sig.decompose()

    # 3. Find the first Outlook message header block
    outlook_headers = soup.find_all("div", class_=re.compile(r"OutlookMessageHeader", re.I))
    if outlook_headers:
        # Chop the document at the first Outlook header
        outlook_headers[0].decompose()

    # 4. Now extract the top part as plain text
    text = soup.get_text(separator=" ", strip=True)

    text = re.sub('From:.*?Subject: ', '', text, flags=re.DOTALL)
    return text


class Mail:
    def __init__(self, message):
        self.body = clean_body(message.body.content)
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

    async def get_app_only_token(self):
        graph_scope = 'https://graph.microsoft.com/.default'
        access_token = await self.client_credential.get_token(graph_scope)
        return access_token.token

    async def get_mails(self, recipient_id, delta_url=None):
        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            select = ['sender', 'subject', 'hasAttachments', 'body'],
            # top = 5,
            # orderby=['receivedDateTime DESC']
        )
        request_configuration = RequestConfiguration(
            query_parameters=query_params
        )
        # request_configuration.headers.add("Prefer", f"outlook.body-content-type=\"text\"")
        if delta_url:
            request_info = RequestInformation()
            request_info.url_template = delta_url
            request_info.http_method = Method.GET
            error_map = {
                "4XX": ODataError,
                "5XX": ODataError
            }
            # token = await self.get_app_only_token()
            # headers = {"Authorization:" f"Bearer {token}"}
            # return requests.get(delta_url, headers=headers)
            return await self.app_client.request_adapter.send_async(request_info, DeltaGetResponse, error_map)
        messages = await self.app_client.users.by_user_id(recipient_id).mail_folders.\
        by_mail_folder_id('inbox').messages.delta.get(
            request_configuration
        )
        return messages

    async def download_attachments(self, messages, recipient_id): 
        # print(f"DELTA: {messages.odata_delta_link}")

        for message in messages.value:
            print(f"SUBJECT: {message.subject}")
            # print(f"SUBJECT: {message.subject}\n\t\t{re.sub(r'\<[^>]*\>', '', message.body.content)}")
            # print(f"{clean_body(message.body.content)}")
            cleaned_body = clean_body(message.body.content)
            # print(f"{cleaned_body=}\n")
            attachments = await self.app_client.users.by_user_id(recipient_id).mail_folders.\
                by_mail_folder_id('inbox').messages.by_message_id(message.id).attachments.get()
            save_attachment(attachments)
        return

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

