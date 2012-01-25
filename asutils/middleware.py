#
# File: $Id: middleware.py 1853 2008-10-24 00:13:25Z scanner $
#
"""
Bits of django middleware that we find useful in a number of projects.
"""

import urllib
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseRedirect

#############################################################################
#
class ActiveViewMiddleware(object):
    """
    Cribbed from http://www.djangosnippets.org/snippets/1153/
    """
    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Records the view function used on this request and its *args
        and **kwargs.  Needed by {% ifactive %} to determine if a
        particular view is currently active.
        """
        request._view_func = view_func
        request._view_args = list(view_args)
        request._view_kwargs = view_kwargs

#############################################################################
#
def allow_anonymous(view_func):
    """
    A helper function wrapper that will set the 'allow_anonymous'
    attribute on a view function, which is watched for the
    'RequireLogin' middleware to let you access the view without
    needing to be authenticated first.
    """
    view_func.allow_anonymous = True
    return view_func

#############################################################################
#
class RequireLogin(object):
    """
    When most pages in a site require authentication, decorating all the
    views with @login_required can be annoying. You can reverse the
    default behavior by creating a custom middleware class.

    This comes from: "Private by default" - by Nathan Ostgard
    http://nathanostgard.com/archives/2007/7/22/private-by-default/
    """
    ########################################################################
    #
    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.path != settings.LOGIN_URL and \
                request.path[0:15] != "/dojango/media/" and \
                not request.user.is_authenticated() and \
                not getattr(view_func, 'allow_anonymous', False):
            url = '%s?%s=%s' % (settings.LOGIN_URL, REDIRECT_FIELD_NAME,
                                urllib.quote(request.get_full_path()))
            return HttpResponseRedirect(url)

#############################################################################
#
class iPhoneMiddleware(object):
    """
    iPhone Middleware. Dynamically adds the iPhone template dirs if
    iPhone user agent is present

    based on: http://www.djangosnippets.org/snippets/1098/
    """
    ########################################################################
    #
    def __init__(self):
        """
        XXX We need to rework this more sensibly so that it is project generic.
        """
        self.iphone_templates = ()
        return

    ########################################################################
    #
    def process_request(self, request):
        if request.META['HTTP_USER_AGENT'].find('iPhone') != -1:
            request.iphone = True
            # Augment template_dirs
            #
            # settings.TEMPLATE_DIRS = self.iphone_templates + local_settings.TEMPLATE_DIRS
        else:
            request.iphone = False
            # settings.TEMPLATE_DIRS = local_settings.TEMPLATE_DIRS
        return
