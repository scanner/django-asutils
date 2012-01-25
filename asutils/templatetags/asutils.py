#
# File: $Id: asutils.py 1895 2008-11-03 05:03:47Z scanner $
#
"""
This module contains a bunch of django templatetag definitions of
various sorts that are fairly generic across a wide range of apps,
hence they are part of the asutils app.
"""

# System imports.
#
import os.path
import math
import pytz
from datetime import datetime
from types import MethodType

# Django imports
#
import django.utils.dateformat
from django import template
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.template import Library, Node, resolve_variable, TemplateSyntaxError, Variable
from django.utils.encoding import smart_str
from django.core.urlresolvers import get_callable, RegexURLResolver, get_resolver
from django.utils.tzinfo import LocalTimezone
from django.utils.timesince import timesince, timeuntil



# Django contrib model imports
#
from django.contrib.auth.models import User

try:
    import notification
except ImportError:
    notification = None

#
# This is a template library
#
register = template.Library()

#############################################################################
#
class MonikerNode(template.Node):
    """
    implement the class that will either stick a 'moniker' in a context
    variable or return it as a string. See the 'do_moniker' function
    for the full description.
    """
    def __init__(self, objects, var_name = None):
        self.objects = objects
        self.var_name = var_name

    def render(self, context):
        """
        The worker horse. Basically we are going to construct a string
        that is the class names and id's of all of the objects
        concatenated with '-'

        The goal is to build a string that can be used as an 'id'
        attribute in a html tag so that we have a programmatic and
        repeatable way of generating id strings for sets of objects.

        If self.var_name is None then we render the moniker by
        returning the string.

        If self.var_name is not None then we return the empty string
        and set a variable named by self.var_name in the context with
        the results of our moniker.
        """
        moniker = []
        for obj_name in self.objects:
            try:
                obj = context[obj_name]
                moniker.append(obj.__class__.__name__)
                moniker.append(str(obj.id))
            except KeyError:
                pass

        result = '-'.join(moniker)
        if self.var_name:
            context[self.var_name] = result
            return ''
        return result

#############################################################################
#
@register.tag
def moniker(parser, token):
    '''
    Implement the parser for the {% moniker ... %} tag.

    This template tag is given a series of objects. It either returns
    a string which is the class/ids of these objects or sets a
    variable in the context which is the class/ids of these objects.

    The primary use is for compactly generating strings suitable for
    use as "id" attributes in html tags.

    For example:

      <span id="{% moniker foo %}">

    would turn in to:

      <span id="Video5">

    if foo was of class "Video".

    You can also do:

      {% moniker foo bar biz bat %}

    which would return:

      Video5-Series1-User10

    if foo was video id 5, bar was Series id 1, and bat was a User with id 10.

    If the second to last argument is the string "as" then the final
    argument is the name of a variable in the template context to
    insert the string in to instead of rendering it inline. Handy if
    you are going to refer to the same moniker several times.
    '''

    try:
        args = token.contents.split(None)
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires arguments" % \
              token.contents.split()[0]

    # Pop off the first argument which is the name of our templatetag.
    #
    args.pop(0)
    variable_name = None

    # If the next to last argument is 'as' then the last argument is a
    # variable name to use. We pop these off.
    if args[-2].lower() == "as":
        variable_name = args.pop()
        args.pop() # get rid of the 'as' too.

    # The rest of these args are the names of objects in the context.
    #
    return MonikerNode(args, variable_name)

#############################################################################
#
# This code was gotten from: http://www.djangosnippets.org/snippets/308/
#
@register.inclusion_tag("asutils/table_header.html", takes_context=True)
def table_header(context, headers):

    # We pass in the rest of the GET query parameters through so that
    # changing the sort order does not lose other GET parameters, however
    # we need to pull out of the query string we generate the GET parameters
    # that are set by the SortHeaders class.
    #
    ORDER_VAR = 'o'
    ORDER_TYPE_VAR = 'ot'

    get = context['request'].GET.copy()
    if ORDER_VAR in get:
        del get[ORDER_VAR]
    if ORDER_TYPE_VAR in get:
        del get[ORDER_TYPE_VAR]

    return { 'headers': headers,
             'query'  : get.urlencode(), }

