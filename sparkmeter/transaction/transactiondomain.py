# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
"""Transaction and transaction source domain models."""
import datetime
import logging

from flask_babel import lazy_gettext as _
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.sql import text
from sqlalchemy.sql.expression import and_, distinct, func, or_
from sqlalchemy.sql.schema import CheckConstraint, Column, ForeignKey, UniqueConstraint
from sqlalchemy.types import Boolean, DateTime, Float, String

from sparkmeter.database.alchemy import sql
from sparkmeter.database.columns import JSONString
from sparkmeter.database.sync import (SYNC_CHANNEL_TRANSACTION, SYNC_CHANNEL_WALLET,
                                      SYNC_GROUP_CLOUD, SYNC_GROUP_GROUND, syncchannel)
from sparkmeter.database.tables import get_table_by_name
from sparkmeter.database.types import ChoiceType, UUIDType
from sparkmeter.event.eventdomain import Event
from sparkmeter.exceptions import TransactionError
from sparkmeter.models import BaseDomain, BaseView
from sparkmeter.snapshot.snapshotdomain import Snapshot

logger = logging.getLogger(__name__)


@syncchannel(SYNC_CHANNEL_WALLET)
class Wallet(BaseDomain):

    """Wallet model.

    A Wallet is a balance, a type: credit/debt or plan and a setting
    controlling if balance is allowed to go negative.

    It also contains a reference to the owner of the Wallet, either a
    ground, meter or sales account.
    This is conceptually similar to a deposit/savings account.
    """

    __tablename__ = 'wallet'
    __table_args__ = (
        # one of meter/ground/sales_account needs to be set
        CheckConstraint('meter_id IS NOT NULL OR '
                        'sales_account_id IS NOT NULL',
                        name='wallet_references_not_null'),
        # one of meter/ground/sales_account needs to be unset
        CheckConstraint('meter_id IS NULL OR '
                        'sales_account_id IS NULL',
                        name='wallet_references_one_null'),
        # Can only be one wallet of each type per meter/ground/sales_account
        UniqueConstraint('meter_id', 'sales_account_id', 'wallet_type',
                         name='wallet_type_unique'),
    )

    TYPE_CREDIT = u'credit'
    TYPE_DEBT = u'debt'
    TYPE_PLAN = u'plan'
    TYPES = [TYPE_CREDIT, TYPE_DEBT, TYPE_PLAN]

    #: The ground where this wallet was created, this is used by syncing.
    #: This is always set, if you want to get the system credit/debt wallets for a ground,
    #: you need to use .ground_id instead.
    grid_id = Column(
        UUIDType(binary=False),
        ForeignKey('ground.id', name='wallet_grid_id_fkey', use_alter=True),
        nullable=True,
    )

    # Note: Only one of the following 3 fields will have a value
    # depending on which object this wallet belongs to

    #: The id of the meter this wallet belongs to or None
    meter_id = Column(
        UUIDType(binary=False),
        nullable=True
    )

    #: The id of the sales account this wallet belongs to or None
    sales_account_id = Column(
        UUIDType(binary=False),
        # FIXME: This should be a foreign key, but factory boy does not like that
        # ForeignKey('sales_account.id', name='wallet_sales_account_id_fkey'),
        nullable=True
    )

    #: string (credit/debt/plan)
    wallet_type = Column(String, nullable=False)

    #: balance of this wallet, as a floating point number
    value = Column(Float, default=0.0, nullable=False)

    #: if a negative balance is permitted for this account
    negative_permitted = Column(Boolean, default=False, nullable=False)

    #: The Ground this wallet was created in, used by syncing
    grid = relationship(
        'Ground',
        foreign_keys=[grid_id],
        passive_deletes=True,
        post_update=True,
    )

    #: The meter this wallet belongs to, or None
    meter = relationship(
        'Meter',
        uselist=False,
        primaryjoin="foreign(Wallet.meter_id) == Meter.id",
        single_parent=True,
        cascade='all, delete-orphan',
        passive_deletes=True,
        post_update=True,
    )  # type: Meter

    #: If this Wallet belongs to a User, the user it belongs to
    sales_account = relationship(
        'SalesAccount',
        uselist=False,
        primaryjoin="foreign(Wallet.sales_account_id) == SalesAccount.id",
        single_parent=True,
        cascade='all, delete-orphan',
        passive_deletes=True,
        post_update=True,
    )  # type: SalesAccount

    @classmethod
    def sync_init(cls, group):
        """Initialize sync cloud configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_GROUND)
        if group.is_cloud():
            # FIXME: Use SQLAlchemy syntax
            group.set_subselect_router(
                "(c.external_id IN ("
                "SELECT serial FROM ground WHERE id = cast(:GRID_ID as uuid)) OR "
                "cast(:GRID_ID as uuid) IS NULL)"
            )

    def request_zero(self):
        """Initiate a zeroing action for this wallet."""
        event = Event.create(Event.TYPE_CUSTOMER_WALLET_ZERO_REQUESTED, obj=self)
        self.session.add(event)
        return event


@syncchannel(SYNC_CHANNEL_TRANSACTION)
class TransactionSource(BaseDomain):

    """TransactionSource Postgres SQLAlchemy Model."""

    # FIXME: Rename this to transaction_source
    __tablename__ = 'transaction_sources'

    name = Column(String, info={'label': _('Name')})
    monetary = Column(Boolean, info={'label': _('Monetary')})
    transaction_metadata = Column(JSONString, info={'label': _('Metadata')})
    transactions = relationship("Transaction", info={'label': _('Transactions')})

    #: The name of the bonus transaction source
    BONUS = 'bonus'

    #: The name of the cash transaction source
    CASH = 'cash'

    @classmethod
    def sync_init(cls, group):
        """Initialize sync cloud configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_CLOUD)

    @classmethod
    def get_by_name(cls, name):
        """Get a transaction source given a name.

        :param name: name of the source.
        :returns: the source or ``None``.
        """
        return cls.query.filter_by(name=name).scalar()


