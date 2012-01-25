#
# File: $Id: decorators.py 1677 2008-10-03 00:38:31Z scanner $
#
"""
Some utility decorators.
"""
import base64

from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth import authenticate, login

############################################################################
#
def wrapped(wrapfunc):
    """
    This is a decorator utility function. Decorators frequently need to
    provide an inner wrapped function which is returned as the result of the
    decoration of a function. This makes writing our own decorators a bit
    simpler in that this will do the wrapping for us so we do not need to
    define a function inside our decorator functions.

    How do you use this? Decorate your decorator functions with this function.
    """
    def outerwrapper(func):
        def innerwrapper(*args, **kwargs):
            wrapfunc(func, args, kwargs)
            return func(*args, **kwargs)
        return innerwrapper
    return outerwrapper

#############################################################################
#
def view_or_basicauth(view, request, test_func, *args, **kwargs):
    """
    This is a helper function used by both 'logged_in_or_basicauth' and
    'has_perm_or_basicauth' that does the nitty of determining if they
    are already logged in or if they have provided proper http-authorization
    and returning the view if all goes well, otherwise responding with a 401.

    NOTE: The realm to use is expected to be defined in
    settings.HTTP_AUTHENTICATION_REALM
    """

    # The realm to use is defined in our settings.
    #
    realm = settings.HTTP_AUTHENTICATION_REALM

    if test_func(request.user):
        # Already logged in, just return the view.
        #
        print "Args is: %s" % str(args)
        print "kwargs is: %s" % str(kwargs)
        print "realm: %s" % str(realm)
        return view(request, *args, **kwargs)

    # They are not logged in. See if they provided login credentials
    #
    if 'HTTP_AUTHORIZATION' in request.META:
        auth = request.META['HTTP_AUTHORIZATION'].split()
        if len(auth) == 2:
            # NOTE: We are only support basic authentication for now.
            #
            if auth[0].lower() == "basic":
                uname, passwd = base64.b64decode(auth[1]).split(':')
                user = authenticate(username=uname, password=passwd)
                if user is not None:
                    if user.is_active:
                        login(request, user)
                        request.user = user
                        return view(request, *args, **kwargs)

    # Either they did not provide an authorization header or
    # something in the authorization attempt failed. Send a 401
    # back to them to ask them to authenticate.
    #
    response = HttpResponse()
    response.status_code = 401
    response['WWW-Authenticate'] = 'Basic realm="%s"' % realm
    return response

#############################################################################
#
def logged_in_or_basicauth():
    """
    A simple decorator that requires a user to be logged in. If they are not
    logged in the request is examined for a 'authorization' header.

    If the header is present it is tested for basic authentication and
    the user is logged in with the provided credentials.

    If the header is not present a http 401 is sent back to the
    requestor to provide credentials.

    The purpose of this is that in several django projects I have needed
    several specific views that need to support basic authentication, yet the
    web site as a whole used django's provided authentication.

    The uses for this are for urls that are access programmatically such as
    by rss feed readers, yet the view requires a user to be logged in. Many rss
    readers support supplying the authentication credentials via http basic
    auth (and they do NOT support a redirect to a form where they post a
    username/password.)

    NOTE: The realm is expected to be defined in
          settings.HTTP_AUTHENTICATION_REALM

    Use is simple:

    @logged_in_or_basicauth
    def your_view:
        ...

    """
    def view_decorator(func):
        def wrapper(request, *args, **kwargs):
            return view_or_basicauth(func, request,
                                     lambda u: u.is_authenticated(),
                                     *args, **kwargs)
        return wrapper
    return view_decorator

#############################################################################
#
def has_perm_or_basicauth(perm):
    """
    This is similar to the above decorator 'logged_in_or_basicauth'
    except that it requires the logged in user to have a specific
    permission.

    NOTE: The realm is expected to be defined in
          settings.HTTP_AUTHENTICATION_REALM

    Use:

    @logged_in_or_basicauth('asforums.view_forumcollection')
    def your_view:
        ...

    """

    def view_decorator(func):
        def wrapper(request, *args, **kwargs):
            return view_or_basicauth(func, request,
                                     lambda u: u.has_perm(perm),
                                     *args, **kwargs)
        return wrapper
    return view_decorator

