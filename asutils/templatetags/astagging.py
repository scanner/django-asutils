#
# File: $Id: astagging.py 1551 2008-07-24 22:16:34Z scanner $
#
"""
some templating utilities for use in how I use the django-tagging application.
"""

# Django imports
#
import django.utils.dateformat
from django import template

#
# This is a template library
#
register = template.Library()

#############################################################################
#
@register.inclusion_tag("astagging/tags_for_object.html")
def tags_for_object(object, tag_field):
    """
    This defines a django inclusion tag called 'tags_for_object' which
    creates a html fragment that will list the tags for the given
    object. Each tag will have a link allowing it to be deleted.

    There will also be a text entry field for adding a new tag to this object.

    The key thing is that the removing and adding of tags is done
    inline via some AJAX calls.

    This code basically assumes a certain level of ajax functionality
    and it is currently not very forgiving if it is missing.

    This code assumes that the object has a method named 'del_tag_url'
    that returns a url that will delete a tag passed as the argument
    'tag' vis POST, and a method named 'add_tag_url' that will add a
    tag named via the argument 'tag' also as a POST.

    The argument 'tag_field' passed to this function is the name of
    the field on the object passed to this function that holds the
    tags for this object you wish to have listed.

    An example would be:

       {% tags_for_object foo 'tags' %}

    where 'foo' is the object in the template context, and foo.tags is
    the field that holds the tags.

    foo has the method 'add_tag_url()' and 'del_tag_url()' that return
    absolute url's to views that will add and remove a tag from
    foo. The tag to be added or removed is past as the 'tag' field of
    a form as a string via POST to those url's.
    """

    return {
        'object' : object,
        'tags'   : getattr(object, tag_field)
        }