#############################################################################
#
# This code was gotten from: http://code.djangoproject.com/wiki/PaginatorTag
#
@register.inclusion_tag("asutils/paginator.html", takes_context=True)
def paginator(context, adjacent_pages=5):
    """
    Adds pagination context variables for first, adjacent and next page
    links in addition to those already populated by the object_list generic
    view.
    """
    page_numbers = \
                 [n for n in \
                  range(context["page"] - adjacent_pages, context["page"] + \
                        adjacent_pages + 1) \
                  if n > 0 and n <= context["pages"]]

    # If the page/context we are rendering was a GET with query
    # parameters, then pass that in to our template so that we can
    # preserve our query parameters as we page around. This is
    # important for having sorting and filtering parameters apply to
    # every page of a listing.
    #
    # We need to make a copy of the GET dictionary because we need to
    # remove the 'page' parameter if it is defined in there. This is
    # because the the 'page' parameter is treated specially in our
    # template in that we specify different values for different urls
    # we render (previous/next/curent, etc.)
    #
    if 'request' in context and \
       context["request"].method == "GET" and \
       len(context["request"].GET) > 0:
        if 'page' in context["request"].GET:
            copy = context["request"].GET.copy()
            del copy["page"]
            query = copy.urlencode()
        else:
            query = context["request"].GET.urlencode()
    else:
        query = None

    return {
        "hits": context["hits"],
        "query" : query,
        "results_per_page": context["results_per_page"],
        "page": context["page"],
        "pages": context["pages"],
        "page_numbers": page_numbers,
        "next": context["next"],
        "previous": context["previous"],
        "has_next": context["has_next"],
        "has_previous": context["has_previous"],
        "show_first": 1 not in page_numbers,
        "show_last": context["pages"] not in page_numbers,
    }

#
#############################################################################

#############################################################################
#
# This code was gotten from: http://code.djangoproject.com/wiki/ColumnizeTag
#
@register.tag('columnize')
def columnize(parser, token):
    '''Put stuff into columns. Can also define class tags for rows and cells

    Usage: {% columnize num_cols [row_class[,row_class2...]|''
           [cell_class[,cell_class2]]] %}

    num_cols:   the number of columns to format.
    row_class:  can use a comma (no spaces, please) separated list that
                cycles (utilizing the cycle code) can also put in '' for
                nothing, if you want no row_class, but want a cell_class.
    cell_class: same format as row_class, but the cells only loop within a
                row. Every row resets the cell counter.

    Typical usage:

    <table border="0" cellspacing="5" cellpadding="5">
    {% for o in some_list %}
       {% columnize 3 %}
          <a href="{{ o.get_absolute_url }}">{{ o.name }}</a>
       {% endcolumnize %}
    {% endfor %}
    </table>
    '''
    nodelist = parser.parse(('endcolumnize',))
    parser.delete_first_token()

    #Get the number of columns, default 1
    columns = 1
    row_class = ''
    cell_class = ''
    args = token.contents.split(None, 3)
    num_args = len(args)
    if num_args >= 2:
        #{% columnize columns %}
        if args[1].isdigit():
            columns = int(args[1])
        else:
            raise template.TemplateSyntaxError('The number of columns must ' \
                                               'be a number. "%s" is not a ' \
                                               'number.') % args[2]
    if num_args >= 3:
        #{% columnize columns row_class %}
        if "," in args[2]:
            #{% columnize columns row1,row2,row3 %}
            row_class = [v for v in args[2].split(",") if v]  # split and kill
                                                              # blanks
        else:
            row_class = [args[2]]
            if row_class == "''":
                # Allow the designer to pass an empty string (two quotes) to
                # skip the row_class and only have a cell_class
                row_class = []
    if num_args == 4:
        #{% columnize columns row_class cell_class %}
        if "," in args[3]:
            #{% columnize row_class cell1,cell2,cell3 %}
            cell_class = [v for v in args[3].split(",") if v] # split and kill
                                                              # blanks
        else:
            cell_class = [args[3]]
            if cell_class == "''":
                # This shouldn't be necessary, but might as well test for it
                cell_class = []

    return ColumnizeNode(nodelist, columns, row_class, cell_class)

