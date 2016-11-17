import datetime, sys

from django import forms


class GmailFilter(forms.Form):

    OPTIONS = [
        ("CATEGORY_PERSONAL", "CATEGORY_PERSONAL"),
        ("CATEGORY_SOCIAL", "CATEGORY_SOCIAL"),
        ("CATEGORY_PROMOTIONS", "CATEGORY_PROMOTIONS"),
        ("CATEGORY_UPDATES", "CATEGORY_UPDATES"),
        ("CATEGORY_FORUMS", "CATEGORY_FORUMS")
    ]

    max_results = forms.IntegerField(label='Max Results', max_value=sys.maxsize, initial=100, required=False)
    all_messages = forms.BooleanField(label='All messages', initial=False, required=False,
                                      help_text="Maximum number of messages to return. Limit: 1,000,000 messages")
    labels = forms.MultipleChoiceField(label='Categories', choices=OPTIONS, widget=forms.CheckboxSelectMultiple,
                                       initial=["CATEGORY_PERSONAL", "CATEGORY_FORUMS"],
                                       help_text='Return messages in selected category. Messages in your inbox are automatically sorted into categories by Gmail, like Primary, Social, Promotions, Updates, and Forums. All archived messages are also included. <a target="_blank" href="https://support.google.com/mail/answer/3094499?co=GENIE.Platform%3DDesktop&hl=en">More about Categories?</a>')
    from_date = forms.DateField(label='From Date', widget=forms.SelectDateWidget(
        years=range(datetime.date.today().year - 10, datetime.date.today().year)),)
    to_date = forms.DateField(label='To Date', widget=forms.SelectDateWidget(), initial=datetime.date.today(),
                              help_text="Return Messages between selected dates.")