@syncchannel(SYNC_CHANNEL_TRANSACTION)
class Transaction(BaseDomain):

    """Transaction Postgres SQLAlchemy Model."""

    # FIXME: Rename this to transaction
    __tablename__ = 'transactions'

    #: This transaction has been created by a user
    ORIGIN_USER = 'user'

    #: This transaction has been created by the system (bonus for instance)
    ORIGIN_SYSTEM = 'system'

    #: This transaction has been created via a reversal operation
    ORIGIN_REVERSAL = 'reversal'

    #: This transaction has been created via a wallet zeroing operation
    ORIGIN_ZEROING = 'zeroing'

    #: If this transaction is pending
    STATE_PENDING = 'pending'

    #: If this transaction has been processed
    STATE_PROCESSED = 'processed'

    #: If this transaction had an error during processing
    STATE_ERROR = 'error'

    #: If this transaction has been reversed
    STATE_REVERSED = 'reversed'

    #: The ground this transaction belongs to
    ground_id = Column(UUIDType(binary=False), ForeignKey('ground.id'),
                       nullable=False)

    #: The user performing the action
    user_id = Column(UUIDType(binary=False), ForeignKey('user.id'),
                     nullable=False)

    #: When this transaction was created
    created = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    #: The transaction amount, how much is transferred between the parties
    amount = Column(Float, default=0, info={'label': _('Amount')})

    # FIXME: Replace with a normal String column.
    #: Account type, either credit or debt
    acct_type = Column(
        ChoiceType([
            (u'credit', _('Credit')),
            (u'debt', _('Debt')),
        ]),
        info={'label': _('Type')}
    )

    #: Wallet which is sending (from) the transaction
    from_wallet_id = Column(
        UUIDType(binary=False), ForeignKey('wallet.id'), info={'label': _('From')})

    #: Wallet which is receiving (to) the transaction
    to_wallet_id = Column(
        UUIDType(binary=False), ForeignKey('wallet.id'), info={'label': _('To')})

    #: For bonus transactions, a reference to the transaction the bonuses was applied to
    #: For reversal transactions, which transaction it reverses
    reference_id = Column(
        UUIDType(binary=False), ForeignKey('transactions.id'), info={'label': _('Reference')})

    #: An identifier for a transaction in an external system
    external_id = Column(String, info={'label': _('External ID')})

    #: Description of the transaction
    memo = Column(String(300), info={'label': _('Memo')})

    source_id = Column(
        UUIDType(binary=False), ForeignKey('transaction_sources.id'), info={'label': _('Source')})

    #: Error message in case the processing of this transaction caused an error
    error = Column(String, default=None, info={'label': _('Processing Error')})

    #: The state of this transaction, PENDING/PROCESSED/ERROR/REVERSED
    state = Column(String, nullable=False, default=STATE_PENDING)

    #: When this transaction was marked as processed
    processed_timestamp = Column(DateTime, default=None)

    #: When this transaction was marked as reversed
    reversed_timestamp = Column(DateTime, default=None)

    #: When this transaction was marked as errored
    errored_timestamp = Column(DateTime, default=None)

    #: Where does this transaction originate, user/system/reverse
    origin = Column(String, nullable=False, default=ORIGIN_USER)

    #: Reference to the transaction source
    source = relationship("TransactionSource", foreign_keys=[source_id], overlaps="transactions")

    #: Reference to the wallet that is sending(to) money
    to_wallet = relationship("Wallet", foreign_keys=[to_wallet_id])  # type: Wallet

    #: Reference to the wallet that is receiving(from) money
    from_wallet = relationship("Wallet", foreign_keys=[from_wallet_id])  # type: Wallet

    #: Reference to the child/sub transactions
    children = relationship("Transaction", info={'label': _('Children')})

    #: Reference to the ground
    ground = relationship("Ground")

    #: Reference to the user
    user = relationship("User")

    #: A snapshot of the to_wallet holder
    to_snapshot_id = Column(ForeignKey('snapshot.id'), nullable=True)

    #: A snapshot of the from_wallet holder
    from_snapshot_id = Column(ForeignKey('snapshot.id'), nullable=True)

    #: Reference to the to_wallet snapshot
    to_snapshot = relationship('Snapshot', foreign_keys=[to_snapshot_id])  # type: Snapshot

    #: Reference to the from_wallet snapshot
    from_snapshot = relationship('Snapshot', foreign_keys=[from_snapshot_id])  # type: Snapshot

    @classmethod
    def sync_init(cls, group):
        """Initialize sync cloud configuration for this table."""
        group.set_conflict_winner(SYNC_GROUP_GROUND)
        if group.is_cloud():
            ground_t = get_table_by_name('ground')
            group.set_column_router("external_data=:EXTERNAL_ID")
            group.set_external_select(
                ground_t.c.id == group.format_trigger_attr(cls.ground_id),
            )

    @property
    def status_text(self):
        """Transaction status as a text string."""
        if self.state == Transaction.STATE_PROCESSED:
            status = _('Processed')
        elif self.state == Transaction.STATE_ERROR:
            status = _('Error')
        elif self.state == Transaction.STATE_REVERSED:
            status = _('Reversed')
        elif self.state == Transaction.STATE_PENDING:
            status = _('Not processed')
        else:
            raise NotImplementedError(self.state)
        return status

    @classmethod
    def get_unprocessed(cls, ground):
        """Get all unprocessed transactions.
        :param ground: the ground transactions should be tied to
        :type ground: Ground
        :returns: a list of transactions
        :rtype: List[Transaction]
        """
        return cls.query.filter_by(ground=ground, state=Transaction.STATE_PENDING).all()

    @classmethod
    def get_by_id(cls, object_id):
        """
        Get the object by the given object_id.
        :param object_id: the object id for the transcation to fetch
        :type object_id: UUID
        :returns the transaction with the specified id
        :rtype: Transaction
        :raises NoResultFound: if no transaction could be found
        """
        return cls.query.get(object_id)

    @classmethod
    def get_by_external_id(cls, external_id):
        """
        Get a transaction given an external_id.
        :returns: a Transaction or None
        :rtype: Optional[Transaction]
        """
        return cls.query.filter_by(external_id=external_id).scalar()

    @classmethod
    def get_by_id_or_external_id(cls, id_):
        """
        Get a transaction given an identifier that's either our ID or an external ID.
        :returns: a Transaction or None
        :rtype: Optional[Transaction]
        """
        filters = [cls.external_id == str(id_)]
        converter = UUIDType(binary=False)
        try:
            converter.coercion_listener(None, id_, None, None)
            # The ID is a UUID, allow querying against the ID field
            filters.append(cls.id == id_)
        except Exception:
            pass  # The ID isn't a UUID, don't query against the ID field
        txs = cls.query.filter(or_(*filters)).all()
        if len(txs) == 0:
            raise NoResultFound()
        elif len(txs) == 1:
            return txs[0]
        else:  # Multiple results found
            try:
                # Try returning the result with an internal ID
                return next(tx for tx in txs if tx.id == id_)
            except StopIteration:  # None of the results had an internal ID
                raise MultipleResultsFound("Multiple transactions with external ID {} found".format(id_))

    @classmethod
    def get_by_tariff_period(cls, tariff, ground, start, end):
        """Summarize transaction based on a tariff and period.

        :param tariff: the tariff
        :type tariff: sparkmeter.tariff.tariffdomain.Tariff
        :param ground: the ground
        :type ground: sparkmeter.ground.grounddomain.Ground
        :param start: start of the period
        :param end: end of the period
        :returns: a resultset sequence with these attributes:
           :total_amount: sum of all transactions for the period
           :transaction_count: number of transactions
        """
        wallet_t = Wallet.__table__
        meter_t = get_table_by_name('meter')
        meter_billing_t = get_table_by_name('meter_billing')
        tariff_t = get_table_by_name('tariff')

        from_wallet = wallet_t.alias('fw')
        from_meter = meter_t.alias('fw_meter')
        from_meter_billing = meter_billing_t.alias('fw_meter_billing')
        from_tariff = tariff_t.alias('fw_tariff')

        to_wallet = wallet_t.alias('tw')
        to_meter = meter_t.alias('tw_meter')
        to_tariff = tariff_t.alias('tw_tariff')
        to_meter_billing = meter_billing_t.alias('tw_meter_billing')

        query = (
            cls.query
            .filter(or_(from_tariff.c.id == tariff.id,
                        to_tariff.c.id == tariff.id))
            .filter(and_(cls.created >= start,
                         cls.created < end))
            .filter(or_(cls.state == Transaction.STATE_PROCESSED,
                        cls.state == Transaction.STATE_REVERSED))
            .with_entities(
                func.sum(cls.amount).label('total_amount'),
                func.count(distinct(cls.id).label('transaction_count')),
            )
            .join(from_wallet, from_wallet.c.id == cls.from_wallet_id)
            .outerjoin(from_meter, and_(from_meter.c.id == from_wallet.c.meter_id,
                                        from_meter.c.ground_id == ground.id))
            .outerjoin(from_meter_billing, from_meter_billing.c.meter_id == from_meter.c.id)
            .outerjoin(from_tariff, from_tariff.c.id == from_meter_billing.c.tariff_id)
            .join(to_wallet, to_wallet.c.id == cls.to_wallet_id)
            .outerjoin(to_meter, and_(to_meter.c.id == to_wallet.c.meter_id,
                                      to_meter.c.ground_id == ground.id))
            .outerjoin(to_meter_billing, to_meter_billing.c.meter_id == to_meter.c.id)
            .outerjoin(to_tariff, to_tariff.c.id == to_meter_billing.c.tariff_id)
        ).group_by(
            from_tariff.c.id,
            to_tariff.c.id
        )
        return query

    @classmethod
    def get_processed_by_day(cls, ground, start, end, created_before=None):
        """
        Get the creation dates (and counts) of the transactions that were
        processed or reversed within the specified time period.

        :param ground: the ground
        :param start: start of the period
        :param end: end of the period
        :param created_before: Optionally cap results by creation date (e.g.,
            only select transactions created two or more days ago that were
            processed today.
        :returns: a resultset sequence with these attributes:
           :total_amount: sum of all transactions for the period
           :transaction_count: number of transactions
        """
        if created_before is None:
            created_before = func.now()
        query = (
            sql.session.query(
                func.date_trunc('day', cls.created).label('day_created'),
                func.count(cls.id).label('total_processed'),
            )
            .filter(ground == cls.ground)
            .filter(or_(cls.state == Transaction.STATE_PROCESSED,
                        cls.state == Transaction.STATE_REVERSED))
            .filter(cls.created < created_before)
            .filter(or_(
                and_(cls.processed_timestamp >= start,
                     cls.processed_timestamp < end),
                and_(cls.reversed_timestamp >= start,
                     cls.reversed_timestamp < end)))
        ).group_by('day_created').order_by('day_created')
        return query

    @classmethod
    def create_transactions(cls,
                            from_object,
                            to_object,
                            amount,
                            user,
                            wallet_type,
                            source,
                            ground,
                            memo=None,
                            markup=None,
                            external_id=None,
                            session=None,
                            return_bonus_tuple=False):
        """
        Create transaction(s) between two objects.

        This can be run on either ground or cloud because no balance updates occur.
        Current use cases:

          - credit from a sales account to a meter
          - debt from a meter to a sales account
          - credit from a system sales account to a sales account (transfer)
          - debt from a sales account to a system sales account (transfer)

        :param from_object: the source of the transaction, either a meter or a sales account
        :type from_object: Meter | SalesAccount
        :param to_object: the destination of the transaction, either a meter or a sales account
        :type to_object: Meter | SalesAccount
        :param amount: how much to transfer, only system sales accounts can make this negative
        :type amount: int, float
        :param wallet_type: what kind of wallet; debt/credit/plan
        :param user: the user that is creating this transaction
        :param source: the transaction source
        :type source: TransactionSource
        :param ground: ground this applies to
        :type ground: Ground
        :param markup: optionally, a second transaction will be created using the bonus source based on the
          markup rate.
        :type markup: Optional[float]
        :param external_id: optionally, an external_id. Must be unique
        :type external_id: Optional[str]
        :param session: optionally, a database session to run this in
        :param return_bonus_tuple: `True` if the return value should be a tuple that includes an optional
            bonus transaction
        :type return_bonus_tuple: bool
        :raises TransactionError: if the vendor doesn't have enough funds to make this transaction
        :raises TransactionError: if there already exists a transaction with is external_id
        :raises ValueError: if the amount is zero
        :raises ValueError: if the amount is negative and the from_object is not a system sales account
        :returns: the new transaction. If `return_bonus_tuple` is `True`, then a tuple of the transaction and
            bonus transaction
        :rtype: Transaction
        """
        from sparkmeter.ground.grounddomain import Ground
        from sparkmeter.meter.meterdomain import Meter
        from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
        from sparkmeter.user.userdomain import User
        if not isinstance(from_object, (Meter, SalesAccount)):  # pragma: nocover
            raise TypeError("from_object must be a meter, ground or sales account, not %r" % (
                from_object, ))
        if not isinstance(to_object, (Meter, SalesAccount)):  # pragma: nocover
            raise TypeError("to_object must a meter, ground or sales account, not %r" % (
                to_object, ))
        if amount == 0:
            raise ValueError("amount cannot be zero")
        if amount < 0:
            if isinstance(from_object, SalesAccount):
                if not from_object.system:
                    raise ValueError("only system sales accounts can create negative transactions")
            else:
                raise ValueError("amount must be positive, not %r" % (amount, ))
        if wallet_type not in Wallet.TYPES:  # pragma: nocover
            raise ValueError("incorrect wallet_type: %r" % (wallet_type, ))
        if not isinstance(user, User):  # pragma: nocover
            raise TypeError("user must be a User, not %r" % (user, ))
        if not isinstance(source, TransactionSource):  # pragma: nocover
            raise TypeError("source must be a TransactionSource, not %r" % (source, ))
        if not isinstance(ground, Ground):  # pragma: no cover
            raise TypeError("ground must be a Ground, not %r" % (ground, ))
        if markup and amount < 0:
            raise ValueError("negative transactions cannot have markup")
        if markup and not 0 <= markup <= 1:
            raise ValueError("markup must be between 0 and 1")
        if session is None:  # pragma: nocoverage
            session = sql.session
        if memo and len(memo) > cls.__table__.columns.memo.type.length:
            raise ValueError(
                "memos may not be longer than {} characters".format(cls.__table__.columns.memo.type.length))

        from_object.check_can_sell_from(user)
        to_object.check_can_sell_to(user)
        from_wallet = from_object.get_wallet(wallet_type)
        to_wallet = to_object.get_wallet(wallet_type)

        # make sure the from wallet can cover the transaction amount
        if from_wallet.value - amount < 0 and not from_wallet.negative_permitted:
            raise TransactionError(
                TransactionError.ERROR_NOT_ENOUGH_FUNDS,
                _((u'%(obj)s does not have enough %(wallet_type)s (%(val).2f) '
                   u'to cover a transaction of %(amt).2f'),
                    obj=from_object.description,
                    wallet_type=wallet_type,
                    val=from_wallet.value,
                    amt=amount))

        # make sure the external_id is unique
        if external_id is not None:
            if Transaction.get_by_external_id(external_id):
                raise TransactionError(
                    TransactionError.ERROR_DUPLICATED,
                    _("A transaction with external_id %(external_id)s already exists.",
                      external_id=external_id))

        from_snapshot = Snapshot.get_or_create_wallet_snapshot(from_wallet, session=session)
        to_snapshot = Snapshot.get_or_create_wallet_snapshot(to_wallet, session=session)

        transaction = cls(
            ground_id=ground.id,
            amount=amount,
            user=user,  # user performing action
            acct_type=wallet_type,  # credit or debt
            source=source,
            from_wallet=from_wallet,
            to_wallet=to_wallet,
            external_id=external_id,
            origin=Transaction.ORIGIN_USER,
            memo=memo,
            from_snapshot=from_snapshot,
            to_snapshot=to_snapshot,
        )
        session.add(transaction)
        session.flush()

        bonus_transaction = None
        if markup and wallet_type == Wallet.TYPE_CREDIT and source.name != TransactionSource.BONUS:
            # transfers have an automatic bonus transaction based on the vendor markup
            # the operator can overwrite the markup percent on the transaction form
            # if the markup is 0, then there is no bonus transaction created.
            bonus = session.query(TransactionSource).filter_by(name=TransactionSource.BONUS).one()
            bonus_transaction = cls(
                ground_id=transaction.ground_id,
                amount=amount * markup,
                user=user,  # user performing action
                from_wallet=from_wallet,  # ground selling credits
                to_wallet=to_wallet,  # vendor receiving credits
                acct_type=Wallet.TYPE_CREDIT,  # automatic bonus transaction
                reference_id=transaction.id,
                source=bonus,
                origin=Transaction.ORIGIN_SYSTEM,
                from_snapshot=from_snapshot,
                to_snapshot=to_snapshot,
            )
            session.add(bonus_transaction)
            session.flush()

        if return_bonus_tuple:
            return transaction, bonus_transaction
        return transaction

    def is_pending(self):
        """Figure out if this transaction is pending.
        :returns: True if the transaction is pending, False otherwise.
        """
        return self.state == Transaction.STATE_PENDING

    def is_processed(self):
        """Figure out if this transaction has been processed.
        :returns: True if the transaction is processed, False otherwise.
        """
        return self.state == Transaction.STATE_PROCESSED

    def set_error(self, error):
        """Set a transaction error.

        :param error: the error message to set.
        """
        if self.state == Transaction.STATE_ERROR:
            raise ValueError("This transaction has already an error set.")
        self.state = Transaction.STATE_ERROR
        self.error = error
        self.errored_timestamp = datetime.datetime.utcnow()

    def has_been_reversed(self):
        """Figure out if this transaction has been reversed already.

        A transaction is considered reversed if another transaction
        references the parent transaction of this transaction and is
        processed with a reversal origin set.
        :returns: True if the transaction has been reversed.
        """
        query = (
            self.query
            .filter_by(reference_id=self.id,
                       origin=Transaction.ORIGIN_REVERSAL,
                       state=Transaction.STATE_PROCESSED)
        )
        return bool(query.count())

    def process(self):
        """Process a pending transaction.

        Process a pending transaction, by transfering the requested amount
        from the source wallet to the destination wallet.

        If a transaction is destined to a meter, request a meter update state
        so that the meter state is consistent with the funds and trigger
        an customer event for a successful payment.

        :raises ValueError: if the transaction is not pending
        :raises ValueError: if the account type is not credit/debt/plan
        :raises ValueError: if negative_allowed is not set and there's not enough funds
        """
        if not self.is_pending():
            raise TransactionError(
                TransactionError.ERROR_ALREADY_PROCESSED,
                'Error processing transaction {id}: already processed'.format(
                    id=self.id))

        if self.acct_type not in Wallet.TYPES:
            raise TransactionError(
                TransactionError.ERROR_WRONG_TYPE,
                'Error processing transaction {id}: unknown transaction type ({acct_type.code})'.format(
                    acct_type=self.acct_type,
                    id=self.id))

        # If the parent transaction has already been reversed, don't allow
        # this one to be processed, eg no double-reversals are allowed.
        if self.origin == Transaction.ORIGIN_REVERSAL and self.reference_id:
            parent = self.query.get(self.reference_id)
            if parent.has_been_reversed():
                raise TransactionError(
                    TransactionError.ERROR_ALREADY_REVERSED,
                    _('Parent transaction already reversed.'))
            parent.state = Transaction.STATE_REVERSED
            parent.reversed_timestamp = datetime.datetime.utcnow()
            self.session.add(parent)
            event = Event.create(Event.TYPE_REVERSAL_TRANSACTION,
                                 obj=parent)
            event.created_by = self.user
            self.session.add(event)

        # save the starting values for logging at the end
        from_wallet_starting = self.from_wallet.value
        to_wallet_starting = self.to_wallet.value

        # Decrease the amount in the from wallet
        if not self.from_wallet.negative_permitted and self.from_wallet.value - self.amount < 0:
            raise TransactionError(
                TransactionError.ERROR_NOT_ENOUGH_FUNDS,
                _('Sending side does not contain enough funds ({val:.2f}) '
                  'to complete transfer of value {amount:.2f}.').format(
                    val=self.from_wallet.value,
                    amount=self.amount))
        self.from_wallet.value -= self.amount
        self.session.add(self.from_wallet)

        # Increase the amount in the to wallet
        self.to_wallet.value += self.amount
        self.session.add(self.to_wallet)

        # If we are decreasing the value of a wallet that is connected to a customer,
        # update the state of the meter, possibly turning it off if there are no
        # more credits.
        meter = self.to_wallet.meter
        if meter is not None:
            meter.send_set_config_based_on_system_info()
            if self.acct_type == Wallet.TYPE_CREDIT and self.origin != Transaction.ORIGIN_REVERSAL:
                if self.source.name == TransactionSource.CASH:
                    event = Event.create(Event.TYPE_CUSTOMER_CREDIT_TRANSACTION, obj=self)
                    event.created_by = self.user
                    self.session.add(event)
                elif self.source.name == TransactionSource.BONUS:
                    event = Event.create(Event.TYPE_CUSTOMER_CREDIT_BONUS_TRANSACTION, obj=self)
                    event.created_by = self.user
                    self.session.add(event)

            meter.maybe_convert_negative_balance_to_debt()

        self.state = Transaction.STATE_PROCESSED
        self.processed_timestamp = datetime.datetime.utcnow()

        # Under some cases, the ChoiceType is just a string. Rather than dive into the madness that is
        #  SQLAlchemy ORM lifecycle, just work around the field differences.
        account_type = self.acct_type.code if hasattr(self.acct_type, 'code') else self.acct_type
        msg = ('Successfully processed transaction {id}: '
               'from wallet:{account_type}: {starting:.2f} - {amount:.2f} = {ending:.2f}')
        logger.info(msg.format(starting=from_wallet_starting,
                               ending=self.from_wallet.value,
                               account_type=account_type,
                               **self._data))

        msg = ('Successfully processed transaction {id}: '
               'to wallet:{account_type}: {starting:.2f} + {amount:.2f} = {ending:.2f}')
        logger.info(msg.format(starting=to_wallet_starting,
                               ending=self.to_wallet.value,
                               account_type=account_type,
                               **self._data))

    def reverse(self, user):
        """Reverses a processed transaction.

        Reverses a processed transaction, by transfering the requested amount
        from the source wallet to the destination wallet.

        If a transaction is destined to a meter, request a meter update state
        so that the meter state is consistent with the funds and trigger
        an customer event for a successful payment.

        :param user: the user that is creating this transaction
        :type user: User
        :returns: a reversal transaction
        :rtype: Transaction
        :raises TransactionError: if the transaction is not processed
        """
        from sparkmeter.user.userdomain import User
        if not isinstance(user, User):
            raise TypeError("user must be a User, not %r" % (type(user).__name__, ))

        if self.has_been_reversed():
            raise TransactionError(
                TransactionError.ERROR_ALREADY_REVERSED,
                u"Already reversed")
        elif not self.is_processed():
            raise TransactionError(
                TransactionError.ERROR_NOT_PROCESSED,
                u"Not processed")

        from_snapshot = Snapshot.get_or_create_wallet_snapshot(self.from_wallet)
        to_snapshot = Snapshot.get_or_create_wallet_snapshot(self.to_wallet)

        transaction = Transaction(
            ground=self.ground,
            amount=-self.amount,
            user=user,
            acct_type=self.acct_type,
            source=self.source,
            from_wallet=self.from_wallet,
            to_wallet=self.to_wallet,
            reference_id=self.id,
            origin=Transaction.ORIGIN_REVERSAL,
            from_snapshot=from_snapshot,
            to_snapshot=to_snapshot,
        )
        return transaction