class ColumnizeNode(template.Node):
    def __init__(self, nodelist, columns = 1, row_class = '', cell_class = ''):
        self.nodelist = nodelist
        self.columns = int(columns)
        self.counter = 0
        self.rowcounter = -1
        self.cellcounter = -1
        self.row_class_len = len(row_class)
        self.row_class = row_class
        self.cell_class_len = len(cell_class)
        self.cell_class = cell_class

    def render(self, context):
        output = ''
        self.counter += 1
        if (self.counter > self.columns):
            self.counter = 1
            self.cellcounter = -1

        if (self.counter == 1):
            output = '<tr'
            if self.row_class:
                self.rowcounter += 1
                output += ' class="%s">' % self.row_class[self.rowcounter % self.row_class_len]
            else:
                output += '>'

        output += '<td'
        if self.cell_class:
            self.cellcounter += 1
            output += ' class="%s">' % self.cell_class[self.cellcounter % self.cell_class_len]
        else:
            output += '>'

        output += self.nodelist.render(context) + '</td>'

        if (self.counter == self.columns):
            output += '</tr>'

        return output
#
#############################################################################

#############################################################################
#
@register.inclusion_tag("asutils/icon.html")
def icon(icon_name, icon_title=""):
    """The defines a django inclusion tag called 'icon'

    This will insert the standard html defined for one of our icons
    with the path of icon is supposed to be (the latter part will
    later on become a configurable item letting us switch to different
    icon sets (although then we need to know the user.)
    """

    # If our icon_title is a string surrounded by quotes then it is a string
    # and treat it as such. Otherwise, it is a variable name and we need to
    # resolve this variable in to its value.
    #
    # XXX We need the 'context' for this to work.
#     if len(icon_title) > 0:
#         if icon_title[0] == icon_title[-1] and icon_title[0] in ('"', "'"):
#             icon_title = icon_title[1:-1]
#         else:
#             icon_title = resolve_variable(icon_title, context)

    return { 'MEDIA_URL' : settings.MEDIA_URL,
             'icon_dir'  : 'img/silk-icons',
             'icon_name' : icon_name,
             'icon_title': icon_title }

#############################################################################
#
@register.filter()
def filesize_k(value):
    """
    Expects an integer that is in kilobytes. It returns a string with
    this value rendered in to a more humane format. ie: 1,024k is 1mb.

    We expect kilobytes because integers in django db fields are
    limited to signed 32 bits.. which means file sizes greater then
    4gb can not be stored as bytes, so we store them as
    kilobytes. This is fine for video files.

    The basic code was gotten from:

    http://mail.python.org/pipermail/python-list/2007-June/445065.html
    """
    if isinstance(value, str):
        # XXX We should make sure the string is an integer.
        value = int(str)
    if not isinstance(value, int):
        return ""

    precision = 2

    bytes = value * 1024
    if bytes is 0:
        return '0bytes'
    log = math.floor(math.log(bytes, 1024))
    return "%.*f%s" % (
        precision,
        bytes / math.pow(1024, log),
        ['bytes', 'KiB', 'MiB', 'GiB', 'TiB',
         'PiB', 'EiB', 'ZiB', 'YiB'][int(log)])

