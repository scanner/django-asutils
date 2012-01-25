#
# File: $Id: filterfields.py 1551 2008-07-24 22:16:34Z scanner $
#
"""
Like 'filterspecs.py' in the django.contrib.admin module this defines a
class that can be used for filtering arbitrary fields in a model with
a related UI.

The goal is if you want to search/filter a model and present those
results to the user, but do not want to have to re-write filtering
code unique to your model, you use this class to create the form,
parse the results, and and parse query parameters to create a QuerySet
that filters your model.
"""

# Django imports
#
from django.db import models

# Create some additional filter specs so that we can filter on more fields
# then the filter spects in the admin app provide.
#

############################################################################
#
# class FilterSpec(Object):
#     """
#     A lot of the ideas for these FilterSpec objects came right from the
#     FilterSpect object in the django.contrib.admin app.

#     I made my own because I wanted to acutally use these for more fields and
#     types of queries then what the FilterSpec's that the django.contrib.admin
#     app supported (and that you can supply more the one filter spec.)
#     """

#     # This is a class instance variable that holds the list of registered
#     # filter specs.
#     #
#     filter_specs = []

#     ########################################################################
#     #
#     def __init__(self, f, request, params, model):
#         self.field = f
#         self.params = params

#     ########################################################################
#     #
#     @classmethod
#     def register(cls, test, factory):
#         """
#         This is a class method that is called when you want to add a new filter
#         spect to the set of currently known filter specs.

#         You provide the 'test' function that is passed the django model field
#         type object (True if the passed in field is of the type that this
#         filter spec supports.)

#         You also provide the 'factor' which the class invoked to create an
#         instance of the filter spec of the appropriate type.
#         """
#         cls.filter_specs.append((test, factory))

#     ########################################################################
#     #
#     @classmethod
#     def create(cls, f, request, params, model):
#         """
#         This class method is what is used by the FilterFields class to search
#         through the registered filter specs looking for one whose test returns
#         True for the given field. It will then instantiate the appropriate
#         FilterSpec sub-class with the given parameters.
#         """
#         for test, factory in cls.filter_specs:
#             if test(f):
#                 return factory(f, request, params, model)
#         raise NotImplementedError("No suppoted FilterSpec for a field of "
#                                   "type %s" % type(f))

#     ########################################################################
#     #
#     def get_filter_args(query_params):
#         """
#         Given a dictionary of query parameters go through the parameters and
#         for each one that matches the kind of query set filter this FilterSpec
#         represents add the argument and its value to a list that we return
#         to our caller.
#         """
#         raise NotImplementedError

#     ########################################################################
#     #
#     def has_output(self):
#         return True

#     def choices(self, cl):
#         raise NotImplementedError()

#     ########################################################################
#     #
#     def title(self):
#         """
#         When displaying a filter spec as a form element this provides the name
#         of the filter spec. We use the verbose name of the field that this
#         filter spec is for.
#         """
#         return self.field.verbose_name

#     def output(self, cl):
#         t = []
#         if self.has_output():
#             t.append(_(u'<h3>By %s:</h3>\n<ul>\n') % self.title())

#             for choice in self.choices(cl):
#                 t.append(u'<li%s><a href="%s">%s</a></li>\n' % \
#                     ((choice['selected'] and ' class="selected"' or ''),
#                      iri_to_uri(choice['query_string']),
#                      choice['display']))
#             t.append('</ul>\n\n')
#         return "".join(t)


    
#     def __init__(self, f, request, params, model):
#         super(CharFilterSpec, self).__init__(f, request, params, model)
#         self.lookup_kwarg = '%s__exact' % f.name
#         self.lookup_val = request.GET.get(self.lookup_kwarg, None)

#     def choices(self, cl):
#         yield {'selected': self.lookup_val is None,
#                'query_string': cl.get_query_string({}, [self.lookup_kwarg]),
#                'display': _('All')}
#         for k, v in self.field.choices:
#             yield {'selected': smart_unicode(k) == self.lookup_val,
#                     'query_string': cl.get_query_string({self.lookup_kwarg: k}),
#                     'display': v}

# FilterSpec.register(lambda f: isinstance(f, models.CharField), CharFilterSpec)

