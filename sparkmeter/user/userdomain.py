# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""User domain."""

import logging
import uuid

from flask_security import RoleMixin, SQLAlchemyUserDatastore, UserMixin
from flask_security.utils import hash_password
from sqlalchemy.orm import backref, relationship
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import not_, select, true
from sqlalchemy.sql.schema import Column, ForeignKey
from sqlalchemy.sql.sqltypes import Boolean, String

from sparkmeter.config.configdict import config
from sparkmeter.database.alchemy import sql
from sparkmeter.database.expressions import JSONAgg
from sparkmeter.database.sync import SYNC_CHANNEL_USER, SYNC_GROUP_CLOUD, syncchannel
from sparkmeter.database.types import UUIDType
from sparkmeter.misc.passwordutils import generate_password
from sparkmeter.misc.uuidutils import as_uuid
from sparkmeter.models import BaseDomain
from sparkmeter.salesaccount.salesaccountdomain import SalesAccount

logger = logging.getLogger(__name__)


@syncchannel(SYNC_CHANNEL_USER)
class RolesUsers(BaseDomain):
    """User Role mapping table."""

    # FIXME: Rename this to users_roles
    __tablename__ = "roles_users"

    #: Role reference
    role_id = Column(UUIDType(binary=False), ForeignKey("role.id"), nullable=False)

    #: User reference
    user_id = Column(UUIDType(binary=False), ForeignKey("user.id"), nullable=False)

    @classmethod
    def sync_init(cls, group):
        """Initialize sync cloud configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_CLOUD)
        group.set_key_columns(cls.user_id, cls.role_id)


@syncchannel(SYNC_CHANNEL_USER)
class Role(BaseDomain, RoleMixin):
    """User Role table."""

    __tablename__ = "role"

    #: Name of the role, must be unique
    name = Column(String(80), unique=True)

    #: Description of the role
    description = Column(String(255))

    @classmethod
    def sync_init(cls, group):
        """Initialize sync cloud configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_CLOUD)

    @classmethod
    def get_by_name(cls, name):
        """Get a role given a name.

        :param name: the name of the role
        :returns: the Role
        :raises NoResultFound: if there's no role with the specified name.
        """
        return Role.query.filter_by(name=name).one()

    def __str__(self):
        """Role object display name."""
        return self.name


@syncchannel(SYNC_CHANNEL_USER)
class SalesAccountsUsers(BaseDomain):
    """User Role mapping table."""

    # FIXME: Rename this to users_sales_accounts
    __tablename__ = "sales_accounts_users"

    #: SalesAccount this mapping applies to
    sales_account_id = Column(UUIDType(binary=False), ForeignKey("sales_account.id"), nullable=False)

    #: User this mapping applies to
    user_id = Column(UUIDType(binary=False), ForeignKey("user.id"), nullable=False)

    #: User reference
    user = relationship("User")

    #: SalesAccount reference
    sales_account = relationship("SalesAccount")

    @classmethod
    def sync_init(cls, group):
        """Initialize sync cloud configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_CLOUD)
        group.set_key_columns(cls.user_id, cls.sales_account_id)
        # FIXME: Only sync over sales accounts that exists in the specific ground

    @classmethod
    def get_default_id(cls, context):
        """Get the default id for a SalesAccountUsers object."""
        return as_uuid(context.current_parameters["sales_account_id"], context.current_parameters["user_id"])


@syncchannel(SYNC_CHANNEL_USER)
class UsersGrounds(BaseDomain):
    """Ground Users mapping table."""

    __tablename__ = "users_grounds"

    #: Ground this mapping applies to
    ground_id = Column(UUIDType(binary=False), ForeignKey("ground.id"), nullable=False)

    #: User this mapping applies to
    user_id = Column(UUIDType(binary=False), ForeignKey("user.id"), nullable=False)

    #: User reference
    user = relationship("User")

    #: Ground reference
    ground = relationship("Ground")

    @classmethod
    def sync_init(cls, group):
        """Initialize sync cloud configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_CLOUD)
        group.set_key_columns(cls.user_id, cls.ground_id)

    @classmethod
    def get_default_id(cls, context):
        """Get the default id for this table."""
        return as_uuid(context.current_parameters["user_id"], context.current_parameters["ground_id"])