#############################################################################
#
@register.filter()
def user_tz(value, user):
    """
    Expects a datetime as the value. Expects a User object as the arg.
    Looks up the 'timezone' value in the user's profile, and converts
    the given datetime in to one in the user's timezone.

    NOTE: This assumes that you have the 'pytz' module
    (pytz.sourceforge.net) and that the user profile has a field
    called 'timezone' that is a character string and that the timezone
    thus specified is a valid timezone supported by pytz.
    """

    if not isinstance(value, datetime):
        return ""

    tz = settings.TIME_ZONE
    server_tz = pytz.timezone(tz)
    if isinstance(user, User):
        try:
            tz = user.get_profile().timezone
        except ObjectDoesNotExist:
            pass
    try:
        result = value.astimezone(pytz.timezone(tz))
    except ValueError:
        # Hm.. the datetime was stored 'naieve' ie: without timezone info.
        # We assume that all times are stored in the server's timezone
        # if they are naieve.
        #
        result = value.replace(tzinfo=server_tz).astimezone(pytz.timezone(tz))
    return result

#############################################################################
#
@register.filter()
def tz_std_date(value, user):
    """This is a simplification of the kinds of time stamps we
    frequently use in our app framework. The given datetime, expressed
    in the user's profile's time zone in a standard format (that is
    defined using the django standard settings.DATETIME_FORMAT.

    XXX Later on we may add the ability for a user to specify their own date
    XXX time format to use.
    """
    if not isinstance(value, datetime):
        return ""
    return django.utils.dateformat.format(user_tz(value, user),
                                          settings.DATETIME_FORMAT)

#############################################################################
#
@register.filter()
def tz_std_date_ago(value, user):
    """
    This is a further simplification of the kinds of time stamps we
    frequently use in our app framework. It is just like tz_std_date, except
    we return the datetime string with ' (<timesince> ago)'

    NOTE: We switch to 'timeuntil' if the date provided is in the
          the future.
    """
    if not isinstance(value, datetime):
        return ""

    # We need to see if the date is before or after now. If the date does
    # not have a timezone set then we assume it is in the server's timezone.
    #
    now = datetime.utcnow().replace(tzinfo = pytz.UTC)
    if value.tzinfo is None:
        server_tz = pytz.timezone(settings.TIME_ZONE)
        value = value.replace(tzinfo = server_tz)
    if value < now:
        return "%s (%s ago)" % (tz_std_date(value, user), timesince(value))
    else:
        return "%s (in %s)" % (tz_std_date(value, user), timeuntil(value))

##############################################################################
#
@register.tag(name = 'method_arg')
def method_arg(parser, token):
    """
    This tag allows us to call the given method with the given
    argument and set the resultant value to a variable in our context.
    ie: {% method_arg foo.bar user as post %} would result in the
    variable 'post' getting the result of evaluating foo.bar(user).
    If the argument is surrounded by quotes, then it is considered a
    string and not a variable to be resolved.
    """
    try:
        tag_name, var_method_name, arg, ign, dst = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, "%r requires arguments in the " \
              "format of <variable>.<methodname> <argument> as <variable>."
    if ign.lower() != "as":
        raise template.TemplateSyntaxError, "%r requires arguments in the " \
              "format of <variable>.<methodname> <argument> as <variable>."
    (var, method_name) = var_method_name.split('.')
    return MethodArgNode(var, method_name, arg, dst)

class MethodArgNode(template.Node):
    """
    The template node sub-class that does the work of looking up the
    method you wish to invoke in your template, resolving the variable
    to pass to it and setting the resultant value in the template's
    context.
    """
    def __init__(self, var, method_name, arg, dst):
        self.var = var
        self.method_name = method_name
        self.arg = arg
        self.dest = dst

    def render(self, context):
        try:
            obj = resolve_variable(self.var, context)
            if hasattr(obj, self.method_name) and \
               isinstance(getattr(obj, self.method_name), MethodType):
                if self.arg[0] == self.arg[-1] and self.arg[0] in ('"', "'"):
                    context[self.dest] = \
                                getattr(obj, self.method_name)(self.arg[1:-1])
                else:
                    context[self.dest] = getattr(obj, self.method_name)\
                                         (resolve_variable(self.arg, context))
        except:
            # render() should never raise any exception. If something goes
            # wrong we need to log it somewhere else, not chuck it up the
            # call stack.
            #
            raise
            pass
        return ""

