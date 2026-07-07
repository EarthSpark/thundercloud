# -*- coding: utf-8 -*-
# Copyright © 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""User permissions."""

import functools
import http.client
from builtins import object

from flask import abort
from flask_security import current_user

_permissions = {}


def _get_permission(entity):
    permission = _permissions.get(entity)
    if permission is None:  # pragma nocoverage
        raise NotImplementedError("Missing permission for entity %s" % (entity, ))
    return permission


def _register_permission(cls):
    if cls.entity is None:  # pragma nocoverage
        raise TypeError("%s.entity cannot be None" % (cls.__name__, ))
    _permissions[cls.entity] = cls()


class Permission(object):

    """Abstract Permission class, all permissions should subclass for this."""

    entity = None

    def can_view(self):  # pragma nocoverage
        """Check if a currently logged in user can view this permission type."""
        raise NotImplementedError(type(self).__name__ + '.can_view')

    def can_edit(self):  # pragma nocoverage
        """Check if a currently logged in user can edit this permission type."""
        raise NotImplementedError(type(self).__name__ + '.can_edit')

    def can_add(self):  # pragma nocoverage
        """Check if a currently logged in user can add this permission type."""
        raise NotImplementedError(type(self).__name__ + '.can_add')


@_register_permission
class _MeterPermission(Permission):

    entity = 'meter'

    def can_edit(self):
        # Only operators can edit
        return current_user.has_role('operator')

    def can_add(self):  # pragma nocoverage
        return self.can_edit()

    def can_view(self):  # pragma nocoverage
        return True


@_register_permission
class _GroundPermission(Permission):

    entity = 'ground'

    def can_edit(self):
        # Only operators can edit
        return current_user.has_role('operator')  # pragma nocoverage

    def can_view(self):
        return current_user.has_role('operator')   # pragma nocoverage


@_register_permission
class _TariffPermission(Permission):

    entity = 'tariff'

    def can_edit(self):
        # Only operators can edit
        return current_user.has_role('operator')

    def can_add(self):
        return self.can_edit()

    def can_view(self):
        return current_user.has_role('operator')


@_register_permission
class _TransactionPermission(Permission):

    entity = 'transaction'

    def can_add(self):
        return current_user.has_role('operator')


@_register_permission
class _TransactionSourcePermission(Permission):

    entity = 'transaction-source'

    def can_edit(self):
        # Only operators can edit
        return current_user.has_role('operator')  # pragma nocoverage

    def can_add(self):
        return self.can_edit()

    def can_view(self):
        return current_user.has_role('operator')


@_register_permission
class _UserPermission(Permission):

    entity = 'user'

    def can_edit(self):
        # Only operators can edit
        return current_user.has_role('operator')

    def can_add(self):  # pragma nocoverage
        return self.can_edit()

    def can_view(self):
        return current_user.has_role('operator')


@_register_permission
class _SalesAccountPermission(Permission):

    entity = 'sales-account'

    def can_add(self):
        # Only operators can edit
        return current_user.has_role('operator')

    def can_edit(self):  # pragma nocoverage
        return self.can_add()

    def can_view(self):
        return current_user.has_role('operator') or current_user.has_role('vendor')


@_register_permission
class _VendorPermission(Permission):

    entity = 'vendor'

    def can_view(self):  # pragma nocoverage
        return True


def can_view(entity):
    """Check if a currently logged in user can view this permission type."""
    return _get_permission(entity).can_view()


def can_edit(entity):
    """Check if a currently logged in user can edit this permission type."""
    return _get_permission(entity).can_edit()


def can_add(entity):
    """Check if a currently logged in user can add this permission type."""
    return _get_permission(entity).can_add()


def register_functions(app):
    """Register all functions here so they can be used in jinja templates."""
    app.jinja_env.globals.update(can_view=can_view,
                                 can_edit=can_edit,
                                 can_add=can_add)


class verify_permission(object):

    """A decorator that can be used to verify the permission of view function."""

    def __init__(self, entity, perm, status=http.client.NOT_FOUND):
        """Verify the permission for a specific permission for an entity.

        This will call flask' abort function if the permission is not allowed.

        :param entity: the entity we want to check
        :param perm: permission to check for; add/edit or view
        :param status: the status that should be sent, defaults to NOT_FOUND
        """
        if perm == 'add':
            check_func = can_add
        elif perm == 'edit':
            check_func = can_edit
        elif perm == 'view':
            check_func = can_view
        else:  # pragma: nocoverage
            raise NotImplementedError((entity, perm))

        self.entity = entity
        self.perm = perm
        self.status = status
        self.check_func = check_func

    def __call__(self, func):
        """The actual decorator function."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not self.check_func(self.entity):
                abort(self.status)
            return func(*args, **kwargs)

        return wrapper
