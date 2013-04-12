from django import template

register = template.Library()

@register.filter(name="zip")
def zip_lists(list1, list2):
    return zip(list1, list2)
zip_lists.is_safe = False

@register.filter(name="in")
def obj_in_list(list, obj):
    return obj in list
obj_in_list.is_safe = False