#############################################################################
#
# This was gotten from: http://www.djangosnippets.org/snippets/840/
#
class AddParameters(Node):
  def __init__(self, vars):
    self.vars = vars

  def render(self, context):
    req = resolve_variable('request',context)
    params = req.GET.copy()

    for i in range(0, len(self.vars), 2):
      key = self.vars[i].resolve(context)
      if key == '': key = self.vars[i]
      value = self.vars[i+1].resolve(context)
      if value == '': value = self.vars[i+1]
      params[key] = value

    return '%s?%s' % (req.path, params.urlencode())

def addparam(parser, token):
  """
  Add multiple parameters to current url

  Usage:
    {% addparam name1 value1 name2 value2 %}
                      or
    {% addparam "name1" value1 "name2" value2 %}

    variable can be use inplace of names and values
    example: {% addparam "view" message.id %}

  """

  bits = token.contents.split(' ')
  if len(bits) < 2:
    raise TemplateSyntaxError, "'%s' tag requires atleast two arguments" % bits[0]

  if len(bits)%2 != 1:
    raise TemplateSyntaxError, "The arguments must be pairs"

  vars = [parser.compile_filter(bit) for bit in bits[1:]]
  return AddParameters(vars)

register.tag('addparam', addparam)

#############################################################################
#
class PathFirstNode(template.Node):
    def __init__(self, path, var_name):
        self.path = Variable(path)
        self.var_name = var_name

    def render(self, context):
        path = self.path.resolve(context)
        context[self.var_name] = "/" + path.split('/')[1]
        return ""

@register.tag(name = "pathfirst")
def do_path_first(parser, token):
    """
    Given a path (typically request.path) split it and get the first
    element of the path and put it into the templates context as
    the given variable.
    """
    try:
        tag_name, path, ign, var_name = token.split_contents()
        if ign.lower() != 'as':
            raise template.TemplateSyntaxError, "%r tag expects arguments of the form 'variablename as variablename'" % token.contents.split()[0]
    except ValueError:
        raise template.TemplateSyntaxError, "%r tag requires two arguments separated by the word 'as'" % token.contents.split()[0]
    return PathFirstNode(path, var_name)

####################################################################
#
class IfObservedNode(Node):
    """
    Cribbed from the 'IfChangedNode' class in django/template/defaulttags.py
    The goal is to see if the object passed in is being 'observed'
    by the 'notification' app.

    NOTE: If the notification app is not available then this will always
          say that the object is NOT being observed.
    """
    def __init__(self, nodelist_true, nodelist_false, obj_var_name, signal):
        self.nodelist_true, self.nodelist_false = nodelist_true, nodelist_false
        self.obj_var = template.Variable(obj_var_name)
        self.signal = signal

    def render(self, context):
        """
        See if the variable is being observed. This only works if the
        notifcation app is available, and if the user is authenticated.
        """

        # We have to have a user, it has to be authenticated, and the
        # notification app has to be installed for us to proceed.
        #
        if 'user' in context and \
                context['user'].is_authenticated and \
                notification:
            user = context['user']
        elif self.nodelist_false:
            # Hm. One of our above tests failed, if we have a 'else' clause
            # then render it.
            #
            return self.nodelist_false.render(context)
        else:
            # Otherwise return an empty string.. the test failed, the object
            # is not observable.
            #
            return ''

        try:
            # If the 'signal' is surrounded by quotes then we need to
            # interpret it as a string, otherwise we treat it as a variable
            # and look it up in our context.
            #
            if self.signal[0] == self.signal[-1] and self.signal in ('"', "'"):
                signal = self.signal[1:-1]
            else:
                signal = template.Variable(self.signal).resolve(context)

            # Okay, we can actually test if the object is observed.
            #
            obj = self.obj_var.resolve(context)
            succeeded = notification.models.is_observing(obj,user,
                                                         signal = signal)
        except template.VariableDoesNotExist:
            succeeded = False

        if succeeded:
            return self.nodelist_true.render(context)
        elif self.nodelist_false:
            return self.nodelist_false.render(context)
        return ''

