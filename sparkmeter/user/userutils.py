# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
"""User utilities."""

from zope.component import provideUtility, queryUtility

from sparkmeter.interface import ICurrentUser


def get_current_user():
    # type: () -> Optional[User]
    """Get the currently logged in user or None."""
    user_id = queryUtility(ICurrentUser)
    if user_id is not None:
        from sparkmeter.user.userdomain import User

        return User.get_by_id(user_id)


def set_current_user(user):
    # type: (User) -> None
    """Set the current user."""
    if user is not None and hasattr(user, "id"):
        utility = user.id
    else:
        utility = None
    provideUtility(utility, ICurrentUser)
