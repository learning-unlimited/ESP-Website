from django.dispatch import Signal

formstack_post_signal = Signal(providing_args=['form_id', 'submission_id', 'fields'])
