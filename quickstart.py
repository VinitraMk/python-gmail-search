from __future__ import print_function

import os.path
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pushbullet import PushBullet
from pywebio.input import *
from pywebio.output import *
from pywebio.session import *
import time
import json

class Main:
    service = None

    def __init__(self):
    # If modifying these scopes, delete the file token.json.
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.labels',
                'https://www.googleapis.com/auth/gmail.modify']
        self.year_to_check = 2022
        self.month_to_check = 8
        self.timeformatA = '%a, %d %b %Y %H:%M:%S'
        self.timeformatB = '%d %b %Y %H:%M:%S'
        #allow_labels = ['CATEGORY_FORUMS','CATEGORY_UPDATES','CATEGORY_PERSONAL','SPAM']
        self.check_labels = ['UNREAD', 'SPAM']
        self.allow_labels = ['UNREAD']
        self.selected_unis_email_domains = ['illinois.edu','uic.edu','rutgers.edu','ucsd.edu','liasoncas.com','stonybrook.edu','wisc.edu','berkeley.edu','gmu.edu',
                'uci.edu','ucla.edu','umass.edu','tamu.edu','purdue.edu','colorado.edu',
                'uchicago.edu','nyu.edu','rochester.edu','buffalo.edu','neu.edu']
        with open('./pushbullet_creds.json') as fp:
            data = json.load(fp)
            self.access_token = data['ACCESS_TOKEN']

    def __get_message_id(self, message):
        return message['id']

    def __get_domain(self, sender):
        return sender.split('@')[1][0:-1]

    def __is_after_date(self, date_value):
        try:
            date_object = datetime.strptime(date_value[:24], self.timeformatA)
        except:
            date_object = datetime.strptime(date_value[:19], self.timeformatB)
        return date_object.year >= self.year_to_check and ((date_object.year == 2022 and date_object.month >= self.month_to_check) or (date_object.year > 2022 and date_object.month >= 1))

    def __is_sender_in_selected_unis(self, sender):
        #print('is email domain in sender', sender, any(x in sender for x in self.selected_unis_email_domains))
        if any(x in sender for x in self.selected_unis_email_domains):
            return True
        return False

    def __mail_mapper(header):
        if header['name'] == 'From' or header['name'] == 'Date':
            return header['value']
        return None

    def __get_messages(self, nextPageToken, labelId):
        if nextPageToken == None:
            results_messages = self.service.users().messages().list(userId='me', includeSpamTrash = True, labelIds=labelId, maxResults = 500).execute()
        else:
            results_messages = self.service.users().messages().list(userId='me', includeSpamTrash = True, labelIds=labelId, pageToken = nextPageToken,
                    maxResults = 500).execute()
        messages = results_messages.get('messages', [])
        messages = list(map(self.__get_message_id, messages))
        nextPageToken = results_messages.get('nextPageToken')
        return messages, nextPageToken

        
    def __get_mail(self, message_id):
        email = self.service.users().messages().get(userId='me', id=message_id).execute()
        this_year_email = False
        header_dict = { x['name']: x['value'] for x in email.get('payload')['headers'] }
        is_after_date = self.__is_after_date(header_dict['Date'])
        domain_name = self.__get_domain(header_dict['From'])
        if is_after_date and '.edu' in domain_name:
            if self.__is_sender_in_selected_unis(header_dict['From']):
                self.service.users().messages().modify(userId='me',
                        id=message_id, body={"addLabelIds": ['Label_6961090433011574317']}).execute()
            else:
                self.service.users().messages().modify(userId='me', id=message_id, body={"removeLabelIds":['Label_6961090433011574317']}).execute()
            return { 'Sender': header_dict['From'], 'Subject': header_dict['Subject'] }
        elif not(is_after_date):
            return 'date_passed'
        return None

    def __get_mails(self, messages):
        from_list = []
        date_passed = False
        for message_id in messages:
            email = self.__get_mail(message_id)
            if email != None and email != 'date_passed':
                from_list.append(email)
            elif email == 'date_passed':
                date_passed = True
                break
        return from_list, date_passed
    
    def __send_push_notification(self, all_msgs):
        selected_uni_senders = [x['Sender'] for x in all_msgs if self.__is_sender_in_selected_unis(x['Sender'])]
        other_unis = [x['Sender'] for x in all_msgs if x['Sender'] not in selected_uni_senders]
        title, message = '', ''
        if len(selected_uni_senders) > 0:
            title = f'IMPORTANT!\nYou have unread mails from some of your choice universities\n\n'
            message = f'You have unread mails from the following universities\n\n'
            for uni in selected_uni_senders:
                message = f'{message}\t\t{uni}\n\n'
            pb =  PushBullet(self.access_token)
            push = pb.push_note(title, message)
        if len(other_unis) > 0:
            title = 'You have mails from some other prospective universities'
            message = 'You have some new emails from prospective universities, please check your mail'
            pb =  PushBullet(self.access_token)
            push = pb.push_note(title, message)
        print('\nNotifications sent to mobile successfully :-D')

    def main(self):
        """Shows basic usage of the Gmail API.
        Lists the user's Gmail labels.
        """
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', self.SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        try:
            # Call the Gmail API
            self.service = build('gmail', 'v1', credentials=creds)
            '''
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            if not labels:
                print('No labels found.')
                return
            print('Labels:')
            for label in labels:
                print(label['name'], label)
            print()
            '''

            nextPageToken = None
            all_msgs = []
            for labelId in self.check_labels:
                i = 0
                print(f'Reading messages from {labelId}')
                while True:
                    print(f'\treading messages from page {i+1}')
                    messages, nextPageToken = self.__get_messages(nextPageToken, labelId)
                    from_list, date_passed = self.__get_mails(messages)
                    all_msgs = all_msgs + from_list
                    if nextPageToken == None or date_passed:
                        break
                    i = i + 1
            self.__send_push_notification(all_msgs)

        except HttpError as error:
            # TODO(developer) - Handle errors from gmail API.
            print(f'An error occurred: {error}')


if __name__ == '__main__':
    main = Main()
    main.main()
