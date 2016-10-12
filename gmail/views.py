import httplib2
import csv

from apiclient import discovery
from django.http import StreamingHttpResponse, HttpResponseRedirect
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
    if len(messages) == 0:
        yield ''
    else:
        for message in messages:
            results = service.users().messages().get(userId='me', id=message['id']).execute()
            headers = {d['name']: d['value'] for d in results.get('payload').get('headers')}
            yield [headers['Subject'], headers['Date'], headers['From'], headers['To']]

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
            max_results = form.cleaned_data['max_results']
            social = request.user.social_auth.get(provider='google-oauth2')
            credential = AccessTokenCredentials(social.extra_data['access_token'], 'my-user-agent/1.0')
            if credential is None or credential.invalid is True:
                return redirect('/')
            else:
                http = httplib2.Http()
                http = credential.authorize(http)
                service = discovery.build("gmail", "v1", http=http)
                results = service.users().messages().list(userId='me', maxResults=max_results).execute()
                messages = results.get('messages', [])

                # GMAIL CHECK
                if not messages:
                    print('No Messages found.')
                else:
                    '''# triditional way
                    response = HttpResponse(content_type='text/csv')
                    response['Content-Disposition'] = 'attachment; filename="gmail.csv"'

                    writer = csv.writer(response)
                    for message in messages:
                        results = service.users().messages().get(userId='me', id=message['id']).execute()
                        # convert list of dict to dict
                        headers = {d['name']: d['value'] for d in results.get('payload').get('headers')}
                        writer.writerow([headers['Subject'], headers['Date'], headers['From'], headers['To']])
                    return response'''

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