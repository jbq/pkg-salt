# -*- coding: utf-8 -*-
'''
Alex Martelli's soulution for recursive dict update from
http://stackoverflow.com/a/3233356
'''
from __future__ import absolute_import

# Import python libs
import collections
import copy
import logging
import salt.ext.six as six
from salt.utils.odict import OrderedDict
from salt.utils.serializers.yamlex \
    import merge_recursive as _yamlex_merge_recursive

log = logging.getLogger(__name__)


def update(dest, upd):
    for key, val in six.iteritems(upd):
        try:
            if isinstance(val, OrderedDict):
                klass = OrderedDict
            else:
                klass = dict
            dest_subkey = dest.get(key, klass())
        except AttributeError:
            dest_subkey = None
        if isinstance(dest_subkey, collections.Mapping) \
                and isinstance(val, collections.Mapping):
            ret = update(dest_subkey, val)
            dest[key] = ret
        elif key:
            dest[key] = upd[key]
    return dest


def merge_list(obj_a, obj_b):
    ret = {}
    for key, val in six.iteritems(obj_a):
        if key in obj_b:
            ret[key] = [val, obj_b[key]]
        else:
            ret[key] = val
    return ret


def merge_recurse(obj_a, obj_b):
    copied = copy.copy(obj_a)
    return update(copied, obj_b)


def merge_aggregate(obj_a, obj_b):
    return _yamlex_merge_recursive(obj_a, obj_b, level=1)


def merge_overwrite(obj_a, obj_b):
    for obj in obj_b:
        if obj in obj_a:
            obj_a[obj] = obj_b[obj]
    return merge_recurse(obj_a, obj_b)


def merge(obj_a, obj_b, strategy='smart', renderer='yaml'):
    if strategy == 'smart':
        if renderer == 'yamlex' or renderer.startswith('yamlex_'):
            strategy = 'aggregate'
        else:
            strategy = 'recurse'

    if strategy == 'list':
        merged = merge_list(obj_a, obj_b)
    elif strategy == 'recurse':
        merged = merge_recurse(obj_a, obj_b)
    elif strategy == 'aggregate':
        #: level = 1 merge at least root data
        merged = merge_aggregate(obj_a, obj_b)
    elif strategy == 'overwrite':
        merged = merge_overwrite(obj_a, obj_b)
    else:
        log.warning('Unknown merging strategy \'{0}\', '
                    'fallback to recurse'.format(strategy))
        merged = merge_recurse(obj_a, obj_b)

    return merged
