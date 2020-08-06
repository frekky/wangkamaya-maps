""" Set of functions to deal with retrieving and updating existing rows from the database """

from django.db.models import Q
from featuremap.models import Language
import logging

logger = logging.getLogger(__name__)

def handle_matching_set(model, objs, dry_run=False):
    num = objs.count()
    if num > 1:
        logger.debug("deleting %d matching instances of model %s" % (model._meta.name))
        if not dry_run:
            objs.delete()
        return None
    elif num == 1:
        logger.debug("found single match of model %s, updating object id '%s'" % (model._meta.name, str(objs[0].id)))
        return objs[0]
    else:
        return None

def find_model_instance(model, values_unique, dry_run=False):
    """ most basic attempt to find an existing model row based on a set of 'soft-unique' values """
    # TODO: find a model instance if it is present in the database already
    instances = list(model.objects.filter(model, **values_unique))
    if len(instances) == 0:
        return None
    elif len(instances) == 1:
        return instances[0]
    else:
        # soft uniqueness-constraint violation...?
        return instances

def find_matching_by_source(model, source=None, source_ref=None):
    filter = {
        'source__exact': source,
        'source_ref__exact': source_ref,
    }
    objs = model.objects.filter(**filter)

    return handle_matching_set(model, objs)

def get_find_matching_by_source(model):
    return lambda model, *args, **kwargs: find_matching_by_source(model, *args, **kwargs)

def find_matching_lang(model, name):
    filter = Q(name__iexact=name) | Q(alt_names__icontains=name)
    objs = Language.objects.filter(filter)
    return handle_matching_set(Language, objs)
    
