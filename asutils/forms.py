#!/usr/bin/env python
#
# File: $Id: forms.py 1557 2008-07-25 01:24:03Z scanner $
#
"""
This module defines some forms fields that we want to centralize
in one area.
"""

from django.template import RequestContext
from django.shortcuts import render_to_response
from django.http import HttpResponse

from django import forms
from django.forms.widgets import TextInput,flatatt
from django.forms.util import smart_unicode

from django.utils.html import escape

##############################################################################
#
class AutoCompleteField(TextInput):
    """
    This scriptaculous autocomplete field was gotten from

       http://www.djangosnippets.org/snippets/253/

    written by http://www.djangosnippets.org/users/eopadoan/
    """
    def __init__(self, url='', options='{paramName: "text"}', attrs=None):
        self.url = url
        self.options = options
        if attrs is None:
            attrs = {}
        self.attrs = attrs

    def render(self, name, value=None, attrs=None):
        final_attrs = self.build_attrs(attrs, name=name)
        if value:
            value = smart_unicode(value)
            final_attrs['value'] = escape(value)
        if not self.attrs.has_key('id'):
            final_attrs['id'] = 'id_%s' % name
        return (u'<input type="text" name="%(name)s" id="%(id)s"/> '
                '<div class="autocomplete" id="box_%(name)s"></div>'
                '<script type="text/javascript">'
                'new Ajax.Autocompleter(\'%(id)s\', \'box_%(name)s\', '
                '\'%(url)s\', %(options)s);'
                '</script>') % {'attrs' : flatatt(final_attrs),
                                'name'  : name,
                                'id'    : final_attrs['id'],
                                'url'   : self.url,
                                'options' : self.options}


#
#  Usage example
#
# class TestForm(forms.Form):
#     person = forms.CharField(required=False,
#                              widget=AutoCompleteField(url='/autocomplete/'))

# def test_view(request):
#     return render_to_response('test_template.html', {'form': TestForm()},
#                               context_instance=RequestContext(request))

# def autocomplete(request):
#     """ Return a simple response with a <ul>
#     """
#     if request.method == 'POST':
#         text = request['text']
#     # Search things on the database with 'text'
#     # Or simply perform any computing with this
#     # to generate a <ul>
#     # But this is not important here.
#     return HttpResponse(
#         '''
#         <ul>
#            <li>ACME Inc <span class="informal"> 5012 East 5th Street</span></li>
#            <li>Scriptaculous <span class="informal"> 1066 West Redlands Parkway</span></li>
#            <li>Test00001</li>
#            <li>Test00001</li>
#            <li>Another Silly test</li>
#            <li>%s</li>

#         </ul>'''%text) # put the text in the end of the example list to see if this works
