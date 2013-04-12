from django.contrib.auth.models import User
from django.contrib.auth.models import Group as AuthGroup
from django.core.cache import cache
from django.conf import settings

def clear_cache_specialty(sender, instance, signal, *args, **kwargs):
    """
    When a specialty is added/changed, make sure that all top level cache entries
    are cleared for every user.  Top-level means when Department is selected.
    """
    DocGroup = AuthGroup.objects.get(name='Provider')
    doctors_list = [ u for u in User.objects.all() if DocGroup in u.groups.all() ]

    for user in doctors_list:
        cache_key = "%i,%i,0" % (settings.SITE_ID, int(user.id))
        cache.delete(cache_key)
        cache_key = "%i,%i,%i" % (settings.SITE_ID, int(user.id), int(instance.id))
        cache.delete(cache_key)

def clear_cache_group(sender, instance, signal, *args, **kwargs):
    """
    When a group is added/changed make sure that all top-level and specialty-level
    cache entries are cleared for every user.  Top-level means when Department is
    selected, and specialty-level means whenever the specialty the group belongs to
    is selected.
    """
    DocGroup = AuthGroup.objects.get(name='Provider')
    doctors_list = [ u for u in User.objects.all() if DocGroup in u.groups.all() ]

    for user in doctors_list:
        cache_key = "%i,%i,0" % (settings.SITE_ID, int(user.id))
        cache.delete(cache_key)
        cache_key = "%i,%i,%i" % (settings.SITE_ID, int(user.id), int(instance.specialty.id))
        cache.delete(cache_key)

def clear_cache_specialist(sender, instance, signal, *args, **kwargs):
    """
    When a specialist is added/changed make sure that all top-level and specialty-level
    cache entries are cleared for every user.  Top-level means when Department is
    selected, and specialty-level means whenever the specialty the specialist belongs to
    is selected.
    """
    DocGroup = AuthGroup.objects.get(name='Provider')
    doctors_list = [ u for u in User.objects.all() if DocGroup in u.groups.all() ]

    for user in doctors_list:
        cache_key = "%i,%i,0" % (settings.SITE_ID, int(user.id))
        cache.delete(cache_key)
        cache_key = "%i,%i,%i" % (settings.SITE_ID, int(user.id), int(instance.group.specialty.id))
        cache.delete(cache_key)