class TransactionView(BaseView):
    """
    A database view of transaction and related columns.
    This contains aggregated columns of a transaction list, suitable for usage within
    a listing.
    """

    __tablename__ = 'transaction_view'

    #: Account type, either credit or debt
    acct_type = Column(String)

    #: The transaction amount, how much is transferred between the parties
    amount = Column(Float)

    #: When this transaction was created
    created = Column(DateTime)

    #: Error message in case the processing of this transaction caused an error
    error = Column(String)

    #: An identifier for a transaction in an external system
    external_id = Column(String)

    #: Description of the transaction
    memo = Column(String(300))

    #: Where does this transaction originate, user/system/reverse
    origin = Column(String)

    #: For bonus transactions, a reference to the transaction the bonuses was applied to
    #: For reversal transactions, which transaction it reverses
    reference_id = Column(UUIDType(binary=False), ForeignKey('transactions.id'))

    #: The state of this transaction, PENDING/PROCESSED/ERROR/REVERSED
    state = Column(String)

    #: Name of the transaction source
    source_name = Column(String)

    #: If the transaction source is monetary
    source_monetary = Column(Boolean)

    #: User's username
    user_username = Column(String)

    #: The ground this transaction belongs to
    ground_id = Column(UUIDType(binary=False), ForeignKey('ground.id'))

    #: Name of the ground
    ground_name = Column(String)

    #: Serial of the ground
    ground_serial = Column(String)

    #: If this transaction has a reversal
    has_reversal = Column(Boolean)

    #: sales account id sending this transaction or None
    from_sales_account_id = Column(UUIDType(binary=False), ForeignKey('sales_account.id'))

    #: sales account id receiving this transaction or None
    to_sales_account_id = Column(UUIDType(binary=False), ForeignKey('sales_account.id'))

    #: meter id for credit transactions, or None
    from_meter_id = Column(UUIDType(binary=False), ForeignKey('meter.id'))

    #: meter id for debt transaction, or None
    to_meter_id = Column(UUIDType(binary=False), ForeignKey('meter.id'))

    #: Ground for this transaction or None for transaction between two global accounts
    ground = relationship("Ground")

    #: sales account sending this transaction or None
    from_sales_account = relationship(
        "SalesAccount",
        foreign_keys=[from_sales_account_id])  # type: SalesAccount

    #: sales account receiving this transaction or None
    to_sales_account = relationship(
        "SalesAccount",
        foreign_keys=[to_sales_account_id])  # type: SalesAccount

    #: meter for credit transactions, or None
    from_meter = relationship("Meter", foreign_keys=[from_meter_id])  # type: Meter

    #: meter for debt transaction, or None
    to_meter = relationship("Meter", foreign_keys=[to_meter_id])  # type: Meter

    #: from wallet information as JSON
    from_data = Column(JSONString)

    #: to wallet information as JSON
    to_data = Column(JSONString)

    @classmethod
    def get_transaction_view(cls,
                             ground=None,
                             meter=None,
                             sales_account=None,
                             user=None,
                             query_string='',
                             order='created',
                             ascending=False,
                             offset=None,
                             limit=None):
        """Get a set of transactions.

        This will be used to display the list of transactions for meters & sales accounts
        It will return a list of dictionaries instead of Transaction object due to performance
        reasons. It's suitable for putting into jsonify() and display in the interface.

        If you specify multiple parameters (meter, sales account) the returned query
        will include the intersection (the common to all).

        By default the results will be orded by creation date descending.

        :param ground: restricte the transactions to ground or ``None``
        :type ground: Ground
        :param meter: restrict the transactions to a meter or ``None``
        :type meter: Meter
        :param sales_account: restrict the transactions to a sales_account or ``None``
        :type sales_account: SalesAccount
        :param user: the currently logged in user
        :type user: sparkmeter.user.userdomain.User
        :param query_string: an optional string by which results should be filtered
        :type query_string: str
        :param order: the column name by which results should be sorted
        :type order: str
        :param ascending: `True` if results should be sorted in ascending order, `False` otherwise
        :type ascending: bool
        :param offset: (optional) the start offset for the transaction results
        :type offset: int
        :param limit: (optional) the maximum number of results that may be returned in a query
        :type limit: int
        :returns: transaction query result tuple: 0 - trans, 1 - total results
        """

        q = sql.session.query(cls, func.count(cls.id).over().label('total'))

        if meter is not None:
            q = q.filter(or_(cls.from_meter == meter, cls.to_meter == meter))

        if ground is not None:
            q = q.filter_by(ground=ground)

        if sales_account is not None:
            q = q.filter(or_(cls.from_sales_account == sales_account,
                             cls.to_sales_account == sales_account))

        if user is not None:
            users_grounds_t = get_table_by_name('users_grounds')
            q = q.filter(users_grounds_t.c.user_id == user.id,
                         users_grounds_t.c.ground_id == cls.ground_id)

        if order in ('from_data', 'to_data'):
            q = q.order_by(text("""COALESCE(
                           json_extract_path({colname}::json, 'sales_account_name'),
                           json_extract_path({colname}::json, 'meter_serial')
                           )::text {dir}""".format(colname=order, dir='ASC' if ascending else 'DESC')))
        else:
            try:
                q = q.order_by(getattr(getattr(cls, order), 'asc' if ascending else 'desc')())
            except AttributeError:
                logger.warning("Invalid order parameter requested: '%s'. Ignoring.", order)

        if query_string:
            q = q.filter(or_(
                text('{}.{}::text ~* :query_string'.format(
                    cls.__table__,
                    column.key
                )).params(
                    query_string=query_string
                )
                for column in (
                    cls.acct_type,
                    cls.amount,
                    cls.created,
                    cls.error,
                    cls.external_id,
                    cls.from_data,
                    cls.id,
                    cls.memo,
                    cls.ground_name,
                    cls.ground_serial,
                    cls.source_monetary,
                    cls.origin,
                    cls.reference_id,
                    cls.source_name,
                    cls.state,
                    cls.to_data,
                    cls.user_username,
                )
            ))

        if limit is not None:
            q = q.limit(limit)

        if offset is not None:
            q = q.offset(offset)

        return q
