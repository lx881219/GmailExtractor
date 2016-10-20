import datetime

from django import forms


class GmailFilter(forms.Form):
    max_results = forms.IntegerField(label='Max Results', max_value=32767, initial=100)
    from_date = forms.DateField(label='From Date', widget=forms.SelectDateWidget(years=range(datetime.date.today().year-10, datetime.date.today().year)))
    to_date = forms.DateField(label='To Date', widget=forms.SelectDateWidget(), initial=datetime.date.today())