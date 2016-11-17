import httplib2
import csv
import sys
import logging

from apiclient import discovery, errors
from django.http import StreamingHttpResponse, HttpResponseRedirect, HttpResponse
from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.contrib.auth import logout as auth_logout
from django.contrib import messages as django_messages
from oauth2client.contrib.django_orm import Storage
from oauth2client.client import AccessTokenCredentials
from oauth2client.client import AccessTokenCredentialsError

from .forms import GmailFilter

# Get an instance of a logger
logger = logging.getLogger(__name__)


# Create your views here.
class Echo(object):
    """An object that implements just the write method of the file-like
    interface.
    """

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value


def _get_header(service, messages):
    def _message_metadata(request_id, response, exception):
        if exception is not None:
            logger.debug("Error when getting data 150/batch")
            # print("Error when getting data")
            pass
        else:
            if response.get('payload') is not None:
                headers = {d['name']: d['value'] for d in response.get('payload').get('headers')}
                # Use partition rather than split to improve performance
                if headers.get('From') is not None:
                    from_address = headers.get('From').partition('<')[-1].rpartition('>')[0] if '<' in headers.get(
                        'From') else headers.get('From')
                    date = headers.get('Date')
                    if headers.get('To') is not None:
                        to_list = [email.partition('<')[-1].rpartition('>')[0] if '<' in email else email for email in
                                   headers.get('To').split(', ')]
                        for to in to_list:
                            result.append([from_address, to, date])
                    if headers.get('CC') is not None:
                        cc_list = [email.partition('<')[-1].rpartition('>')[0] if '<' in email else email for email in
                                   headers.get('CC').split(', ')]
                        for cc in cc_list:
                            result.append([from_address, cc, date])
                    if headers.get('Bcc') is not None:
                        bcc_list = [email.partition('<')[-1].rpartition('>')[0] if '<' in email else email for email in
                                    headers.get('Bcc').split(', ')]
                        for bcc in bcc_list:
                            result.append([from_address, bcc, date])

    if len(messages) == 0:
        yield {}
    else:
        result = []
        # batch messages (100 requests per batch, google limit)
        batch = service.new_batch_http_request()
        # for message in messages:
        for count, message in enumerate(messages, 1):
            batch.add(service.users().messages().get(userId='me', id=message['id'], format='metadata',
                                                     metadataHeaders=['From', 'To', 'CC', 'Bcc', 'Date'],
                                                     fields='payload/headers'), callback=_message_metadata)
            if count % 100 == 0:
                batch.execute()
                for res in result:
                    yield res
                result = []
                batch = service.new_batch_http_request()
        batch.execute()
        for res in result:
            yield res


def home(request):
    context = {}
    template = 'home.html'
    return render(request, template, context)


def members(request):
    """

    :param request:
    :return:
    """

    if request.method == 'POST':
        form = GmailFilter(request.POST)
        if form.is_valid():
            # Create a credential using access_token
            # There maybe a better way to get credential
            if form.cleaned_data['all_messages'] is True:
                max_results = 1000000
            else:
                max_results = form.cleaned_data['max_results']
            from_date = form.cleaned_data['from_date']
            to_date = form.cleaned_data['to_date']
            labels = form.cleaned_data['labels']
            social = request.user.social_auth.get(provider='google-oauth2')
            credential = AccessTokenCredentials(social.extra_data['access_token'], 'my-user-agent/1.0')
            if credential is None or credential.invalid is True:
                return redirect('/')
            else:
                http = httplib2.Http()
                http = credential.authorize(http)
                service = discovery.build("gmail", "v1", http=http)
                try:
                    messages = []
                    results_remained = max_results
                    for label in labels:
                        if results_remained <= 0:
                            break
                        try:
                            response = service.users().messages().list(userId='me', maxResults=results_remained,
                                                                       labelIds=label, q='after:%s before:%s' % (
                                    from_date, to_date)).execute()
                        except AccessTokenCredentialsError as error:
                            django_messages.error(request,
                                                  "The access_token is expired or invalid and can\'t be refreshed. Please logout and login again!")
                        if 'messages' in response:
                            messages.extend(response.get('messages'))
                        results_remained -= len(response.get('messages'))
                        while 'nextPageToken' in response and results_remained > 0:
                            response = service.users().messages().list(userId='me', maxResults=results_remained,
                                                                       labelIds=label,
                                                                       pageToken=response.get('nextPageToken'),
                                                                       q='after:%s before:%s' % (
                                                                           from_date, to_date)).execute()
                            messages.extend(response.get('messages'))
                            results_remained -= len(response.get('messages'))
                except errors.HttpError as error:
                    django_messages.error(request,
                                          "An error occurred. Please login again!")
                    print('An error occurred: %s' % error)
                # GMAIL CHECK
                if not messages:
                    django_messages.error(request,
                                          "No Message found!")
                    print('No Message found.')
                else:
                    print(len(messages))
                    # # triditional way
                    # response = HttpResponse(content_type='text/csv')
                    # response['Content-Disposition'] = 'attachment; filename="gmail.csv"'
                    #
                    # writer = csv.writer(response)
                    # batch = service.new_batch_http_request()
                    # for message in messages:
                    #     # for count, message in enumerate(messages, 1):
                    #     # batch.add(service.users().messages().get(userId='me', id=message['id'], format='metadata', metadataHeaders=['From', 'To', 'CC', 'Bcc']))
                    #     batch.add(service.users().messages().get(userId='me', id=message['id'], format='metadata',
                    #                                              metadataHeaders=['From', 'To', 'CC', 'Bcc']),
                    #               callback=_message_metadata)
                    # batch.execute()
                    # return response

                    # Use generator to speedup

                    rows = _get_header(service, messages)
                    pseudo_buffer = Echo()
                    writer = csv.writer(pseudo_buffer)
                    # django_messages.success(request, "Start downloading")
                    response = StreamingHttpResponse((writer.writerow(row) for row in rows),
                                                     content_type="text/csv")
                    response['Content-Disposition'] = 'attachment; filename="gmail.csv"'
                    return response
        else:
            django_messages.error(request,
                                  "Form is not valid. Please correct the highlighted fields")
            print("Form not valid")
    else:
        # Get labels
        social = request.user.social_auth.get(provider='google-oauth2')
        credential = AccessTokenCredentials(social.extra_data['access_token'], 'my-user-agent/1.0')
        if credential is None or credential.invalid is True:
            return redirect('/')
        else:
            http = httplib2.Http()
            http = credential.authorize(http)
            service = discovery.build("gmail", "v1", http=http)
            labels = []
            try:
                response = service.users().labels().list(userId='me').execute()
                if 'labels' in response:
                    labels.extend(response.get('labels'))
            except (AccessTokenCredentialsError, errors.HttpError) as error:
                print('An error occurred: %s' % error)
                django_messages.error(request,
                                      "The access_token is expired or invalid and can\'t be refreshed. Please logout and login again!")
            # Labels check
            OPTIONS = []
            if len(labels) == 0:
                django_messages.error(request,
                                      "No Label found!")
            else:
                OPTIONS = [(label['id'], label['name']) for label in labels if "CATEGORY" in label['id']]

            form = GmailFilter()
            form.fields['labels'].choices = OPTIONS

    context = {
        'form': form,
    }
    template = 'members.html'
    return render(request, template, context)


def login_error(request):
    context = {"message": "You have logged in using another Gmail account. Please logout first!"}
    template = 'login_error.html'
    return render(request, template, context)


def logout(request):
    auth_logout(request)
    return HttpResponseRedirect(reverse('gmail:home'))
