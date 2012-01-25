#
# File: $Id: gfk.py 1638 2008-09-27 01:47:23Z scanner $
#
"""
From: http://www.djangosnippets.org/snippets/1079/

his is an improvement on snippet 984. Read it's description and this
blog post for good explanations of the problem this solves -
http://zerokspot.com/weblog/2008/08/13/genericforeignkeys-with-less-queries/

Unlike snippet 984, this version is able to handle multiple generic
foreign keys, generic foreign keys with nonstandard ct_field and
fk_field names, and avoids unnecessary lookups to the ContentType
table.

To use, just assign an instance of GFKManager as the objects attribute
of a model that has generic foreign keys. Then:

MyModelWithGFKs.objects.filter(...).fetch_generic_relations()

The generic related items will be bulk-fetched to minimize the number
of queries.
"""

from django.db.models.query import QuerySet
from django.db.models import Manager
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.generic import GenericForeignKey

class GFKManager(Manager):
    """
    A manager that returns a GFKQuerySet instead of a regular QuerySet.

    """
    def get_query_set(self):
        return GFKQuerySet(self.model)

class GFKQuerySet(QuerySet):
    """
    A QuerySet with a fetch_generic_relations() method to bulk fetch
    all generic related items.  Similar to select_related(), but for
    generic foreign keys.

    Based on http://www.djangosnippets.org/snippets/984/

    """
    def fetch_generic_relations(self):
        qs = self._clone()

        gfk_fields = [g for g in self.model._meta.virtual_fields
                      if isinstance(g, GenericForeignKey)]

        ct_map = {}
        item_map = {}

        for item in qs:
            for gfk in gfk_fields:
                ct_id_field = self.model._meta.get_field(gfk.ct_field).column
                ct_map.setdefault(
                    (ct_id_field, getattr(item, ct_id_field)), {}
                    )[getattr(item, gfk.fk_field)] = (gfk.name, item.id)
            item_map[item.id] = item

        for (ct_id_field, ct_id), items_ in ct_map.items():
            ct = ContentType.objects.get_for_id(ct_id)
            for o in ct.model_class().objects.select_related().filter(
                id__in=items_.keys()).all():
                (gfk_name, item_id) = items_[o.id]
                setattr(item_map[item_id], gfk_name, o)

        return qs