############################################################################
#
class FilterSpec(object):
    """
    This is the base class for FilterSpec objects. The idea for how to do this
    was cribbed from the django.contrib.admin app which lets you specify
    fields to filter on in the admin ui based on data in the Admin sub-class
    of a django model.

    The idea is that different FilterSpec sub-classes will know how to filter
    different types of fields in a django model class.

    For example, a filter spec that knows how to deal with CharFields would
    understand that if we have a field declaration of:

        name = models.CharField(maxlength = 256, db_index = True)

    then we know that we can perform the following filters:

        name__exact
        name__iexact
        name__contains
        name__icontains
        name__gt
        name__gte
        name__lt
        name__lte
        name__startswith
        name__istartswith
        name__endswith
        name__iendswith
        name__isnull
        name__regex
        name__iregex

    This is because we know that 'name' is a char field and we know what
    kinds of filters are allowed on a char field.

    NOTE: We do not support foreign key relationships. This is mostly a
    problem with how we specify the fields that can be filtered on. If you
    specify a foreign key field you need to specify what field on that related
    object you want to do the filtering on. I figure eventually we will
    support this by letting you specify a field as
    'foreignkeyfieldname__subfield'

    NOTE: How do you use this? This base class is implemented by sub-classes
    knowing how to filter a specific field type. Those sub-classes register
    themsevles with this base class.

    Then, when a FilterSpec is created it finds out which registered filter
    specs apply to which fields it has been told to allow filtering on.
    """

    # This is a class instance variable that holds the list of registered
    # filter specs.
    #
    filter_specs = []

    ########################################################################
    #
    def __init__(self, f, request, params, model):
        self.field = f
        self.params = params

    ########################################################################
    #
    @classmethod
    def register(cls, test, factory):
        """
        This is a class method that is called when you want to add a new filter
        spect to the set of currently known filter specs.

        You provide the 'test' function that is passed the django model field
        type object (True if the passed in field is of the type that this
        filter spec supports.)

        You also provide the 'factor' which the class invoked to create an
        instance of the filter spec of the appropriate type.
        """
        cls.filter_specs.append((test, factory))

    ########################################################################
    #
    @classmethod
    def create(cls, f, request, params, model):
        """
        This class method is what is used by the FilterFields class to search
        through the registered filter specs looking for one whose test returns
        True for the given field. It will then instantiate the appropriate
        FilterSpec sub-class with the given parameters.
        """
        for test, factory in cls.filter_specs:
            if test(f):
                return factory(f, request, params, model)
        raise NotImplementedError("No suppoted FilterSpec for a field of "
                                  "type %s (field name: '%s')" % \
                                  (type(f), f.name))
        
    ########################################################################
    #
    def has_output(self):
        """
        Returns 'True' if this filter spec can render a HTML form that lets
        the user specify a filter to apply to the model for this field.

        (I believe this will always be 'True'. This is part of what I cribbed
        directly from the django.contrib.admin app but I am not sure that it
        applies to what I am doing inere.)
        """
        return True

    ########################################################################
    #
    def match_query_param(self, param):
        """
        Returns 'True' if the given parameter from a QueryDict (gotten from a
        HTTP request via a django view, presumably) is the text representation
        for a filter of a specific field that this instance of a FilterSpec
        supports.

        What does that mean?

        Let us say this is a FilterSpec object that knows how to filter the
        following field definition in a django model:

           name = models.CharField(maxlength = 256, db_index = True)

        This means that if the django view (that handled some sort of request
        for this model) had a query parameter:

           ?name__icontains=bloop

        then when this method is called with the param 'name__icontains' it
        would return 'True' because it was created to recognize filters on the
        field 'name' and because 'name' is a CharField it knew to recognize
        that 'icontains' is a valid filter for 'name.'

        This is the case where the FilterSpec object knew how to handle
        CharField classes.
        """
        # Each sub-class may need to implement this differently
        # but this will work fairly well for most classes of filter spec
        # out of the box.
        #
        try:
            field_name, field_lookup = param.split("__")
        except ValueError:
            return False

        if field_name != self.field.name:
            return False

        if field_lookup in self.field_lookups:
            # We stash the field lookup being used in our object for later
            # use by the field_lookup() and field_value() methods. Because
            # we are holding state like this in a single object that may be
            # used multiple times in a single request this requires
            # that the field_lookup() and field_value() methods if they
            # require this information follow this method invocation.
            #
            self.field_lookup_value = str(field_lookup)
            return True
        return False


    ########################################################################
    #
    def field_lookup(self, param):
        """
        This converts the parameter from a user's query in a URL in to what we
        should actually pass to django's 'filter()' method. This lets us
        rewrite queries from one form in to another. One possible use, for
        instance, is to convert all 'contains' 'startswith' etc, in to
        'icontains', 'istartswith'
        """
        return str(param)

    ########################################################################
    #
    def field_value(self, value):
        """
        This does any normalization or cleaning we need to on the value of a
        field lookup.  The default case will just pass the result through.
        """
        return str(value)
    
############################################################################
#
class CharFilterSpec(FilterSpec):
    """
    A FilterSpec that understands how to filter CharFields and present a web
    UI to let a user specify a filter for a CharField.

    As such this FilterSpec will specifically know to support the following
    django field lookups:

        name__exact
        name__iexact
        name__contains
        name__icontains
        name__gt
        name__gte
        name__lt
        name__lte
        name__startswith
        name__istartswith
        name__endswith
        name__iendswith
        name__isnull
        name__regex
        name__iregex

    NOTE: Maybe we should convert fields that may be case insensitive to
    be case insensitive.
    """

    # The field lookups we support. The actual lookup is going to be
    # <field name>__<field lookup>.
    #
    # This also lets us map from the term specified to the term we want them
    # to use. In this case we make all searches that may be case insensitive
    # to be case insensitive.
    #
    field_lookups = {
        'exact'       : 'iexact',
        'iexact'      : 'iexact',
        'contains'    : 'icontains',
        'icontains'   : 'icontains',
        'gt'          : 'gt',
        'gte'         : 'gte',
        'lt'          : 'lt',
        'lte'         : 'lte',
        'startswith'  : 'istartswith',
        'istartswith' : 'istartswith',
        'endswith'    : 'iendswith',
        'iendswith'   : 'iendswith',
        'isnull'      : 'isnull',
        'regex'       : 'iregex',
        'iregex'      : 'iregex',
        }

    ########################################################################
    #
    def field_lookup(self, param):
        """
        Convert lookups to case insensitive ones.
        """
        field_name, field_lookup = param.split("__")
        return "%s__%s" % (str(field_name),
                           CharFilterSpec.field_lookups[field_lookup])

