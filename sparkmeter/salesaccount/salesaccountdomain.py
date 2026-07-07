# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.
"""Salesaccount domain models."""
import logging
import uuid

from flask_babel import lazy_gettext as _
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship
from sqlalchemy.sql.expression import and_, func, null, or_, select, text, true
from sqlalchemy.sql.schema import Column, ForeignKey
from sqlalchemy.types import Boolean, Float, String

from sparkmeter.config.configdict import config
from sparkmeter.database.alchemy import sql
from sparkmeter.database.sync import SYNC_CHANNEL_SALES_ACCOUNT, SYNC_GROUP_CLOUD, syncchannel
from sparkmeter.database.tables import get_table_by_name
from sparkmeter.database.types import UUIDType
from sparkmeter.exceptions import TransactionError
from sparkmeter.models import BaseDomain
from sparkmeter.transaction.transactiondomain import Transaction, Wallet

logger = logging.getLogger(__name__)


@syncchannel(SYNC_CHANNEL_SALES_ACCOUNT)
class SalesAccount(BaseDomain):

    """ A Sales Account is a collection of credit and debt wallets for a vendor.

    This is conceptually similar to a bank account where you can have several different
    underlying accounts (depoist/savings) which do their own accounting.
    """
    __tablename__ = 'sales_account'

    #: Name of the sales account, like 'Sales1'
    name = Column(String)

    #: If this account is visible in the UI and can be used to place transactions
    active = Column(Boolean, default=True)

    #: If this account is systems account
    system = Column(Boolean, default=False)

    #: If this account is global account and can be accessed on all grounds
    global_account = Column(Boolean, default=False)

    #: Default markup for transaction placed from this sales account.
    markup = Column(Float, default=0.05)

    #: The ground this sales account belongs to
    ground_id = Column(UUIDType(binary=False), ForeignKey('ground.id'),
                       nullable=True)

    #: The credit_wallet for this user, only set for vendors
    credit_wallet = relationship(
        Wallet,
        primaryjoin=("and_(foreign(SalesAccount.id) == Wallet.sales_account_id, "
                     "Wallet.wallet_type == 'credit')"),
        single_parent=True,
        cascade="all, delete-orphan")

    #: The debt_wallet for this user, only set for vendors
    debt_wallet = relationship(
        Wallet,
        primaryjoin=("and_(foreign(SalesAccount.id) == Wallet.sales_account_id, "
                     "Wallet.wallet_type == 'debt')"),
        single_parent=True,
        cascade="all, delete-orphan",
        overlaps="credit_wallet")

    #: If the balance of the credit wallet of this sales account is permitted to be negative
    negative_permitted = association_proxy(
        'credit_wallet',
        'negative_permitted',
        creator=lambda value: None)

    #: Reference to the ground
    ground = relationship("Ground")

    @classmethod
    def sync_init(cls, group):
        """Initialize sync cloud configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_CLOUD)

        if group.is_cloud():
            # FIXME: Use SQLAlchemy syntax
            group.set_subselect_router(
                "(c.external_id IN ("
                "SELECT serial FROM ground WHERE id = cast(:GROUND_ID as uuid)) OR "
                "cast(:GROUND_ID as uuid) IS NULL)"
            )

    @classmethod
    def create_empty(cls, ground=None, global_account=False, id=None):
        """
        Create an empty sales account and all sub-objects required.
        :param ground: for restricted accounts only, the ground
        :type ground: sparkmeter.ground.grounddomain.Ground
        :param global_account: if this is a global account
        :type global_account: bool
        :param id: an optional ID for the created sales account
        :type id: uuid.UUID
        :returns the newly created sales account.
        """
        params = {'ground': ground}
        if global_account:
            params['ground'] = None
        if id:  # noqa
            params['id'] = id
        self = cls(**params)
        sql.session.add(self)
        sql.session.flush()
        if global_account:
            self.markup = None
        self.global_account = global_account
        self.add_wallets()

        return self

    @classmethod
    def get_system(cls):
        """
        Get the system sales account.
        :return: the system sales account
        :rtype: SalesAccount
        """
        return cls.query.filter_by(system=True).one()

    @classmethod
    def get_by_id(cls, object_id):
        """Get the SalesACcount by the given object_id.

        :param object_id: id of the SalesAccount to get.
        :returns the SalesAccount or None if it cannot be found.
        :rtype: SalesAccount
        """
        return cls.query.get(object_id)

    @classmethod
    def get_sales_account_view(cls,
                               ground=None,
                               user=None,
                               include_system=False,
                               global_account=False):
        """Get a set of sales accounts.

        This will be used to display the list of sales accounts for users etc.
        It will return a list of dictionaries instead of SalesAccount object due to performance
        reasons. It's suitable for putting into jsonify() and display in the interface.

        By default the results will be orded by account name.

        :param include_system: whether to include the system sales account
        :param ground: restrict the sales accounts to a ground or ``None``
        :param user: restrict the sales accounts to a user or ``None``
        :param global_account:
           if True, include only global sales accounts
           if False, include only restricted sales accounts
        :returns: transaction query result
        :rtype: sqlalchemy.orm.query.Query
        """
        wallet_t = Wallet.__table__
        credit_wallet_t = wallet_t.alias('credit_wallet')
        debt_wallet_t = wallet_t.alias('debt_wallet')
        sales_account_t = get_table_by_name('sales_account')
        columns = [
            cls.active,
            cls.id,
            cls.name,
            cls.markup,
            credit_wallet_t.c.negative_permitted,
            debt_wallet_t.c.value.label('debt'),
            credit_wallet_t.c.value.label('credit'),
        ]
        joins = (
            cls.__table__
            .join(credit_wallet_t, and_(credit_wallet_t.c.sales_account_id == SalesAccount.id,
                                        credit_wallet_t.c.wallet_type == Wallet.TYPE_CREDIT))
            .join(debt_wallet_t, and_(debt_wallet_t.c.sales_account_id == SalesAccount.id,
                                      debt_wallet_t.c.wallet_type == Wallet.TYPE_DEBT))
        )
        wheres = [cls.global_account == global_account]
        group_by = None

        if not include_system:  # pragma: nocoverage
            wheres.append(sales_account_t.c.system != true())

        # A user always need explicit access to a sales account
        if user is not None:
            sales_accounts_users_t = get_table_by_name('sales_accounts_users')
            subquery = select(sales_accounts_users_t.c.sales_account_id).where(
                sales_accounts_users_t.c.user_id == user.id,
            )
            sales_account_clauses = [cls.id.in_(subquery)]
            if user.api_sales_account_id:
                sales_account_clauses.append(cls.id.in_([user.api_sales_account_id]))
            wheres.append(or_(*sales_account_clauses))

            # Restricted sales account needs that the user has access to the ground
            # which the restricted sales account belongs to.
            if not global_account:
                users_ground_t = get_table_by_name('users_grounds')
                subquery = select(users_ground_t.c.ground_id).where(
                    users_ground_t.c.user_id == user.id)
                wheres.append(cls.ground_id.in_(subquery))

        # For global accounts, calculate "X transactions ($Y) in the last 30 days"
        if global_account:
            assert not ground, "can't specify global & ground"
            transaction_t = get_table_by_name('transactions')
            group_by = columns[:]
            columns.extend([
                func.count(transaction_t.c.id).label('transaction_count'),
                func.sum(func.coalesce(transaction_t.c.amount, 0)).label('transaction_total'),
            ])
            joins = joins.outerjoin(transaction_t, and_(
                transaction_t.c.state.in_([Transaction.STATE_PROCESSED,
                                           Transaction.STATE_REVERSED]),
                transaction_t.c.created >= text("NOW() - INTERVAL '30 DAYS'"),
                or_(transaction_t.c.from_wallet_id.in_([credit_wallet_t.c.id,
                                                        debt_wallet_t.c.id]),
                    transaction_t.c.to_wallet_id.in_([credit_wallet_t.c.id,
                                                      debt_wallet_t.c.id])))
            )
        # For restricted, filter by ground and include ground name/serial.
        else:
            if ground is not None:
                wheres.append(cls.ground_id == ground.id)

            ground_t = get_table_by_name('ground')
            joins = joins.outerjoin(ground_t,
                                    ground_t.c.id == cls.ground_id)
            columns.extend([
                ground_t.c.serial.label('ground_serial'),
                ground_t.c.name.label('ground_name'),
            ])

        query = (
            select(*columns)
            .select_from(joins)
            .where(and_(*wheres))
            .order_by(cls.system.desc(), cls.name)
        )
        if group_by is not None:
            query = query.group_by(*group_by)
        return query

    @classmethod
    def is_name_unique(cls, name, skip=None):
        """Check if the name is unique.

        Check if the name passed is unique.
        :param str name: The name to check against the database
        :param skip: Optionally, an object that is ignored for uniqueness
        :returns: ``True`` if it's unique, ``False`` otherwise.
        """
        query = cls.query.filter_by(name=name)
        if skip is not None:
            query = query.filter(cls.id != skip.id)

        return query.count() == 0

    def add_wallets(self):
        """Add wallets to a sales account.

        This should be called during creating of a sales account
        """
        if not self.id:
            self.id = uuid.uuid4()

        session = self.session
        # FIXME: Replace with constraint(s)
        if session.query(Wallet).filter_by(sales_account_id=self.id).count():  # pragma: no coverage
            raise TypeError("Wallets already exists")

        logger.info("Creating wallets for sales account %s" % (self.id, ))
        wallet_types = [('credit_wallet', Wallet.TYPE_CREDIT),
                        ('debt_wallet', Wallet.TYPE_DEBT)]
        grid_id = None
        if not self.global_account:
            grid_id = self.ground.id
        for attr, wallet_type in wallet_types:
            wallet = Wallet(id=uuid.uuid4(),
                            wallet_type=wallet_type,
                            sales_account_id=self.id,
                            value=0,
                            grid_id=grid_id,
                            negative_permitted=self.global_account)
            setattr(self, attr, wallet)

    def remove(self):
        """Delete a sales account and all its transactions."""
        from sparkmeter.user.userdomain import User
        for user in User.query.filter_by(api_sales_account_id=self.id):
            user.api_sales_account = None
            sql.session.add(user)
        sql.session.delete(self.credit_wallet)
        sql.session.delete(self.debt_wallet)
        sql.session.delete(self)

    @property
    def description(self):
        """Get a description of this sales account."""
        return self.name

    @property
    def account_type(self):
        """Get an account type for this sales account"""
        if self.global_account:
            return 'global'
        else:
            return 'restricted'

    def get_wallet(self, wallet_type):
        """Get a wallet for a given wallet type.

        :raises sqlalchemy.orm.exc.NoResultFound: if no wallets are in the database.
        """
        if wallet_type == Wallet.TYPE_CREDIT:
            return self.credit_wallet
        elif wallet_type == Wallet.TYPE_DEBT:
            return self.debt_wallet

    def _check_ground_access(self, prefix):
        # Restricted sales accounts needs explicit ground access
        from sparkmeter.ground.grounddomain import Ground
        ground = Ground.get_current()
        if not config['HEROKU'] and ground != self.ground:
            message = prefix + _(u"transactions for this sales account "
                                 u"can only be placed on ground '%(ground)s'.",
                                 ground=self.ground.name)
            raise TransactionError(TransactionError.ERROR_PERMISSION_DENIED, message)

    def _check_user_access(self, user, prefix):
        # Restricted sales accounts needs explicit user access
        if self.id not in [a.id for a in user.accounts]:
            raise TransactionError(
                TransactionError.ERROR_PERMISSION_DENIED,
                prefix + _(u"user is not associated with sales account '%(sales_account)s'.",
                           sales_account=self.name))

        if self.ground_id not in [m.id for m in user.grounds]:
            raise TransactionError(
                TransactionError.ERROR_PERMISSION_DENIED,
                prefix + _(u"user is not associated with ground '%(ground)s'.",
                           ground=self.ground.name))

    def check_can_sell_from(self, user):
        """
        Checks if a user can place transactions from this sales account.

        :param user: the user to check
        :type user: User
        :raises TransactionError: if it cannot be sold from
        """
        prefix = _(u"user '%(username)s' cannot sell from sales account '%(sales_account)s': ",
                   username=user.username,
                   sales_account=self.name)

        # API Users can only sell from a sales account it is associated with
        if user.is_api():
            if user.api_sales_account is None:
                raise TransactionError(
                    TransactionError.ERROR_PERMISSION_DENIED,
                    prefix + _(u"api user is not allowed to sell electricity."))

            if self.id != user.api_sales_account_id:
                raise TransactionError(
                    TransactionError.ERROR_PERMISSION_DENIED,
                    prefix + _(u"api user can only sell to '%(sales_account)s'.",
                               sales_account=user.api_sales_account.name))

        # Global sales account does not need explicit ground permission
        if self.global_account:
            return

        self._check_ground_access(prefix)

        # Cloud should always allow, no explicit ground access needed
        if config['HEROKU']:
            return

        self._check_user_access(user, prefix)

    def check_can_sell_to(self, user):
        """
        Checks if a user can place transactions to this sales account.

        :param user: the user to check
        :type user: User
        :raises TransactionError: if it cannot be sold to
        """

        prefix = _(u"user '%(username)s' cannot sell to sales account '%(sales_account)s': ",
                   username=user.username,
                   sales_account=self.name)

        # You can never sell to global sales accounts
        if self.global_account:
            raise TransactionError(
                TransactionError.ERROR_PERMISSION_DENIED,
                prefix + _(u"selling to global sales accounts is not permitted."))

        self._check_ground_access(prefix)

        # Both operator and vendors need access to the System Sales Account to
        # be able to sell at all. API users just need global sales account access.
        if user.is_api():
            if not user.api_sales_account.global_account:
                raise TransactionError(TransactionError.ERROR_PERMISSION_DENIED,
                                       prefix + "API user is not associated with a global sales account.")
        elif SalesAccount.get_system() not in user.accounts:
            raise TransactionError(
                TransactionError.ERROR_PERMISSION_DENIED,
                prefix + _(u"user is not associated with system sales account."))

        # Operators and API users can sell to all restricted accounts
        if (config['HEROKU'] and user.is_operator()) or user.is_api():
            return

        self._check_user_access(user, prefix)

    @classmethod
    def get_accounts_by_user_ground(cls, user, ground, active_only=False):
        """
        Get accounts that this user can access for a specific ground.

        :param user: user to get accounts for
        :type: user: sparkmeter.ground.grounddomain.Ground
        :param ground: ground to get accounts for
        :type: ground: sparkmeter.ground.grounddomain.Ground
        :param active_only: `True` if only active sales accounts should be retrieved
        :type: bool
        :return: query represeting the querys
        :rtype: sqlalchemy.orm.query.Query
        """
        sales_accounts_users_t = get_table_by_name('sales_accounts_users')
        query = (cls.query
                 .filter(sales_accounts_users_t.c.sales_account_id == cls.id)
                 .filter(sales_accounts_users_t.c.user_id == user.id)
                 .filter(or_(cls.ground_id == null(),
                             cls.ground_id == ground.id, None))
                 .order_by(cls.system.desc(), cls.name)
                 )
        if active_only:
            query = query.filter(cls.active.is_(True))
        return query
