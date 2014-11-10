# -*- coding: utf-8 -*-
'''
Management of PostgreSQL extensions (e.g.: postgis)
===================================================

The postgres_extensions module is used to create and manage Postgres extensions.

.. code-block:: yaml

    adminpack:
      postgres_extension.present
'''

# Import Python libs
import logging

# Import salt libs
from salt.modules import postgres

log = logging.getLogger(__name__)


def __virtual__():
    '''
    Only load if the postgres module is present
    '''
    return 'postgres.create_extension' in __salt__


def present(name,
            if_not_exists=None,
            schema=None,
            ext_version=None,
            from_version=None,
            user=None,
            maintenance_db=None,
            db_password=None,
            db_host=None,
            db_port=None,
            db_user=None):
    '''
    Ensure that the named extension is present with the specified privileges

    name
        The name of the extension to manage

    if_not_exists
        Add a if_not_exists switch to the ddl statement

    schema
        Schema to install the extension into

    from_version
        Old extension version if already installed

    ext_version
        version to install

    user
        System user all operations should be performed on behalf of

    maintenance_db
        Database to act on

    db_user
        database username if different from config or default

    db_password
        user password if any password for a specified user

    db_host
        Database host if different from config or default

    db_port
        Database port if different from config or default
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': 'Extension {0} is already present'.format(name)}
    db_args = {
        'maintenance_db': maintenance_db,
        'runas': user,
        'host': db_host,
        'user': db_user,
        'port': db_port,
        'password': db_password,
    }
    # check if extension exists
    mode = 'create'
    mtdata = __salt__['postgres.create_metadata'](
        name,
        schema=schema,
        ext_version=ext_version,
        **db_args)

    # The extension is not present, install it!
    toinstall = postgres._EXTENSION_NOT_INSTALLED in mtdata
    if toinstall:
        mode = 'install'
    toupgrade = False
    if postgres._EXTENSION_INSTALLED in mtdata:
        for flag in [
            postgres._EXTENSION_TO_MOVE,
            postgres._EXTENSION_TO_UPGRADE
        ]:
            if flag in mtdata:
                toupgrade = True
                mode = 'upgrade'
    if __opts__['test']:
        ret['result'] = None
        if mode:
            ret['comment'] = 'Extension {0} is set to be {1}ed'.format(
                name, mode).replace('eed', 'ed')
        return ret
    cret = None
    if toinstall or toupgrade:
        cret = __salt__['postgres.create_extension'](
            name=name,
            if_not_exists=if_not_exists,
            schema=schema,
            ext_version=ext_version,
            from_version=from_version,
            **db_args)
    if cret:
        ret['comment'] = 'The extension {0} has been {1}ed'.format(name, mode)
    elif cret is not None:
        ret['comment'] = 'Failed to {1} extension {0}'.format(name, mode)
        ret['result'] = False
    else:
        ret['result'] = True
    return ret


def absent(name,
           if_exists=None,
           restrict=None,
           cascade=None,
           user=None,
           maintenance_db=None,
           db_password=None,
           db_host=None,
           db_port=None,
           db_user=None):
    '''
    Ensure that the named extension is absent

    name
        Extension name of the extension to remove

    cascade
        Drop on cascade

    if_exists
        Add if exist slug

    restrict
        Add restrict slug

    maintenance_db
        Database to act on

    user
        System user all operations should be performed on behalf of

    db_user
        database username if different from config or default

    db_password
        user password if any password for a specified user

    db_host
        Database host if different from config or default

    db_port
        Database port if different from config or default
    '''
    ret = {'name': name,
           'changes': {},
           'result': True,
           'comment': ''}
    db_args = {
        'maintenance_db': maintenance_db,
        'runas': user,
        'host': db_host,
        'user': db_user,
        'port': db_port,
        'password': db_password,
    }
    # check if extension exists and remove it
    exists = __salt__['postgres.is_installed_extension'](name, **db_args)
    if exists:
        if __opts__['test']:
            ret['result'] = None
            ret['comment'] = 'Extension {0} is set to be removed'.format(name)
            return ret
        if __salt__['postgres.drop_extension'](name,
                                               if_exists=if_exists,
                                               restrict=restrict,
                                               cascade=cascade,
                                               **db_args):
            ret['comment'] = 'Extension {0} has been removed'.format(name)
            ret['changes'][name] = 'Absent'
            return ret
        else:
            ret['result'] = False
            ret['comment'] = 'Extension {0} failed to be removed'.format(name)
            return ret
    else:
        ret['comment'] = 'Extension {0} is not present, so it cannot ' \
                         'be removed'.format(name)

    return ret