FilterSpec.register(lambda f: isinstance(f, models.CharField), CharFilterSpec)

############################################################################
#
class IntFilterSpec(FilterSpec):
    """
    A FilterSpec that understands how to filter IntFields.

    This will support the following django field lookups:

       name__exact
       name__in    (comma separated list)
       name__gt
       name__gte
       name__lt
       name__lte
       name__isnull
       name__range (comma separate list of two values)
       
    """

    field_lookups = ('exact','in','gt','gte','lt','lte','isnull','range')
    
    ########################################################################
    #
    def field_value(self, value):
        """
        For an int, we need to return a value as an int. Also if the
        field lookup is 'in' or 'range' we need to return a list, we
        assume that the value is a comma separated list of ints.
        """
        if self.field_lookup_value in ('in', 'range'):
            return [int(x) for x in value.split(',')]
        return int(value)

FilterSpec.register(lambda f: isinstance(f, models.IntegerField), IntFilterSpec)
FilterSpec.register(lambda f: isinstance(f, models.AutoField), IntFilterSpec)

############################################################################
#
class FilterFields(object):
    """
    The class makes it easier for developers to filter on various kinds of
    fields in a django model.

    The class itself serves two functions: Creation of a query string to use on
    http requests to filter a model's query set, and the actual application of
    a query string on a http request to filter the model's query set.

    The first part is applied by generating a form that can be used by a user
    to define a simple query set.

    There are also methods used to incrementally define form query fields so
    that some clever javascript can extend a form according to user's input.
    """

    ########################################################################
    #
    def __init__(self, request, model, field_names):
        """
        request: The request currently being processed. The current
                 filtering fields are determined based on GET
                 parameters in the request.

        model: The django model that is being filtered. We need this so that we
               can determine the types of the fields that are being filtered
               on.

        fields: The names of the fields in our model that the user can use for
                filtering. (a list or tuple)
        """
        self.model = model
        self.opts = model._meta
        self.lookup_opts = self.opts
#         self.manager = self.opts.admin.manager
        self.manager = self.model.objects
        self.field_names = field_names
        self.request = request
        self.params = dict(request.GET.items())
        self.filter_specs, self.has_filters = self.get_filters(request)
        return

    ########################################################################
    #
    def get_filters(self,request):
        """
        Retrieves a list of FilterSpec objects based on the fields we may
        filter on.
        """
        filter_specs = []

        # Get references to the actual fields in the model that we want to be
        # able to filter on.
        #
        filter_fields = [self.lookup_opts.get_field(field_name) \
                         for field_name in self.field_names]

        # For each of the fields that we want to filter on, instantiate the
        # proper FilterSpec (based on the type of the field.)
        #
        for f in filter_fields:
            spec = FilterSpec.create(f, self.request, self.params, self.model)
            if spec and spec.has_output():
                filter_specs.append(spec)

        return filter_specs, bool(filter_specs)

    ########################################################################
    #
    def query_from_form(self):
        """
        Using the form posted in the 'request' build the query string that can
        be used by this class to filter the model according to the user's input
        in the form.
        """
        pass

    ########################################################################
    #
    def form_from_query(self):
        """
        Construct a Form based on the filter fields in the query, use the
        values of the filtered fields in the query as initial data for the
        form.
        """
        pass

    ########################################################################
    #
    def form_from_field(self, field_name):
        """
        Return the element of a form to specify the filter for the given field.
        """
        pass
    
    ########################################################################
    #
    def get_query_set(self):
        """
        Based on the filter fields specified in the query construct
        a chain of query sets that will filter the model appropriately.
        """
        kwargs = {}

        # if we have no filters, then we return all the objects.
        #
        if not self.has_filters:
            return self.manager.all()
        
        # NOTE: We are only apply 'and' filters, and as such, they all
        # have the same effect no matter what order we specify them
        # in.
        #

        # Go through all of the parameters in the GET query. We are looking
        # for ones that match a pattern that one of our filter specs matches.
        #
        for fs in self.filter_specs:
            for param,value in self.request.GET.items():

                # See if the parameter is one that the current filter spec
                # matches.
                #
                if fs.match_query_param(param):
                    kwargs[fs.field_lookup(param)] = fs.field_value(value)

        # If at the end of apply every parameter to every filter set we find
        # no matches, return the 'all' objects queryset.
        #
        if len(kwargs) == 0:
            return self.manager.all()

        # Otherwise return a query set that is filtered according to the
        # arguments in the request object.
        #
        return self.manager.filter(**kwargs)
