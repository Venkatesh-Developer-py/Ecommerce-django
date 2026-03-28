from django.views.decorators.cache import never_cache
from django.utils.decorators import method_decorator

def no_cache(view_func):
    """
    Completely disables browser caching & history
    """
    return never_cache(view_func)
