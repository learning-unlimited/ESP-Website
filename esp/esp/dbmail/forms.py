from django import forms
from esp.dbmail.models import InboundEmailThread


class InboxReplyForm(forms.Form):
    """Form for replying to an inbound email thread from the inbox UI."""
    body = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 8,
            'class': 'inbox-reply-textarea',
            'placeholder': 'Type your reply...',
        }),
        label='Reply',
    )


class InboxFilterForm(forms.Form):
    """Form for filtering the inbox list view."""
    STATUS_CHOICES = [('', 'All')] + list(InboundEmailThread.STATUS_CHOICES)

    q = forms.CharField(
        required=False,
        label='Search',
        widget=forms.TextInput(attrs={
            'placeholder': 'Search by subject or sender...',
            'class': 'inbox-search-input',
        }),
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        label='Status',
    )
    date_from = forms.DateField(
        required=False,
        label='From',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    date_to = forms.DateField(
        required=False,
        label='To',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    mine_only = forms.BooleanField(
        required=False,
        label='My assignments only',
    )
