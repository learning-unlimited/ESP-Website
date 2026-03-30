def default_user_search(user_param='user'):
    """Returns a list containing all the default ways we like to be able to search a user by."""
    return [f'{user_param}__username', f'{user_param}__first_name', f'{user_param}__last_name', f'{user_param}__email', f'={user_param}__id']

def optimized_user_search_fields():
    """
    Optimized user search fields that reduce database JOINs.
    Focuses on the most commonly searched fields.
    """
    return ['username', 'email', 'first_name', 'last_name']

def get_optimized_user_search_q(search_term):
    """
    Returns an optimized Q object for user searches.
    """
    from django.db.models import Q
    
    if not search_term:
        return Q()
    
    # If search term is numeric, try ID search first
    if search_term.isdigit():
        return Q(id=int(search_term))
    
    # Otherwise search common fields
    search_q = Q()
    search_q |= Q(username__icontains=search_term)
    search_q |= Q(email__icontains=search_term)
    search_q |= Q(first_name__icontains=search_term)
    search_q |= Q(last_name__icontains=search_term)
    
    return search_q
