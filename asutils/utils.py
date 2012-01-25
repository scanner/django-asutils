#
# File: $Id: utils.py 1803 2008-10-12 03:05:03Z scanner $
#
"""
some top level utilities useful for manyapps.
"""
# Python standard lib imports
#
import pytz
import time

# Django imports
#
from django.conf import settings
from django.template.defaultfilters import slugify as django_slugify
from django.template import RequestContext
from django.shortcuts import render_to_response

# Establish a tuple of timezones. Used for model fields that
# are meant to represent a choice of timezones.
#
TZ_CHOICES = tuple([(x,x) for x in pytz.all_timezones])

#############################################################################
#
def msg_user(user, message):
    """A helper function to send a 'message' to a user (using the message
    object framework for users from the django.contrib.auth
    module. This is NOT email. This is for basic messages like "you
    have successfully posted your message" etc.
    """
    if user.is_authenticated():
        user.message_set.create(message = message)
    return

#############################################################################
#
def slugify(value, length):
    """Take the given string and slugify it, making sure it does not exceed
    the specified length.
    """
    if len(value) > length:
        return django_slugify(value[:length/2] + value[-length/2:])
    else:
        return django_slugify(value)

from time import mktime

#############################################################################
#
# From http://www.djangosnippets.org/snippets/387/,
def datetime_to_ms_str(dt):
    """
    Converting datetime to Javascript milliseconds in epoch
    """
    return str(1000 * time.mktime(dt.timetuple()))

#############################################################################
#
def asrender_to_response(request, template_name, info_dict = { },
                         extra_context = None, **kwargs):
    """
    A helper function. For making generic views I kept finding myself
    repeating this pattern so I decided to simplify it to this.

    We take a template name, a context, and an extra_context. This is
    for the case where we have a somewhat generic view that is going
    to render a template with a context, however the caller of the
    view may have extra context information they want to add to it. We
    also want to always use a django RequestContext so that we get
    things like the session and user passed along.

    Arguments:
    - `request`: the django request object from the view.
    - `template_name`: name of django template to render.
    - `info_dict`: context to pass to the template renderer
    - `extra_context`: if specific, another dict of context variables to add
                       to the context. NOTE: These will be over-ridden
                       by the contents of `context`

                       NOTE: The values in the extra context can be
                       callables. If they are we put in the context
                       the return value of the callable.
    """
    if extra_context is None:
        extra_context = {}
    context = RequestContext(request)
    for key, value in extra_context.items():
        context[key] = callable(value) and value() or value
    return render_to_response(template_name,
                              info_dict,
                              context_instance=context, **kwargs)

#############################################################################
#
class MultiQuerySet(object):
    """
    From: http://www.djangosnippets.org/snippets/1103/

    This class acts as a wrapper around multiple querysets. Use it if
    you want to chain multiple QSs together without combining them
    with | or &. eg., to put title matches ahead of body matches:

    >>> qs1 = Event.objects.filter(## title matches ##)
    >>> qs2 = Event.objects.filter(## matches in other fields ##)
    >>> qs = MultiQuerySet(qs1, qs2)
    >>> len(qs)
    >>> paginator = Paginator(qs)
    >>> first_ten = qs[:10]

    It effectively acts as an immutable, sliceable QuerySet (with only
    a very limited subset of the QuerySet api)
    """
    def __init__(self, *args, **kwargs):
        self.querysets = args
        self._count = None

    def count(self):
        if not self._count:
            self._count = sum(len(qs) for qs in self.querysets)
        return self._count

    def __len__(self):
        return self.count()

    def __getitem__(self, item):
        indices = (offset, stop, step) = item.indices(self.count())
        items = []
        total_len = stop - offset
        for qs in self.querysets:
            if len(qs) < offset:
                offset -= len(qs)
            else:
                items += list(qs[offset:stop])
                if len(items) >= total_len:
                    return items
                else:
                    offset = 0
                    stop = total_len - len(items)
                    continue

