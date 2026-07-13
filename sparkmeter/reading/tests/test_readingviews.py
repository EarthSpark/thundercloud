# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
import datetime
import logging

from freezegun import freeze_time

from sparkmeter.tests.base import WebViewTestCaseBase
from sparkmeter.tests.test_data_factory import (
    GroundFactory,
    MeterFactory,
    OperatorFactory,
    ReadingFactory,
    TotalizerMeterFactory,
)


class ReadingViewTest(WebViewTestCaseBase):
    @freeze_time("2014-01-01")
    def test_latest_readings_page_ground(self, client, config):
        path = "/readings/latest"

        config["HEROKU"] = False
        response = client.get(path)
        self.verify_response(response)

    @freeze_time("2014-01-01")
    def test_latest_readings_page_cloud(self, client, config):
        path = "/readings/latest"

        config["HEROKU"] = True
        response = client.get(path)
        self.verify_response(response)

    @freeze_time("2014-01-02")
    def test_latest_readings(self, client, config, operator_role):
        other = GroundFactory()
        self.session.commit()

        # meter 1 has no readings
        MeterFactory(serial="SM15R-01-00000001")
        MeterFactory(serial="SM15R-02-00000001", ground=other)

        # meter with empty customer name and code
        m13 = MeterFactory(serial="SM15R-01-00000013")
        m13.customer.name = ""
        m13.customer.code = None
        ReadingFactory(_meter=m13)
        self.session.flush()

        # meter 2 has readings and a good prr
        m12 = MeterFactory(serial="SM15R-01-00000002")
        m22 = MeterFactory(serial="SM15R-02-00000002", ground=other)

        reading = ReadingFactory(_meter=m12)
        self.session.flush()
        m12.system_info.reading_id = reading.id
        reading.heartbeat_start = datetime.datetime(2014, 1, 1, 11, 00)
        reading.heartbeat_end = datetime.datetime(2014, 1, 1, 12, 00)

        reading = ReadingFactory(_meter=m22)
        self.session.flush()
        m22.system_info.reading_id = reading.id
        reading.heartbeat_start = datetime.datetime(2014, 1, 1, 11, 00)
        reading.heartbeat_end = datetime.datetime(2014, 1, 1, 12, 00)

        # meter 3 has no readings either
        MeterFactory(serial="SM15R-01-00000003")
        MeterFactory(serial="SM15R-02-00000003", ground=other)

        # meter 4 is inactive
        m14 = MeterFactory(serial="SM15R-01-00000004")
        m24 = MeterFactory(serial="SM15R-02-00000004", ground=other)
        self.session.flush()
        m14.config.hidden = True
        m24.config.hidden = True

        self.session.commit()

        users = [
            OperatorFactory(roles=[operator_role], username="none", grounds=[]),
            OperatorFactory(roles=[operator_role], username="only-1", grounds=[self.ground]),
            OperatorFactory(roles=[operator_role], username="only-2", grounds=[other]),
            OperatorFactory(roles=[operator_role], username="all", grounds=[self.ground, other]),
        ]
        self.session.commit()

        for params in [
            dict(HEROKU=True),
            dict(HEROKU=False, SERIAL=self.ground.serial),
            dict(HEROKU=False, SERIAL=other.serial),
        ]:
            if params.get("SERIAL") == self.ground.serial:
                where = "ground1"
            elif params.get("SERIAL") == other.serial:
                where = "ground2"
            else:
                where = "cloud"
            for user in users:
                config.update(HEARTBEAT_PERIOD=15, **params)
                client.login_as(user)
                for page, path in [("csv", "/readings/latest.csv"), ("json", "/readings/latest.json")]:
                    response = client.get(path)
                    variant = "%s-%s-%s" % (page, where, user.username)
                    self.verify_response(response, variant=variant)

    def test_latest_readings_totalizers_present(self, client, config):
        path = "/readings/latest.json"
        MeterFactory(serial="SM15R-01-00000001")
        TotalizerMeterFactory(serial="SM200E-01-00000011")
        self.session.commit()

        config["HEROKU"] = False
        response = client.get(path)
        data = response.json()
        assert len(data["readings"]) == 2
        self.verify_response(response)

    def test_latest_readings_uses_meter_driver_heartbeat(self, client, config, monkeypatch):
        config["HEROKU"] = False
        path = "/readings/latest.json"

        monkeypatch.setattr(
            "sparkmeter.reading.readingview._query_latest_readings",
            lambda ground_serial: [],
        )
        monkeypatch.setattr(
            "sparkmeter.config.provider_settings.get_enabled_provider",
            lambda: {"id": "driver-1"},
        )
        monkeypatch.setattr(
            "sparkmeter.config.provider_settings.load_provider_runtime_settings",
            lambda provider: {
                "field_values": {
                    "heartbeat_period_duration": "60",
                }
            },
        )

        response = client.get(path)

        assert response.json()["heartbeat_seconds"] == 60

    def test_latest_readings_heartbeat_falls_back_on_error(self, client, config, monkeypatch, caplog):
        # A provider-lookup failure is logged and falls back to HEARTBEAT_PERIOD (readingview lines 45-46).
        config["HEROKU"] = False
        config["HEARTBEAT_PERIOD"] = 15
        path = "/readings/latest.json"

        monkeypatch.setattr(
            "sparkmeter.reading.readingview._query_latest_readings",
            lambda ground_serial: [],
        )

        def boom():
            raise RuntimeError("provider lookup failed")

        monkeypatch.setattr(
            "sparkmeter.config.provider_settings.get_enabled_provider",
            boom,
        )

        caplog.set_level(logging.ERROR, logger="sparkmeter.reading.readingview")
        response = client.get(path)

        assert response.json()["heartbeat_seconds"] == 15 * 60
        assert "failed to resolve meter-driver heartbeat for latest readings UI" in caplog.text