####################################################################
#
@register.tag
def ifobserved(parser, token):
    """
    It is passed a variable for an object name, and either a signal name in
    quotes, or a variable that contains the signal name.

    If the specified object is being observed by the notifcation system under
    the specified signal then the 'true' clause of the if statement will be
    rendered in the context. Otherwise, if a 'false' clause is provided that
    will be rendered.

    If the user is not authenticated, if the notification system is not
    available, or if any of the variables fail to resolve, it is treated as a
    'false'.

    Examples:

    {% ifobserved topic "topic_change_notice %}
      Topic {{ topic }} is being observed by you.
    {% else %}
      Topic {{ topic }} is not being obsreved by you.
    {% endifobserved %}

    Arguments:
    - `parser`: The django template parser object
    - `token`: The raw contents of our `ifobserved` tag.
    """
    try:
        tag_name, obj_name, signal = token.split_contents()
    except ValueError:
        raise "%r tag requires two arguments" % token.contents.split()

    nodelist_true = parser.parse(('else', 'endifobserved'))
    token = parser.next_token()
    if token.contents == 'else':
        nodelist_false = parser.parse(('endifobserved',))
        parser.delete_first_token()
    else:
        nodelist_false = template.NodeList()
    return IfObservedNode(nodelist_true, nodelist_false, obj_name, signal)

#############################################################################
#
@register.tag('ifactive')
def do_ifactive(parser, token):
    """
    Crribbed from http://www.djangosnippets.org/snippets/1153/

    Defines a conditional block tag, "ifactive" that switches based on whether
    the active request is being handled by a particular view (with optional
    args and kwargs).

    Has the form:

    {% ifactive request path.to.view %}
        [Block to render if path.to.view is the active view]
    {% else %}
        [Block to render if path.to.view is not the active view]
    {% endifactive %}

    'request' is a context variable expression which resolves to the
    HttpRequest object for the current request. (Additionally, the
    ActiveViewMiddleware must be installed for this to work.)

    'path.to.view' can be a string with a python import path (which must be
    mentioned in the urlconf), or a name of a urlpattern (i.e., same as the
    argument to the {% url %} tag).

    You can also pass arguments or keyword arguments in the same form as
    accepted by the {% url %} tag, e.g.:

    {% ifactive request path.to.view var1="bar",var2=var.prop %}...{% endifactive %}

    or:

    {% ifactive request path.to.view "bar",var.prop %}...{% endifactive %}

    The else block is optional.
    """

    end_tag = 'endifactive'

    active_nodes = parser.parse((end_tag,'else'))
    end_token = parser.next_token()
    if end_token.contents == 'else':
        inactive_nodes = parser.parse((end_tag,))
        parser.delete_first_token()
    else:
        inactive_nodes = None

    tag_args = token.contents.split(' ')
    if len(tag_args) < 3:
        raise TemplateSyntaxError("'%s' takes at least two arguments"
                                  " (context variable with the request, and path to a view)" % tag_args[0])

    request_var = tag_args[1]
    view_name = tag_args[2]
    args, kwargs = _parse_url_args(parser, tag_args[3:])

    return ActiveNode(request_var, view_name, args, kwargs, active_nodes,
                      inactive_nodes)

