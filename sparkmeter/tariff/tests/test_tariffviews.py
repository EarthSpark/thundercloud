# -*- coding: utf-8 -*-
# Copyright © 2013-2018 SparkMeter, Inc.
# All Rights Reserved.
import http.client
import operator
from builtins import str
from unittest import mock

import pytest
from flask.helpers import url_for

from sparkmeter.constants import MAX_SIGNED_INT
from sparkmeter.event.eventdomain import Event
from sparkmeter.meter.meterdomain import MeterConfig
from sparkmeter.misc.htmlutils import build_link
from sparkmeter.misc.jsonutils import json_dumps
from sparkmeter.tariff.tariffdomain import Tariff
from sparkmeter.tests.base import WebViewTestCaseBase
from sparkmeter.tests.test_data_factory import MeterFactory, TariffFactory


@pytest.fixture(scope="module", autouse=True)
def _setup(app):
    with mock.patch.dict(app.config, dict(HEROKU=False)):
        yield


class TariffViewTest(WebViewTestCaseBase):
    def test_list(self, client):
        TariffFactory()
        self.session.commit()

        path = "/tariff/"
        response = client.get(path)
        self.verify_response(response)

    def test_view(self, client):
        t = TariffFactory()
        self.session.commit()

        path = "/tariff/{}/".format(t.id)

        response = client.get(path)
        self.verify_response(response)

    def test_view_not_found(self, client):
        path = "/tariff/0b440c54-9be0-4b39-9a06-9236be39fa0a/"

        response = client.get(path)
        self.verify_response(response)

    def test_add(self, client):
        path = "/tariff/add"

        response = client.get(path)
        self.verify_response(response)

    def test_add_modal_get(self, client):
        # GET renders the modal form with no validation errors (tariffview lines 78, 90, 32-33, 36).
        path = "/tariff/add-modal"

        response = client.get(path)
        assert response.status_code == http.client.OK
        assert "X-Form-Errors" not in response.headers
        self.verify_response(response)

    def test_add_modal_post_valid(self, client, config):
        # A valid POST creates the tariff and returns JSON (tariffview lines 79-88).
        path = "/tariff/add-modal"
        data = dict(
            name="MODAL TARIFF",
            flat_load_limit=150,
            plan_price=0,
            cycle_start_day_of_month=1,
            tariff_type="flat",
            flat_price=4,
            tous="",
        )

        config["HEROKU"] = False
        response = client.post(path, data=data)

        assert response.status_code == http.client.OK
        body = response.json()
        assert body["message"] == "Tariff created."

        tariffs = Tariff.get_all()
        assert len(tariffs) == 1
        assert body["tariff"]["name"] == "MODAL TARIFF"
        assert body["tariff"]["id"] == str(tariffs[0].id)

    def test_add_modal_post_invalid(self, client):
        # An invalid POST re-renders the modal form with the error header (tariffview lines 89, 34-35).
        path = "/tariff/add-modal"
        data = dict(name="", flat_load_limit=150, flat_price=4)

        response = client.post(path, data=data)

        assert response.status_code == http.client.BAD_REQUEST
        assert "X-Form-Errors" in response.headers
        assert "Please set a name for this tariff" in response.text
        assert not Tariff.query.scalar()

    def test_add_form(self, client, config):
        path = "/tariff/add"

        data = dict(
            name="TARIFF",
            flat_load_limit=150,
            plan_price=0,
            cycle_start_day_of_month=1,
            tariff_type="flat",
            flat_price=4,
            tous="",
        )

        config["HEROKU"] = False
        response = client.post(path, data=data, follow_redirects=True)

        tariffs = Tariff.get_all()
        assert len(tariffs) == 1
        t = tariffs[0]
        assert t.name == data["name"]
        assert t.flat_load_limit == data["flat_load_limit"]
        assert t.tariff_type == data["tariff_type"]
        assert t.flat_price == data["flat_price"]
        assert not t.tou_enabled
        assert len(t.blockrates) == 0
        assert len(t.tous) == 0
        assert t.cycle_start_day_of_month == 1

        self.verify_response(response, ignore_values=[str(tariffs[0].id)])

        link = build_link(url_for("tariff.edit", tariff_id=t.id), "TARIFF")
        assert "Tariff %s created" % (link,) in response.text

    def test_add_form_int_outrange(self, client, config):
        path = "/tariff/add"

        data = dict(
            name="TARIFF",
            flat_load_limit=MAX_SIGNED_INT + 1,
            load_limit_type="flat",
            plan_price=0,
            cycle_start_day_of_month=1,
            tariff_type="flat",
            flat_price=4,
            tous="",
        )

        config["HEROKU"] = False
        response = client.post(path, data=data, follow_redirects=True)

        self.verify_response(response)
        assert not Tariff.query.scalar()

    def test_add_form_int_max_allowed(self, client, config):
        path = "/tariff/add"

        data = dict(
            name="TARIFF",
            flat_load_limit=MAX_SIGNED_INT,
            load_limit_type="flat",
            plan_price=0,
            cycle_start_day_of_month=1,
            tariff_type="flat",
            flat_price=4,
            tous="",
        )

        config["HEROKU"] = False
        response = client.post(path, data=data, follow_redirects=True)

        tariff = Tariff.query.one()
        self.verify_response(response, ignore_values=[str(tariff.id)])

    def test_add_form_with_tous(self, client, config):
        path = "/tariff/add"

        data = dict(
            tous=json_dumps(
                [
                    {
                        "end": "24:00",
                        "id": "612aaccf-a86f-486e-82b4-3abd136f34ef",
                        "start": "00:00",
                        "value": 100,
                    }
                ]
            ),
            name="TARIFF TOU",
            load_limit_type="flat",
            flat_load_limit=150,
            plan_price=0,
            cycle_start_day_of_month=1,
            tariff_type="flat",
            flat_price=4,
            tou_enabled=True,
        )

        config["HEROKU"] = False
        response = client.post(path, data=data, follow_redirects=True)

        tariffs = Tariff.get_all()
        assert len(tariffs) == 1
        t = tariffs[0]
        assert t.name == data["name"]
        assert t.flat_load_limit == data["flat_load_limit"]
        assert t.tariff_type == data["tariff_type"]
        assert t.flat_price == data["flat_price"]
        assert t.tou_enabled == data["tou_enabled"]
        assert len(t.blockrates) == 0
        assert len(t.tous) == 1
        tous = t.get_tous()
        assert tous[0].start == "00:00"
        assert tous[0].end == "00:00"
        assert tous[0].value == 100

        self.verify_response(response, variant="tous-post", ignore_values=[str(tariffs[0].id)])
        link = build_link(url_for("tariff.edit", tariff_id=t.id), "TARIFF TOU")
        assert "Tariff %s created" % (link,) in response.text

    def test_add_form_with_blockrates(self, client, config):
        path = "/tariff/add"

        data = dict(
            blockrates=json_dumps(
                [
                    {"lower": 0, "upper": 20, "value": 1},
                    {"lower": 20, "upper": 40, "value": 2},
                    {"lower": 40, "upper": 0, "value": 3.5},
                ]
            ),
            name="TARIFF BLOCKRATES",
            load_limit_type="flat",
            flat_load_limit=150,
            plan_price=0,
            cycle_start_day_of_month=1,
            tariff_type=Tariff.TYPE_BLOCKRATE,
            flat_price=4,
        )

        config["HEROKU"] = False
        response = client.post(path, data=data, follow_redirects=True)

        tariffs = Tariff.get_all()
        assert len(tariffs) == 1
        t = tariffs[0]
        assert t.name == data["name"]
        assert t.flat_load_limit == data["flat_load_limit"]
        assert t.tariff_type == data["tariff_type"]
        assert t.flat_price == data["flat_price"]
        assert not t.tou_enabled
        assert len(t.tous) == 0
        assert len(t.blockrates) == 3
        blockrates = list(sorted(t.get_blockrates(), key=operator.attrgetter("value")))
        assert blockrates[0].lower == 0
        assert blockrates[0].upper == 20
        assert blockrates[0].value == 1
        assert blockrates[1].lower == 20
        assert blockrates[1].upper == 40
        assert blockrates[1].value == 2
        assert blockrates[2].lower == 40
        assert blockrates[2].upper == 0
        assert blockrates[2].value == 3.5

        self.verify_response(response, ignore_values=[str(tariffs[0].id)])
        link = build_link(url_for("tariff.edit", tariff_id=t.id), "TARIFF BLOCKRATES")
        assert "Tariff %s created" % (link,) in response.text

    def test_add_form_with_load_limits(self, client, config):
        path = "/tariff/add"

        data = dict(
            load_limits=json_dumps(
                [
                    {"start": "00:00", "end": "18:00", "value": 1},
                    {"start": "18:00", "end": "22:00", "value": 2},
                    {"start": "22:00", "end": "00:00", "value": 3.5},
                ]
            ),
            name="TARIFF LOAD LIMITS",
            load_limit_type=Tariff.LOAD_LIMIT_TYPE_SCHEDULED,
            flat_load_limit=150,
            plan_price=0,
            cycle_start_day_of_month=1,
            tariff_type=Tariff.LOAD_LIMIT_TYPE_FLAT,
            flat_price=4,
        )

        config["HEROKU"] = False
        response = client.post(path, data=data, follow_redirects=True)

        tariffs = Tariff.get_all()
        assert len(tariffs) == 1
        t = tariffs[0]
        assert t.name == data["name"]
        assert t.flat_load_limit == data["flat_load_limit"]
        assert t.tariff_type == data["tariff_type"]
        assert t.flat_price == data["flat_price"]
        assert not t.tou_enabled
        assert len(t.tous) == 0
        assert len(t.blockrates) == 0
        assert len(t.load_limits) == 3
        limits = list(sorted(t.get_load_limits(), key=operator.attrgetter("value")))
        assert limits[0].start == "00:00"
        assert limits[0].end == "18:00"
        assert limits[0].value == 1
        assert limits[1].start == "18:00"
        assert limits[1].end == "22:00"
        assert limits[1].value == 2
        assert limits[2].start == "22:00"
        assert limits[2].end == "00:00"
        assert limits[2].value == 3.5

        self.verify_response(response, ignore_values=[str(tariffs[0].id)])
        link = build_link(url_for("tariff.edit", tariff_id=t.id), "TARIFF LOAD LIMITS")
        print(response.data)
        assert "Tariff %s created" % (link,) in response.text

    def test_add_with_invalid_blockrates(self, client):
        path = "/tariff/add"
        data = dict(
            blockrates=json_dumps([{"lower": "1", "upper": "20", "value": "1"}]),
            name="Tariff",
            load_limit_type="flat",
            flat_load_limit=150,
            plan_price=0,
            cycle_start_day_of_month=1,
            tariff_type=Tariff.TYPE_BLOCKRATE,
        )
        response = client.post(path, data=data, follow_redirects=True)
        self.verify_response(response)
        msg = "Block rates contain at least one gap, between 0 and 65535"
        assert msg in response.text

    def test_add_with_invalid_tous(self, client):
        path = "/tariff/add"
        data = dict(
            tous=json_dumps(
                [
                    {
                        "end": "24:00",
                        "id": "612aaccf-a86f-486e-82b4-3abd136f34ef",
                        "start": "00:00",
                        "value": -100,
                    }
                ]
            ),
            name="TARIFF TOU",
            load_limit_type="flat",
            flat_load_limit=150,
            plan_price=0,
            cycle_start_day_of_month=1,
            tariff_type="flat",
            flat_price=4,
            tou_enabled=True,
        )
        response = client.post(path, data=data, follow_redirects=True)
        self.verify_response(response)
        msg = "The TOU period modifier must be a positive number."
        assert msg in response.text

    def test_error_empty_name(self, client):
        path = "/tariff/add"
        data = dict(name="", flat_load_limit=150, flat_price=4)
        response = client.post(path, data=data, follow_redirects=True)
        self.verify_response(response)
        msg = "Please set a name for this tariff"
        assert msg in response.text

    def test_error_duplicate_name(self, client):
        path = "/tariff/add"
        data = dict(
            name="TARIFF",
            flat_load_limit=150,
            plan_price=0,
            cycle_start_day_of_month=1,
            tariff_type="flat",
            flat_price=4,
            tous="",
        )
        client.post(path, data=data, follow_redirects=True)
        tariffs = Tariff.get_all()
        assert len(tariffs) == 1
        response = client.post(path, data=data, follow_redirects=True)
        self.verify_response(response)
        tariffs = Tariff.get_all()
        assert len(tariffs) == 1

    def test_error_existing_duplicate_names(self, client):
        path = "/tariff/add"
        TariffFactory(name="TARIFF", flat_load_limit=30)
        TariffFactory(name="TARIFF", flat_load_limit=31)
        self.session.commit()
        data = dict(
            name="TARIFF",
            flat_load_limit=150,
            plan_price=0,
            cycle_start_day_of_month=1,
            tariff_type="flat",
            flat_price=4,
            tous="",
        )
        response = client.post(path, data=data, follow_redirects=True)
        self.verify_response(response)
        tariffs = Tariff.get_all()
        assert len(tariffs) == 2

    def test_error_enter_load_limit(self, client):
        path = "/tariff/add"
        data = dict(name="Tariff", load_limit_type="flat", flat_price=4)
        response = client.post(path, data=data, follow_redirects=True)
        self.verify_response(response)
        msg = "Please enter a Load Limit for this tariff"
        assert msg in response.text

    def test_error_no_scheduled_load_limits(self, client):
        path = "/tariff/add"
        data = dict(name="Tariff", load_limit_type="scheduled", load_limits=[])
        response = client.post(path, data=data, follow_redirects=True)
        self.verify_response(response)

    def test_error_negative_load_limit(self, client):
        path = "/tariff/add"
        data = dict(
            name="Tariff",
            load_limit_type="flat",
            flat_load_limit=-2,
            flat_price=4,
        )
        response = client.post(path, data=data, follow_redirects=True)
        self.verify_response(response)
        msg = "Load Limits cannot be negative"
        assert msg in response.text

    def test_error_enter_monthly_plan_price(self, client):
        path = "/tariff/add"
        data = dict(
            name="Tariff",
            flat_load_limit=60,
            flat_price=1,
            plan_enabled=True,
            plan_price=-1,
            cycle_start_day_of_month=1,
        )
        response = client.post(path, data=data, follow_redirects=True)
        self.verify_response(response)
        assert "Number must be at least 0." in response.text

    def test_error_flat_rate(self, client):
        path = "/tariff/add"
        data = dict(
            name="Tariff",
            load_limit_type="flat",
            flat_load_limit=60,
            tariff_type="flat",
            flat_price=0,
        )
        response = client.post(path, data=data, follow_redirects=True)
        self.verify_response(response)
        assert "Please set a Flat Rate" in response.text

    def test_error_negative_flat_rate(self, client):
        path = "/tariff/add"
        data = dict(name="Tariff", flat_load_limit=60, tarriff_type="flat", flat_price=-2)
        response = client.post(path, data=data, follow_redirects=True)
        self.verify_response(response)
        assert "Flat Rate cannot be negative" in response.text

    def test_error_blockrate(self, client):
        path = "/tariff/add"
        data = dict(name="Tariff", flat_load_limit=60, tariff_type=Tariff.TYPE_BLOCKRATE)
        response = client.post(path, data=data, follow_redirects=True)
        self.verify_response(response)
        assert "Please add some block rates." in response.text

    def test_error_tous(self, client):
        path = "/tariff/add"
        data = dict(name="Tariff", flat_load_limit=60, tou_enabled=True)
        response = client.post(path, data=data, follow_redirects=True)
        self.verify_response(response)
        assert "Please add some TOU periods." in response.text

    def test_error_low_balance_empty(self, client):
        path = "/tariff/add"
        data = dict(name="Tariff", flat_load_limit=60, low_balance_threshold="")
        response = client.post(path, data=data, follow_redirects=True)
        self.verify_response(response)
        assert "Low Balance cannot be empty." in response.text

    def test_error_low_balance_negative(self, client):
        path = "/tariff/add"
        data = dict(name="Tariff", flat_load_limit=60, low_balance_threshold=-1)
        response = client.post(path, data=data, follow_redirects=True)
        self.verify_response(response)
        assert "Low Balance must be higher or equals to 0." in response.text

    def test_edit(self, client, config):
        config["HEROKU"] = True
        path = "/tariff/%s/edit"

        tariff = TariffFactory(name="Tariff", flat_load_limit=30)
        MeterFactory(code=1, config__state=MeterConfig.STATE_AUTO, tariff=tariff)
        MeterFactory(code=2, config__state=MeterConfig.STATE_AUTO, tariff=tariff)
        MeterFactory(code=3, config__state=MeterConfig.STATE_AUTO)
        self.session.commit()

        response = client.get(path % (tariff.id), follow_redirects=True)

        self.verify_response(response)

        data = dict(
            name="Tariff", load_limit_type="flat", flat_price=0, tariff_type="flat", flat_load_limit=60
        )
        response = client.post(path % (tariff.id), data=data, follow_redirects=True)
        self.verify_response(response, variant="edit-post-error")
        assert "Please set a Flat Rate" in response.text

        data = dict(name="Tariff", load_limit_type="flat", flat_price=-1, flat_load_limit=60)
        response = client.post(path % (tariff.id), data=data, follow_redirects=True)
        self.verify_response(response, variant="edit-negative-post-error")
        assert "Flat Rate cannot be negative" in response.text

        data = dict(
            name="new tariff", load_limit_type="flat", flat_load_limit=150, tariff_type="flat", flat_price=4
        )
        response = client.post(path % (tariff.id), data=data, follow_redirects=True)
        self.verify_response(response, variant="new-tariff")
        assert "Tariff updated." in response.text

    def test_edit_remove_blockrate(self, client):
        path = "/tariff/%s/edit"
        block1 = dict(lower=0, upper=20, value=1.0)
        tariff = TariffFactory(name="Tariff", flat_load_limit=30)

        self.session.commit()

        data = dict(
            name="Tariff",
            load_limit_type="flat",
            flat_load_limit=150,
            tariff_type=Tariff.TYPE_BLOCKRATE,
            blockrates=json_dumps([block1]),
            tou_enabled=False,
        )
        response = client.post(path % (tariff.id), data=data)
        assert response.status_code == http.client.OK

        tariff = Tariff.get_by_id(tariff.id)
        assert len(tariff.blockrates) == 1

    def test_edit_flat_load_limit_cloud(self, client, config):
        path = "/tariff/%s/edit"
        tariff = TariffFactory(flat_load_limit=10)
        MeterFactory(tariff=tariff)
        self.session.commit()

        data = dict(name="Tariff", flat_load_limit=20)
        config["HEROKU"] = True
        response = client.post(path % (tariff.id), data=data)
        assert response.status_code == http.client.FOUND
        events = Event.query.all()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == Event.TYPE_TARIFF_POWER_LIMIT_CHANGED
        assert event.object.id == tariff.id
        assert not event.processed

    def test_edit_flat_load_limit_ground(self, client, config, send_set_config):
        path = "/tariff/%s/edit"
        tariff = TariffFactory(flat_load_limit=10)
        MeterFactory(tariff=tariff)
        self.session.commit()

        data = dict(name="Tariff", flat_load_limit=20)
        config["HEROKU"] = False
        response = client.post(path % (tariff.id), data=data)
        assert response.status_code == http.client.FOUND
        events = Event.query.all()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == Event.TYPE_TARIFF_POWER_LIMIT_CHANGED
        assert event.object.id == tariff.id
        assert event.processed

        assert send_set_config.mock_calls == [
            mock.call(
                subnet=255,
                current_limit=10000.0,
                load_limit=10.0,
                mac=1,
                command="disable",
                balance=0,
                low_balance=True,
                firmware_version="abc1234",
            ),
        ]

    def test_edit_scheduled_load_limit(self, client, config, mocker, send_set_config):
        path = "/tariff/%s/edit"
        tariff = TariffFactory(
            load_limit_type=Tariff.LOAD_LIMIT_TYPE_SCHEDULED,
            load_limits=[
                {"start": "00:00", "end": "12:00", "value": 5},
                {"start": "12:00", "end": "00:00", "value": 10},
            ],
        )

        MeterFactory(tariff=tariff)
        self.session.commit()

        data = dict(
            name="Tariff",
            flat_load_limit=5,
            load_limit_type=Tariff.LOAD_LIMIT_TYPE_FLAT,
        )
        config["HEROKU"] = False

        f = mocker.patch.object(Tariff, "get_current_load_limit")
        f.side_effect = [10, 20, 20]

        response = client.post(path % (tariff.id), data=data)

        assert response.status_code == http.client.FOUND
        events = Event.query.all()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == Event.TYPE_TARIFF_POWER_LIMIT_CHANGED
        assert event.object.id == tariff.id
        assert event.processed

        assert send_set_config.mock_calls == [
            mock.call(
                subnet=255,
                current_limit=10000.0,
                load_limit=10.0,
                mac=1,
                command="disable",
                balance=0,
                low_balance=True,
                firmware_version="abc1234",
            ),
        ]
