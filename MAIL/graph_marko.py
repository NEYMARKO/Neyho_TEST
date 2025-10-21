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
from kiota_abstractions.base_request_configuration import RequestConfiguration

from bs4 import BeautifulSoup
import os
import re 

DOWNLOAD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ATTS_DOWNLOAD')

def file_valid(attachment):
    # return attachment.additional_data.get("@odata.type") == "#microsoft.graph.fileAttachment" and \
    # (attachment.name.endswith("pdf") or attachment.name.endswith("xlsx"))
    # print(f"ATTACHMENT: {attachment}\n")
    return attachment.odata_type == "#microsoft.graph.fileAttachment" and\
    not attachment.is_inline
    # attachment.name.endswith("pdf") or attachment.name.endswith("xlsx")

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
    
    for link in soup.find_all("a"):
        link.decompose()
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

    text = re.sub(r'From:.*(?=\bSubject:)', '', text, flags=re.DOTALL)
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
        
        # Get the folder ID for "TEXT"
        # folders = await self.app_client.users.by_user_id(recipient_id).mail_folders.get()

        # folder_id = None
        # for folder in folders.value:
        #     # print(f"folder name: {folder.display_name}")
        #     if folder.display_name.lower() == "exception":
        #         folder_id = folder.id
        #         break

        # if not folder_id:
        #     raise ValueError("Folder 'TEXT' not found for this user.")

        query_params = MessagesRequestBuilder.MessagesRequestBuilderGetQueryParameters(
            select = ['sender', 'subject', 'hasAttachments', 'body'],
            # top = 2,
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
        # messages = await self.app_client.users.by_user_id(recipient_id).mail_folders.\
        # by_mail_folder_id(folder_id).messages.delta.get(
        #     request_configuration
        # )
        return messages

    async def download_attachments(self, messages, recipient_id) -> dict: 
        # print(f"DELTA: {messages.odata_delta_link}")
        # print(f"{messages=}")
        data = []
        if not messages:
            return {}
        for message in messages:
            obj = {}
            #these checks exist to avoid error when deleting messages on which
            #delta_link was formed (probably also avoiding errors when deleting any message)
            if "@removed" in (message.additional_data or {}):
                print(f"Message with id: {message.id} was deleted")
                continue
            if not getattr(message, "subject", None):
                print(f"Message with id: {message.id} has no subject; skipping.")
                continue
            obj['Subject'] = message.subject
            print(f"SUBJECT: {message.subject}\n")
            # print(f"SUBJECT: {message.subject}\n\t\t{re.sub(r'\<[^>]*\>', '', message.body.content)}")
            # print(f"{clean_body(message.body.content)}")
            cleaned_body = clean_body(message.body.content)
            obj['Body'] = cleaned_body
            print(f"{cleaned_body=}\n")
            # print(f"{cleaned_body=}\n")
            attachments = await self.app_client.users.by_user_id(recipient_id).mail_folders.\
                by_mail_folder_id('inbox').messages.by_message_id(message.id).attachments.get()
            save_attachment(attachments)
            obj['Attachments'] = [os.path.join(DOWNLOAD_PATH, attachment.name) for attachment in attachments.value]
            data.append(obj)
        return data

    async def close(self):
        await self.client_credential.close()
