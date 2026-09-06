def default_user_search(user_param='user', prefix=''):
    """Returns a list containing all the default ways we like to be able to search a user by.

    Pass prefix='^' to match the start of each text field instead of anywhere
    within it.  That is much cheaper to evaluate, so it's worth using on admins
    over very large tables (e.g., student registrations)."""
    return [f'{prefix}{user_param}__username', f'{prefix}{user_param}__first_name',
            f'{prefix}{user_param}__last_name', f'{prefix}{user_param}__email',
            f'={user_param}__id']
