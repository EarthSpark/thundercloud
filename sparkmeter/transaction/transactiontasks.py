# -*- coding: utf-8 -*-
# Copyright © 2013-2015 SparkMeter, Inc.
# All Rights Reserved.
"""General Sparkmeter tasks to be executed on the NUC."""

import logging

from flask.globals import current_app

from sparkmeter.config.configdict import config
from sparkmeter.exceptions import DatabaseLockTimeoutException, TransactionError
from sparkmeter.ground.grounddomain import Ground
from sparkmeter.transaction.transactiondomain import Transaction

logger = logging.getLogger(__name__)


def process_transactions():
    """Process all of the pending transactions in the nuc."""
    #
    # A previous incarnation of this task used to dispatch a separate task for each transaction,
    # with the intention of being able to take advantage of multiple cores and process as
    # many transactions as possible as fast as possible.
    # That was changed to do everything in one go for the following reasons:
    #
    # - Having multiple transactions being processed at the same time open for inconsitencies
    #   for complex scenarios where reversal transactions could be processed at the same time
    #   See http://jira.spk.io/browse/SW-110 for more information
    # - It's simpler to just process everything in one go, it reduces an abstraction layer which
    #   makes it easier to maintain/understand and test.
    # - It's actually unclear if it's faster to dispatch 1 + N tasks instead of just 1 tasks,
    #   IO/CPU/time overhead of each task has not been measured.
    #
    from sparkmeter.controller import process_transaction as process_transaction_controller

    with current_app.app_context():
        ground = Ground.get_by_serial(config["SERIAL"])
        for transaction in Transaction.get_unprocessed(ground):
            try:
                process_transaction_controller(transaction.id)
            except DatabaseLockTimeoutException:
                logger.error("Could not process transaction %s: database lock timeout", transaction.id)
                current_app.sentry.captureException(
                    message="Transaction {} process lock timeout".format(transaction.id),
                    tags={"action": "transaction_processing"},
                )
                raise
            except TransactionError as txerr:
                logger.exception("Could not process transaction %s: %s", transaction.id, txerr.message)
                # If the error is one where it's safe to proceed with the transaction queue...
                if txerr.code in [
                    TransactionError.ERROR_ALREADY_PROCESSED,
                    TransactionError.ERROR_ALREADY_REVERSED,
                ]:
                    continue
                raise
