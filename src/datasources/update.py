from django.db.models import Q
from featuremap.models import Language
import logging

logger = logging.getLogger(__module__)

def handle_matching_set(model, objs):
    num = objs.count()
    if num > 1:
        logger.debug("deleting %d matching instances of model %s" % (model._meta.name))
        objs.delete()
        return None
    elif num == 1:
        logger.debug("found single match of model %s, updating object id '%s'" % (model._meta.name, str(objs[0].id)))
        return objs[0]
    else:
        return None

def find_matching_by_source(model, source=None, source_ref=None):
    filter = {
        'source__exact': source,
        'source_ref__exact': source_ref,
    }
    objs = model.objects.filter(**filter)

    return handle_matching_set(model, objs)

def find_matching_lang(name):
    filter = Q(name__iexact=name) | Q(alt_names__icontains=name)
    objs = Language.objects.filter(filter)
    return handle_matching_set(Language, objs)
    
