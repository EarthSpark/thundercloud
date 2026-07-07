# -*- coding: utf-8 -*-
# Copyright © 2013-2016 SparkMeter, Inc.
# All Rights Reserved.

from unittest import mock

from testfixtures import log_capture

from sparkmeter.dashboard.dashboarddomain import DashboardDailyTariffSummary
from sparkmeter.meter.meterdomain import MeterBilling
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import (DashboardSummaryFactory, GroundFactory,
                                                MeterFactory, TariffFactory)


class TariffCommandTest(SparkMeterTestCaseBase):
    @log_capture('sparkmeter.tariff.tariffcommand')
    def test_list(self, logger, cli):
        TariffFactory(name='ET1', flat_load_limit=12)
        TariffFactory(name='ET2', flat_load_limit=80)
        TariffFactory(name='ET3', flat_load_limit=120)

        self.session.commit()

        cli('tariff', 'list')

        logger.check(
            ('sparkmeter.tariff.tariffcommand',
             'INFO',
             '                                  ID |                           NAME | LOAD LIMIT | '
             'MONTHLY PLAN |  RATE TYPE |               RATE |          TOUS | METERS'),
            ('sparkmeter.tariff.tariffcommand',
             'INFO',
             '====================================================================================='
             '==========================================================================='),
            ('sparkmeter.tariff.tariffcommand',
             'INFO',
             u'00000004-0000-0000-0000-000000000001 |                            ET1 |         12 |'
             u'          0.0 |       flat |               10.0 |               |      0'),
            ('sparkmeter.tariff.tariffcommand',
             'INFO',
             u'00000004-0000-0000-0000-000000000002 |                            ET2 |         80 |'
             u'          0.0 |       flat |               10.0 |               |      0'),
            ('sparkmeter.tariff.tariffcommand',
             'INFO',
             u'00000004-0000-0000-0000-000000000003 |                            ET3 |        120 |'
             u'          0.0 |       flat |               10.0 |               |      0')
        )

    @log_capture('sparkmeter.tariff.tariffcommand')
    def test_merge(self, logger, cli):
        grounda = GroundFactory()
        groundc = GroundFactory()
        tariffa = TariffFactory()
        tariffb = TariffFactory()
        tariffc = TariffFactory()

        self.session.commit()

        metera = MeterFactory(ground=grounda, billing__tariff=tariffa)
        meterb = MeterFactory(billing__tariff=tariffb)
        meterc = MeterFactory(ground=groundc, billing__tariff=tariffc)

        tariffa_id = metera.billing.tariff.id
        tariffb_id = meterb.billing.tariff.id
        tariffc_id = meterc.billing.tariff.id

        DashboardSummaryFactory(tariff=tariffa, ground=metera.ground)
        DashboardSummaryFactory(tariff=tariffb, ground=meterb.ground)
        DashboardSummaryFactory(tariff=tariffc, ground=meterc.ground)

        self.session.commit()

        result = cli('tariff', 'merge',
                     '-a', str(metera.billing.tariff.id),
                     '-b', str(meterb.billing.tariff.id),
                     '-y')
        assert result.exit_code == 0

        meters_a = MeterBilling.query.filter_by(tariff_id=tariffa_id).count()
        meters_b = MeterBilling.query.filter_by(tariff_id=tariffb_id).count()
        dashboard_summaries_a = DashboardDailyTariffSummary.query.filter_by(tariff_id=tariffa_id).count()
        dashboard_summaries_b = DashboardDailyTariffSummary.query.filter_by(tariff_id=tariffb_id).count()

        assert meters_a == 2
        assert meters_b == 0
        assert dashboard_summaries_a == 2
        assert dashboard_summaries_b == 0

        result = cli('tariff', 'merge',
                     '-a', str(metera.billing.tariff.id),
                     '-b', str(meterc.billing.tariff.id),
                     '-y')
        assert result.exit_code == 0

        meters_a = MeterBilling.query.filter_by(tariff_id=tariffa_id).count()
        meters_c = MeterBilling.query.filter_by(tariff_id=tariffc_id).count()
        dashboard_summaries_a = DashboardDailyTariffSummary.query.filter_by(tariff_id=tariffa_id).count()
        dashboard_summaries_c = DashboardDailyTariffSummary.query.filter_by(tariff_id=tariffc_id).count()

        assert meters_a == 3
        assert meters_c == 0
        assert dashboard_summaries_a == 3
        assert dashboard_summaries_c == 0

    @log_capture('sparkmeter.tariff.tariffcommand')
    def test_merge_errors(self, logger, cli):
        tariffa = TariffFactory(name='tariffa')
        tariffb = TariffFactory(name='tariffb')
        self.session.commit()

        result = cli('tariff', 'merge',
                     '-a', str(tariffa.id), '-b', str(tariffa.id), '-y')
        assert result.exit_code == 1
        logger.check(('sparkmeter.tariff.tariffcommand', 'ERROR',
                      'please enter two different tariffs'))
        logger.clear()

        does_not_exist = '12345678123456781234567812345678'
        does_not_exist_either = '12345678123456781234567812345679'
        result = cli('tariff', 'merge',
                     '-a', does_not_exist, '-b', does_not_exist_either, '-y')
        assert result.exit_code == 1
        logger.check(('sparkmeter.tariff.tariffcommand', 'ERROR',
                      'tariff 12345678123456781234567812345678 does not exist'))
        logger.clear()

        result = cli('tariff', 'merge',
                     '-a', str(tariffa.id), '-b', does_not_exist, '-y')
        assert result.exit_code == 1
        logger.check(('sparkmeter.tariff.tariffcommand', 'ERROR',
                      'tariff 12345678123456781234567812345678 does not exist'))

        logger.clear()

        # Without -y, prompt_bool is called and returns False (abort)
        with mock.patch('sparkmeter.tariff.tariffcommand.prompt_bool') as prompt_bool:
            prompt_bool.return_value = False
            result = cli('tariff', 'merge',
                         '-a', str(tariffa.id), '-b', str(tariffb.id))
            assert result.exit_code == 1

        logger.check(('sparkmeter.tariff.tariffcommand', 'INFO',
                      'Tariff remaining: tariffa (00000004-0000-0000-0000-000000000001)'),
                     ('sparkmeter.tariff.tariffcommand', 'INFO',
                      'Tariff to delete: tariffb (00000004-0000-0000-0000-000000000002)'),
                     ('sparkmeter.tariff.tariffcommand', 'WARNING',
                      '0 meters are associated with tariff tariffb'),
                     ('sparkmeter.tariff.tariffcommand', 'WARNING',
                      '0 dashboard summaries are associated with tariff tariffb'),
                     ('sparkmeter.tariff.tariffcommand', 'INFO', 'tariff merge aborted'))
