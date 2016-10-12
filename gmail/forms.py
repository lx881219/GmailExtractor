from django import forms


class GmailFilter(forms.Form):
    max_results = forms.IntegerField(label='Max Results', max_value=32767, initial=100,
                                     help_text="Select how many messages you want to get")
