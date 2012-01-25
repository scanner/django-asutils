#
# File: $Id: views.py 1864 2008-10-27 22:11:00Z scanner $
#

# Python imports.
#
import os.path

# Django imports
#
from django.views.generic.simple import direct_to_template
from django.utils import simplejson
from django.http import HttpResponse, Http404
from django.utils.functional import Promise
from django.utils.translation import force_unicode
from django.utils.simplejson import JSONEncoder
from django.conf import settings

from asutils.middleware import allow_anonymous

####################################################################
#
def noauth_dtt(request, template, extra_context=None, mimetype=None, **kwargs):
    """
    This is a wrapper around django's 'direct_to_template' with the exception
    that we have tagged it with our 'allow_anonymous' function.

    This allows us to render templates directly to the caller without our
    asutils.middleware.RequireLogin middleware to redirect them to need a login
    if they are not authenticated.
    """
    return direct_to_template(request, template, extra_context=None,
                              mimetype=None, **kwargs)
allow_anonymous(noauth_dtt)

####################################################################
#
def direct_to_template_subdir(request, template, subdir = None, **kwargs):
    """
    A wrapper around django's direct_to_template view. It prepend a
    given file path on to the template we are given. This lets us
    render templates in a sub-dir of the url pattern that matches this
    template.

    What do I mean?

    Take for example:

        url(r'^foo/(?P<template>.*\.html)$', direct_to_template,
            {'subdir' : 'subdir/'}),

    Which will template any url that matches <parent url>/foo/bar.html for any
    'bar'. The problem is if this is a sub-url pattern match this is going to
    look for the template "bar.html" when we may actually want it to get the
    template "<parent url>/foo/bar.html"

    Arguments:
    - `request`: django httprequest object...
    - `template`: The template to render.
    - `subdir`: The subdir to prepend to the template.
    - `**kwargs`: kwargs to pass in to
    """

    if subdir is not None:
        # XXX Hm. I guess this would not work on windows because
        #     os.path would active differently.
        template = os.path.join(subdir,template)
    return direct_to_template(request, template, **kwargs)

####################################################################
#
def noauth_dtt_sd(request, template, subdir = None, **kwargs):
    """
    This is a thin wrapper around 'direct_to_template_subdir' defined
    above. The purpose is that we can tag this view with our 'allow_anonymous'
    function that will let us serve static pages without requiring the remote
    user to be authenticated.

    Arguments:
    - `request`: django httprequest object...
    - `template`: The template to render.
    - `subdir`: The subdir to prepend to the template.
    - `**kwargs`: kwargs to pass in to
    """
    return direct_to_template_subdir(request, template, subdir,
                                     **kwargs)
allow_anonymous(noauth_dtt_sd)

####################################################################
#
# NOTE: This was cribbed directly from:
# http://www.djangosnippets.org/snippets/1157/
#
class LazyEncoder(simplejson.JSONEncoder):
    def default(self, o):
        if isinstance(o, Promise):
            return force_unicode(o)
        else:
            return super(LazyEncoder, self).default(o)

class JSONResponse(HttpResponse):
    def __init__(self, data):
        HttpResponse.__init__(
            self, content=simplejson.dumps(data, cls=LazyEncoder),
            #mimetype="text/html",
        )
def ajax_form_handler(
    request, form_cls, require_login=True, allow_get=settings.DEBUG
):
    """
    Some ajax heavy apps require a lot of views that are merely a
    wrapper around the form. This generic view can be used for them.

    NOTE: This was cribbed directly from:

    http://www.djangosnippets.org/snippets/1157/
    """
    if require_login and not request.user.is_authenticated():
        raise Http404("login required")
    if not allow_get and request.method != "POST":
        raise Http404("only post allowed")
    if isinstance(form_cls, basestring):
        # can take form_cls of the form: "project.app.forms.FormName"
        from django.core.urlresolvers import get_mod_func
        mod_name, form_name = get_mod_func(form_cls)
        form_cls = getattr(__import__(mod_name, {}, {}, ['']), form_name)
    form = form_cls(request, request.REQUEST)
    if form.is_valid():
        return JSONResponse({ 'success': True, 'response': form.save() })
    return JSONResponse({ 'success': False, 'errors': form.errors })
