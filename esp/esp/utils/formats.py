from django.utils.functional import lazy

def format_lazy(string, substitution):
    '''
    Returns a Django __proxy__ object that does a lazy evaluation of
    string % substitution.
    '''
    return lazy(lambda sub: string.__mod__(sub), type(string))(substitution)

