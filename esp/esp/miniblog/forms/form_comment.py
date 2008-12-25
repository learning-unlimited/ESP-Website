
from django import forms


class BlogCommentForm(forms.Form):

    subject = forms.CharField(max_length= 256)

    content = forms.CharField(label="Body",
                              help_text="HTML is not allowed.",
                              widget=forms.Textarea(attrs={'rows':15,
                                                          'cols':70}))
