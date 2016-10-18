import httplib2
import csv
from io import StringIO

from apiclient import discovery, errors
from django.http import StreamingHttpResponse, HttpResponseRedirect, HttpResponse
from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from django.contrib.auth import logout as auth_logout
from oauth2client.contrib.django_orm import Storage
from oauth2client.client import AccessTokenCredentials

from .forms import GmailFilter


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
            pass
        else:
            if response.get('payload') is not None:
                headers = {d['name']: d['value'] for d in response.get('payload').get('headers')}
                # Use partition rather than split to improve performance
                if headers.get('From') is not None:
                    from_address = headers.get('From').partition('<')[-1].rpartition('>')[0] if '<' in headers.get('From') else headers.get('From')
                    if headers.get('To') is not None:
                        to_list = [email.partition('<')[-1].rpartition('>')[0] if '<' in email else email for email in headers.get('To').split(', ')]
                        for to in to_list:
                            result.append([from_address, to])
                    if headers.get('CC') is not None:
                        cc_list = [email.partition('<')[-1].rpartition('>')[0] if '<' in email else email for email in headers.get('CC').split(', ')]
                        for cc in cc_list:
                            result.append([from_address, cc])
                    if headers.get('Bcc') is not None:
                        bcc_list = [email.partition('<')[-1].rpartition('>')[0] if '<' in email else email for email in headers.get('Bcc').split(', ')]
                        for bcc in bcc_list:
                            result.append([from_address, bcc])

    if len(messages) == 0:
        yield {}
    else:
        result = []
        # batch messages (100 requests per batch, google limit)
        batch = service.new_batch_http_request()
        # for message in messages:
        for count, message in enumerate(messages, 1):
            batch.add(service.users().messages().get(userId='me', id=message['id'], format='metadata',
                                                     metadataHeaders=['From', 'To', 'CC', 'Bcc'],
                                                     fields='payload/headers'), callback=_message_metadata)
            if count % 250 == 0:
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

    def _message_metadata(request_id, response, exception):
        if exception is not None:
            pass
        else:
            if response.get('payload') is not None:
                headers = {d['name']: d['value'] for d in response.get('payload').get('headers')}
                if headers.get('To') is not None:
                    for to in headers.get('To').split(', '):
                        writer.writerow([headers.get('From').split(' <')[0], to.split(' <')[0]])
                        # yield [headers.get('Date'), headers.get('From').split(' <')[0], to.split(' <')[0]]
                if headers.get('CC') is not None:
                    for cc in headers.get('CC').split(', '):
                        writer.writerow([headers.get('From').split(' <')[0], cc.split(' <')[0]])
                        # yield [headers.get('Date'), headers.get('From').split(' <')[0], cc.split(' <')[0]]
                if headers.get('Bcc') is not None:
                    for bcc in headers.get('Bcc').split(', '):
                        writer.writerow([headers.get('From').split(' <')[0], bcc.split(' <')[0]])
                        # yield [headers.get('Date'), headers.get('From').split(' <')[0], bcc.split(' <')[0]]

    if request.method == 'POST':
        form = GmailFilter(request.POST)
        if form.is_valid():
            # Create a credential using access_token
            # There maybe a better way to get credential
            max_results = form.cleaned_data['max_results']
            from_date = form.cleaned_data['from_date']
            to_date = form.cleaned_data['to_date']
            social = request.user.social_auth.get(provider='google-oauth2')
            credential = AccessTokenCredentials(social.extra_data['access_token'], 'my-user-agent/1.0')
            if credential is None or credential.invalid is True:
                return redirect('/')
            else:
                http = httplib2.Http()
                http = credential.authorize(http)
                service = discovery.build("gmail", "v1", http=http)
                try:
                    response = service.users().messages().list(userId='me', maxResults=max_results).execute()
                    messages = []
                    if 'messages' in response:
                        messages.extend(response.get('messages'))
                    results_remained = max_results - len(messages)
                    while 'nextPageToken' in response and results_remained > 0:
                        response = service.users().messages().list(userId='me', maxResults=results_remained,
                                                                   pageToken=response.get('nextPageToken'),
                                                                   q='after:%s before:%s' % (
                                                                   from_date, to_date)).execute()
                        messages.extend(response.get('messages'))
                        results_remained = max_results - len(messages)
                except errors.HttpError as error:
                    print('An error occurred: %s' % error)
                # GMAIL CHECK
                if not messages:
                    print('No Messages found.')
                else:
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

                    # use generator to speedup
                    rows = _get_header(service, messages)
                    pseudo_buffer = Echo()
                    writer = csv.writer(pseudo_buffer)
                    response = StreamingHttpResponse((writer.writerow(row) for row in rows),
                                                     content_type="text/csv")
                    response['Content-Disposition'] = 'attachment; filename="gmail.csv"'
                    return response
    else:
        form = GmailFilter()

    context = {
        'form': form,
    }
    template = 'members.html'
    return render(request, template, context)


def logout(request):
    auth_logout(request)
    return HttpResponseRedirect(reverse('gmail:home'))
