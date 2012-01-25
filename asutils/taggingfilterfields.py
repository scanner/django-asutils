#!/usr/bin/env python
#
#
"""
This module contains a subclass of the filterfields.FilterFields class
which does one additional thing - it will also filter by any tags.

Basically, it will look through the model being filtered for a field
that is a ModelTaggedItemManager from tagging.managers and if that
exists, it will also take in to account the 'tags_any' and 'tags_all'
fields in the HTTP REQUEST object and apply those to the filter it
returns to the caller.

This is in its own module to separate out the dependency on the
'django tagging' app written by James Bennett.
"""

# System imports
#

# Django imports
#

# 3rd party django imports
#
import tagging.managers

# asutils imports
#
import filterfields

############################################################################
#
class TaggingFilterFields(filterfields.FilterFields):
    """
    This is a sub-class of FilterFields.

    When instantiated it will see if the model it is being
    instantiated with has any fields that are instances of
    tagging.managers.ModelTaggedItemManager. If it does it will record
    that field.

    When building the query set for that model based on the HTTP
    REQUEST it was created with, it will look for 'tag_any' and
    'tag_all' requests parameters and use those to additionally filter
    the request to include model instances that have any ('tag_any')
    of the tags provided or all ('tag_all') of the tag provided in the request.

    The request can not use both 'tag_any' and 'tag_all'.
    """

    ########################################################################
    #
    def __init__(self, request, model, field_names):

        # First do the initialization in our parent class.
        #
        super(TaggingFilterFields, self).__init__(request, model, field_names)

        # and now look for an instance of ModelTaggedItemManager
        # in the attributes of the model we were passed. If we find
        # it record it so we can use it later.
        #
        # NOTE: We stop at the first one we find.
        #
        self.tags_all = None
        self.tags_any = None
        self.tagged = None
        for field_name in dir(model):
            try:
                if isinstance(getattr(model,field_name),
                              tagging.managers.ModelTaggedItemManager):
                    self.tagged = getattr(model,field_name)
                    break
            except AttributeError:
                # Getting attribute errors while examing the model
                # are okay.. just skip over those. This means that they
                # did not match anyways.
                #
                pass

        # Process the GET parameters to see if the user is trying to
        # change their filter down by adding new tags to use in a
        # 'tag_any' or 'tag_all'.
        self.augment_request()

        return

    ########################################################################
    #
    def augment_request(self):
        """
        The point of this is the user may have a request that looks
        like '?tag_any=cheese&add_tag_any=toast'

        The 'tag_any=cheese' is the existing set of tags being
        filtered on and they want to augment this list with the tag
        for 'toast'.

        This also looks for 'del_tag_any' and 'del_tag_all' and
        removes all keywords listed on those parameters from the set
        of keywords currently being filtered on.

        ie: If we were called with:

         '?tag_all=cheese,toast&del_tag_all=toast'
         
        we would end up with the GET request of:

         '?tag_all=cheese'

        This processing is done after 'add_tag_any' and 'add_tag_all'

        XXX We do not check for the user trying to use 'add_tag_any' and
            'add_tag_all' at the same time. We basiclly check 'add_tag_any'
            first, and if that fails we look for 'add_tag_all'.

        NOTE: This will create a new GET QueryDict, and set it on the
              request object. ie: this basically re-writes the
              parameters as if the user had simply specified the
              additional tag on 'tag_any' or 'tag_all'.
        """

        if self.request.GET.has_key('add_tag_any'):
            new_tags = self.request.GET['add_tag_any'].split(',')
            if self.request.GET.has_key('tag_any'):
                new_tags.extend(self.request.GET['tag_any'].split(','))
            new_get = self.request.GET.copy()
            del new_get['add_tag_any']

            # the set(new_tags)) is to remove any duplicated tags.
            #
            new_get['tag_any'] = ','.join(set(new_tags))
            self.request.GET = new_get
            return
        
        elif self.request.GET.has_key('add_tag_all'):
            new_tags = self.request.GET['add_tag_all'].split(',')
            if self.request.GET.has_key('tag_all'):
                new_tags.extend(self.request.GET['tag_all'].split(','))
            new_get = self.request.GET.copy()
            del new_get['add_tag_all']
            new_get['tag_all'] = ','.join(set(new_tags))
            self.request.GET = new_get
            return
        
        # Look for tags to remove from our filter.
        #
        if self.request.GET.has_key('del_tag_any'):
            del_tags = set(self.request.GET['del_tag_any'].split(','))
            if self.request.GET.has_key('tag_any'):
                new_get = self.request.GET.copy()
                del new_get['del_tag_any']
                new_tags = set(self.request.GET['tag_any'].split(','))
                new_get['tag_any'] = ','.join(new_tags - del_tags)
                self.request.GET = new_get
            return

        elif self.request.GET.has_key('del_tag_all'):
            del_tags = set(self.request.GET['del_tag_all'].split(','))
            if self.request.GET.has_key('tag_all'):
                new_get = self.request.GET.copy()
                del new_get['del_tag_all']
                new_tags = set(self.request.GET['tag_all'].split(','))
                new_get['tag_all'] = ','.join(new_tags - del_tags)
                self.request.GET = new_get
            return
        return
            
    ########################################################################
    #
    def get_query_set(self):
        """
        Get the query_set our parent class would generate.  If we have
        a ModelTaggedItemManager in self.tagged and if we have either
        'tag_any' or 'tag_all' in our HTTP REQUEST object, further
        filter the query set we got from our parent class instance by
        calling 'with_all' or 'with_any' methods on our
        TaggedItemManager.

        NOTE: This has the side affect that it sets up the instance
              variable 'self.tags_any' or 'self.tags_all' with a list
              of strings that are the tags being filtered on.
        """

        orig_queryset = filterfields.FilterFields.get_query_set(self)

        # We have no tagged item manager.. return the query set unmolested.
        #
        if self.tagged is None:
            return orig_queryset

        # We have a tagged item manager.. see if the user is asking for
        # filtering based on tags.
        #
        if self.request.GET.has_key('tag_any'):
            self.tags_any = self.request.GET['tag_any'].split(',')
            if len(self.tags_any) == 0 or len(self.request.GET['tag_any']) ==0:
                self.tags_any = None
                return orig_queryset
            return self.tagged.with_any(self.request.GET['tag_any'],
                                        orig_queryset)
        elif self.request.GET.has_key('tag_all'):
            self.tags_all = self.request.GET['tag_all'].split(',')
            if len(self.tags_all) == 0 or len(self.request.GET['tag_all']) ==0:
                self.tags_all = None
                return orig_queryset
            return self.tagged.with_all(self.request.GET['tag_all'],
                                        orig_queryset)
        else:
            # THey have neither 'tag_any' nor 'tag_all' in the GET parameters.
            # We return the original query set unmolested.
            #
            return orig_queryset