#############################################################################
#
class ActiveNode(Node):
    """
    Cribbed from http://www.djangosnippets.org/snippets/1153/
    """
    def __init__(self, request_var, view_name, args, kwargs, active_nodes,
                 inactive_nodes=None):
        self.request_var = request_var
        self.view_name = view_name
        self.args = args
        self.kwargs = kwargs
        self.active_nodes = active_nodes
        self.inactive_nodes = inactive_nodes

    def render(self, context):

        request = resolve_variable(self.request_var, context)

        view, default_args = _get_view_and_default_args(self.view_name)

        if getattr(request, '_view_func', None) is view:

            resolved_args = [arg.resolve(context) for arg in self.args]
            if request._view_args == resolved_args:

                resolved_kwargs = dict([(k, v.resolve(context)) for k, v in self.kwargs.items()])
                resolved_kwargs.update(default_args)

                if request._view_kwargs == resolved_kwargs:
                    return self.active_nodes.render(context)

        if self.inactive_nodes is not None:
            return self.inactive_nodes.render(context)
        else:
            return ''

def _get_patterns_map(resolver, default_args=None):
    """
    Cribbed from http://www.djangosnippets.org/snippets/1153/

    Recursively generates a map of
    (pattern name or path to view function) -> (view function, default args)
    """

    patterns_map = {}

    if default_args is None:
        default_args = {}

    for pattern in resolver.url_patterns:

        pattern_args = default_args.copy()

        if isinstance(pattern, RegexURLResolver):
            pattern_args.update(pattern.default_kwargs)
            patterns_map.update(_get_patterns_map(pattern, pattern_args))
        else:
            pattern_args.update(pattern.default_args)

            if pattern.name is not None:
                patterns_map[pattern.name] = (pattern.callback, pattern_args)

            # HACK: Accessing private attribute of RegexURLPattern
            callback_str = getattr(pattern, '_callback_str', None)
            if callback_str is not None:
                patterns_map[pattern._callback_str] = (pattern.callback, pattern_args)

    return patterns_map

_view_name_cache = None

def _get_view_and_default_args(view_name):
    """
    Cribbed from http://www.djangosnippets.org/snippets/1153/

    Given view_name (a path to a view or a name of a urlpattern,
    returns the view function and a dict containing any default kwargs
    that are specified in the urlconf for that view.
    """

    global _view_name_cache

    if _view_name_cache is None:
        _view_name_cache = _get_patterns_map(get_resolver(None))

    try:
        return _view_name_cache[view_name]
    except KeyError:
        raise KeyError("%s does not match any urlpatterns" % view_name)

def _parse_url_args(parser, bits):
    """
    Cribbed from http://www.djangosnippets.org/snippets/1153/

    Parses URL parameters in the same way as the {% url %} tag.
    """

    args = []
    kwargs = {}

    for bit in bits:
        for arg in bit.split(","):
            if '=' in arg:
                k, v = arg.split('=', 1)
                k = k.strip()
                kwargs[smart_str(k,'ascii')] = parser.compile_filter(v)
            elif arg:
                args.append(parser.compile_filter(arg))

    return args, kwargs

####################################################################
#
@register.simple_tag
def boundfield_label_tag(field, contents):
    """
    A bound filed has a 'label_tag' method that optionally takes a
    'content' argument. If the content was not supplied it uses the
    field's label.

    There are times when we want to supply the content for the label
    instead of haivng it automatically field in from the field's label
    text.

    However, passing in arguments in the template system to methods is
    something we can not do. This tag lets us pass in a content
    argument to a BoundField instance's 'label_tag()' method.

    XXX Simple tags are annoying in that they do NOT support filters
        being applied to variables passed as arguments. When I have
        more time I will re-write this to be a proper tag so that we
        can pass variables in that have filters being applied to them,
        instead of using the {% with %} hack that we have to for now.

    Arguments:
    - `field`: The BoundField instance we are working with.
    - `contents`: The text to use for the <label></label>
    """
    if not hasattr(field, 'label_tag'):
        return ""
    return field.label_tag(contents = contents)