@syncchannel(SYNC_CHANNEL_USER)
class User(BaseDomain, UserMixin):
    """User table."""

    __tablename__ = "user"

    #: The username, used mainly by flask-security
    username = Column(String(100))

    #: Password, when logging in via the user interface
    password = Column(String(255))

    #: Email, token to use when logging in via the interface
    email = Column(String(255))

    #: Uniquifier for Flask-Security-Too 4.0+ compatibility
    fs_uniquifier = Column(String(255), unique=True, nullable=False, default=lambda: uuid.uuid4().hex)

    #: ID of the user in the cloud portal
    portal_id = Column(UUIDType(binary=False), nullable=True, unique=True)

    #: If this user is active and can log in, used by flask-security.
    active = Column(Boolean, default=True)

    #: Current locale for the user, used by translation and localization
    locale = Column(String, default="en_US")

    # Sales account that is use to place transactions via the API, only for api users
    api_sales_account_id = Column(
        UUIDType(binary=False),
        ForeignKey("sales_account.id"),
        nullable=True,
    )

    #: If this user has access to all sales accounts
    account_all_access = Column(Boolean, default=False, nullable=False)

    #: If this user has access to all grounds
    ground_all_access = Column(Boolean, default=False, nullable=False)

    #: Roles that this user is assigned to
    roles = relationship(
        "Role", secondary=RolesUsers.__table__, backref=backref("users", lazy="dynamic"), order_by="Role.name"
    )

    #: List of sales account this user has access to
    accounts = relationship(
        "SalesAccount",
        secondary=SalesAccountsUsers.__table__,
        backref=backref("users", lazy="dynamic", overlaps="sales_account,user"),
        order_by=(SalesAccount.system.desc(), SalesAccount.name),
        overlaps="sales_account,user",
    )

    #: List of grounds this user has access to
    grounds = relationship(
        "Ground",
        secondary=UsersGrounds.__table__,
        backref=backref("users", lazy="dynamic", overlaps="ground,user"),
        order_by="Ground.name",
        overlaps="ground,user",
    )

    #: Reference to the sales account for this user, only for api users
    api_sales_account = relationship("SalesAccount")  # type: SalesAccount

    @classmethod
    def sync_init(cls, group):
        """Initialize sync cloud configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_CLOUD)

    @classmethod
    def create_empty(cls, role):
        """
        Create an empty user and all sub-objects required.

        :returns the newly created user.
        """
        self = cls()
        self.locale = config.get_current_locale()
        self.roles = [Role.get_by_name(role)]
        self.fs_uniquifier = uuid.uuid4().hex
        return self

    @classmethod
    def get_with_all_account_access(cls):
        """Get all users that has all access to accounts."""
        return cls.query.filter_by(account_all_access=True)

    @classmethod
    def get_with_all_ground_access(cls):
        """Get all users that has all access to grounds."""
        return cls.query.filter_by(ground_all_access=True)

    @classmethod
    def get_by_name(cls, username):
        """Get a user given a username.

        :returns: the user, or None if one does not exist.
        :rtype: User
        """
        try:
            user = cls.query.filter_by(username=username).one()
        except NoResultFound:
            user = None
        return user

    @classmethod
    def get_user_view(cls, role):
        """Get a set of users.

        This will be used to display the list of users.
        It will return a list of dictionaries instead of User object due to performance
        reasons. It's suitable for putting into jsonify() and display in the interface.

        By default the results will be orded by username.

        :param role: list only roles for this role
        :returns: user query result
        """
        sales_account_t = SalesAccount.__table__
        sales_accounts_users_t = SalesAccountsUsers.__table__

        json_agg = JSONAgg(
            [sales_account_t.c.id, sales_account_t.c.name],
            order_by=[sales_account_t.c.system.desc(), sales_account_t.c.name],
        )
        columns = [
            cls.id,
            cls.active,
            cls.email,
            cls.username,
            json_agg.label("accounts"),
        ]
        joins = (
            cls.__table__.outerjoin(sales_accounts_users_t, sales_accounts_users_t.c.user_id == cls.id)
            .outerjoin(
                sales_account_t,
                sales_account_t.c.id.in_(
                    [sales_accounts_users_t.c.sales_account_id, cls.api_sales_account_id]
                ),
            )
            .join(RolesUsers, RolesUsers.user_id == cls.id)
            .join(Role, RolesUsers.role_id == Role.id)
        )
        wheres = []
        if role is not None:
            wheres.append(Role.name == role)

        query = (
            select(*columns)
            .select_from(joins)
            .where(*wheres)
            .group_by(cls.id, cls.active, cls.email, cls.username)
            .order_by(cls.username)
        )
        return query

    def remove(self):
        """Delete a user and all its transactions."""
        logger.info("Deleting user {}".format(self.username))
        from sparkmeter.transaction.transactiondomain import Transaction, TransactionView

        for trans_view, _ in TransactionView.get_transaction_view(user=self):
            trans = Transaction.query.get(trans_view.id)
            sql.session.delete(trans)

        self.accounts = []
        self.grounds = []
        sql.session.delete(self)

    def is_vendor(self):
        """Return if the user is a vendor user."""
        return self.has_role("vendor")

    def is_operator(self):
        """Return if the user is an operator user."""
        return self.has_role("operator")

    def is_api(self):
        """Return if the user is an api user."""
        return self.has_role("api")

    def generate_password(self):
        """Generate a new random password for this user."""
        self.password = hash_password(generate_password(length=16))
        if not self.fs_uniquifier:
            self.fs_uniquifier = uuid.uuid4().hex

    @property
    def transaction_permission(self):
        """If this user has permission to place transactions."""
        return bool(self.api_sales_account)

    @transaction_permission.setter
    def transaction_permission(self, value):
        """Set this user has permission to place transactions ."""
        if not value:
            self.api_sales_account = None

    @classmethod
    def get_login_users(cls):
        """Get all users that can login."""
        return (
            cls.query.join(RolesUsers, RolesUsers.user_id == User.id)
            .join(Role, RolesUsers.role_id == Role.id)
            .filter(not_(Role.name.in_(["api"])))
            .filter(User.active == true())
            .order_by(User.username)
        )

    @classmethod
    def is_email_unique(cls, email):
        """Check if the email is unique.

        Check if the email passed is unique.
        :param str email: The email address to check against the database
        :returns: ``True`` if it's unique, ``False`` otherwise.
        """
        query = sql.session.query(User).filter_by(email=email)
        return query.count() == 0

    @classmethod
    def is_username_unique(cls, username):
        """Check if the username is unique.

        Check if the username passed is unique.
        :param str username: The username to check against the database
        :returns: ``True`` if it's unique, ``False`` otherwise.
        """
        query = sql.session.query(User).filter_by(username=username)
        return query.count() == 0

    def __str__(self):
        """User display name."""
        return self.username


class CloudPortalUserDatastore(SQLAlchemyUserDatastore):
    """Wrap the SQLAlchemyUserDatastore with cloud-portal awareness.

    This must be able to support the SSO shared session cookie in addition to
    the traditional local-account method. Flask-Login requires that the ID be
    stored under the `user_id` key in the session cookie, so we have adopted
    the convention of prefixing cloud portal IDs with a dollar sign. e.g.,

    portal_user.id = UUID(0399480e-318a-4ee3-b125-65d08308880e)
    user_id = f"${portal_user.id}"
    """

    def find_user(self, **kwargs):
        """Find the user with the given attributes."""
        # Start: Block copied from SQLAlchemyUserDatastore.find_user()
        query = self.user_model.query
        if hasattr(self.user_model, "roles"):
            from sqlalchemy.orm import joinedload

            query = query.options(joinedload(self.user_model.roles))
        # End: Block copied from SQLAlchemyUserDatastore.find_user()

        # Handle Flask-Security case_insensitive parameter
        case_insensitive = kwargs.pop("case_insensitive", False)

        id_ = kwargs.get("id")
        # If the session user ID is a portal ID, strip the prefix and alter the query
        if id_ and isinstance(id_, str) and id_.startswith("$"):
            logger.debug("Cloud portal user detected, remapping query")
            kwargs["portal_id"] = id_[1:]
            del kwargs["id"]

        # Apply case-insensitive matching for string fields if requested
        if case_insensitive:
            from sqlalchemy import func

            conditions = []
            for key, value in list(kwargs.items()):
                if key in ("username", "email") and isinstance(value, str):
                    # Use case-insensitive matching for username and email
                    field = getattr(self.user_model, key)
                    conditions.append(func.lower(field) == func.lower(value))
                    del kwargs[key]

            # Apply remaining kwargs as normal filter_by
            if kwargs:
                query = query.filter_by(**kwargs)

            # Apply case-insensitive conditions
            for condition in conditions:
                query = query.filter(condition)

            return query.first()
        else:
            return query.filter_by(**kwargs).first()


user_datastore = CloudPortalUserDatastore(sql, User, Role)
