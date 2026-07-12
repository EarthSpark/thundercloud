# -*- coding: utf-8 -*-
# Copyright © 2013-2017 SparkMeter, Inc.
# All Rights Reserved.
import urllib.parse
from unittest import mock

import pytest
from flask import request
from werkzeug.datastructures import OrderedMultiDict

from sparkmeter.api.tests.test_apiviews0 import APIView0TestCaseBase
from sparkmeter.event.eventdomain import Event
from sparkmeter.exceptions import MeterError
from sparkmeter.meter.meterdomain import MeterConfig, MeterTag, MeterView
from sparkmeter.meter.meterstate import MeterState
from sparkmeter.misc.pythonutils import unset
from sparkmeter.salesaccount.salesaccountdomain import SalesAccount
from sparkmeter.tests.test_data_factory import (
    GroundFactory,
    MeterFactory,
    ReadingFactory,
    TariffFactory,
    TotalizerMeterFactory,
)


class CustomerListTest(APIView0TestCaseBase):
    path = "v0/customers"

    def _query(self, **kwargs):
        return self.get(self.path + "?" + urllib.parse.urlencode(kwargs))

    def test_list_all(self):
        MeterFactory(customer__name="Customer #1")
        MeterFactory(customer__name="Customer #2")
        self.session.commit()
        response = self.get(self.path)
        self.verify_response(response)

    def test_list_all_with_totalizers(self):
        MeterFactory(customer__name="Customer #1")
        MeterFactory(customer__name="Customer #2")
        TotalizerMeterFactory()
        TotalizerMeterFactory()
        self.session.commit()
        response = self.get(self.path)
        self.verify_response(response)

    def test_error_unknown_parameter(self):
        response = self.get(self.path + "?unknown-parameter")
        self.verify_response(response)

    def test_ground_id(self):
        ground1 = GroundFactory(name="Ground #1")
        ground2 = GroundFactory(name="Ground #2")
        self.session.commit()
        MeterFactory(customer__name="Customer #1", ground=ground1)
        MeterFactory(customer__name="Customer #2", ground=ground2)
        self.session.commit()
        response = self._query(ground_id=ground1.id)
        self.verify_response(response)

    def test_ground_name(self):
        ground1 = GroundFactory(name="Ground #1")
        ground2 = GroundFactory(name="Ground #2")
        self.session.commit()
        MeterFactory(customer__name="Customer #1", ground=ground1)
        MeterFactory(customer__name="Customer #2", ground=ground2)
        self.session.commit()
        response = self._query(ground_name=ground1.name.upper())
        self.verify_response(response)

    def test_error_ground_id_and_ground_name(self):
        response = self._query(ground_name=self.ground.name, ground_id=self.ground.id)
        self.verify_response(response)

    def test_error_no_such_ground_name(self):
        response = self._query(ground_name="no-such-ground")
        self.verify_response(response)

    def test_error_no_such_ground_id(self):
        response = self._query(ground_id="75d73108-080a-40d6-a98a-2c24a7974536")
        self.verify_response(response)

    def test_meter_serial(self):
        meter = MeterFactory()
        self.session.commit()
        response = self._query(meter_serial=meter.serial.lower())
        self.verify_response(response)

    def test_error_no_such_meter(self):
        response = self._query(meter_serial="no-such-meter")
        self.verify_response(response)

    def test_meter_tariff_name(self):
        meter = MeterFactory()
        self.session.commit()
        tariff_name = meter.tariff.name.upper()
        response = self._query(meter_tariff_name=tariff_name)
        self.verify_response(response)

    def test_no_such_tariff(self):
        response = self._query(meter_tariff_name="no-such-tariff")
        self.verify_response(response)

    def test_customer_code(self):
        meter = MeterFactory()
        self.session.commit()
        response = self._query(customer_code=meter.customer.code.upper())
        self.verify_response(response)

    def test_customer_phone_number(self):
        meter = MeterFactory()
        self.session.commit()
        response = self._query(customer_phone_number=meter.customer.phone_number)
        self.verify_response(response)

    def test_no_such_customer(self):
        response = self._query()
        self.verify_response(response)

    def test_customer_meters_only(self):
        MeterFactory(customer__name="Customer #1")
        MeterFactory(customer__name="Customer #2")
        TotalizerMeterFactory()
        TotalizerMeterFactory()
        self.session.commit()
        response = self._query(customers_only=True)
        self.verify_response(response)

    def test_all_meters(self):
        MeterFactory(customer__name="Customer #1")
        MeterFactory(customer__name="Customer #2")
        TotalizerMeterFactory()
        TotalizerMeterFactory()
        self.session.commit()
        response = self._query(customers_only=False)
        self.verify_response(response)

    def test_all_meters_with_reading_details(self):
        m1 = MeterFactory()
        m2 = MeterFactory()
        t = TotalizerMeterFactory(serial="SM200E-01-00000011")
        ReadingFactory(_meter=m1)
        ReadingFactory(_meter=m2)
        ReadingFactory(_meter=t)
        self.session.commit()
        response = self._query(reading_details=True)
        self.verify_response(response)

    def test_all_meters_with_reading_details_one_without(self):
        m1 = MeterFactory()
        MeterFactory()
        t = TotalizerMeterFactory(serial="SM200E-01-00000011")
        ReadingFactory(_meter=m1)
        ReadingFactory(_meter=t)
        self.session.commit()
        response = self._query(reading_details=True)
        self.verify_response(response)


class CustomersViewTest(APIView0TestCaseBase):
    path = "v0/customers/{id}"

    def test_get(self):
        self.session.commit()
        meter = MeterFactory()
        tags = [
            "A\\A",
            "B\\B",
            "C\\C",
            "D\\D",
            "E\\E",
            "F\\F",
            "G\\G",
            "H\\H",
            "I\\I",
            "J\\J",
            "K\\K",
            "L\\L",
            "M\\M",
            "N\\N",
            "O\\O",
            "P\\P",
            "Q\\Q",
            "R\\R",
            "S\\S",
            "T\\T",
            "U\\U",
            "V\\V",
            "W\\W",
            "X\\X",
            "Y\\Y",
            "Z\\Z",
            "a\\a",
            "b\\b",
            "c\\c",
            "d\\d",
            "e\\e",
            "f\\f",
            "g\\g",
            "h\\h",
            "i\\i",
            "j\\j",
            "k\\k",
            "l\\l",
            "m\\m",
            "n\\n",
            "o\\o",
            "p\\p",
            "q\\q",
            "r\\r",
            "s\\s",
            "t\\t",
            "u\\u",
            "v\\v",
            "w\\w",
            "x\\x",
            "y\\y",
            "z\\z",
        ]

        for tag in tags:
            MeterTag.add(tag, meter)
        self.session.commit()
        path = self.path.format(id=meter.customer.id)
        response = self.get(path)
        self.verify_response(response)

    def test_get_without_phone_number(self):
        meter = MeterFactory(customer__phone_number=None, customer__phone_number_verified=False)
        self.session.commit()

        path = self.path.format(id=meter.customer.id)
        response = self.get(path)
        self.verify_response(response)

    def test_no_such_customer(self):
        path = self.path.format(id="75d73108-080a-40d6-a98a-2c24a7974536")
        response = self.get(path)
        self.verify_response(response)

    def test_meter_state_values(self):
        meter = MeterFactory(system_info__current_state=MeterState.STATE_PROTECT.id)
        self.session.commit()
        response = self.get(self.path.format(id=meter.customer.id))
        self.verify_response(response)

    def test_get_with_partial_address(self):
        meter = MeterFactory(address__street1="123 Fake Street", address__postalcode=None)
        self.session.commit()

        path = self.path.format(id=meter.customer.id)
        response = self.get(path)
        self.verify_response(response)

    def test_get_with_reading_details(self):
        meter = MeterFactory()
        ReadingFactory(_meter=meter)
        self.session.commit()

        path = self.path.format(id=meter.customer.id)
        response = self.get(path + "?" + urllib.parse.urlencode({"reading_details": True}))
        self.verify_response(response)

    def test_current_daily_energy(self):
        meter = MeterFactory()
        self.session.commit()

        path = self.path.format(id=meter.customer.id)
        response = self.get(path)
        self.verify_response(response, variant="no-recorded-daily-energy")

        meter.billing.last_daily_energy_limit_reset_value = 0.0
        meter.system_info.last_energy = 10.0
        self.session.commit()
        response = self.get(path)
        self.verify_response(response, variant="recorded-daily-energy")


class CustomerViewCodeTest(APIView0TestCaseBase):
    path = "v0/customer/{code}"

    def test_get(self):
        MeterTag(name="tag1")
        MeterTag(name="tag2")
        self.session.commit()
        meter = MeterFactory()
        MeterTag.add("tag1", meter)
        MeterTag.add("tag2", meter)
        MeterTag.add("test\north", meter)
        self.session.commit()

        path = self.path.format(code=meter.customer.code.upper())
        response = self.get(path)
        self.verify_response(response)

    def test_get_with_reading_details(self):
        meter = MeterFactory()
        ReadingFactory(_meter=meter)
        self.session.commit()

        path = self.path.format(code=meter.customer.code.upper())
        response = self.get(path + "?" + urllib.parse.urlencode({"reading_details": True}))
        self.verify_response(response)

    def test_get_without_phone_number(self):
        meter = MeterFactory(customer__phone_number=None, customer__phone_number_verified=False)
        self.session.commit()

        path = self.path.format(code=meter.customer.code)
        response = self.get(path)
        self.verify_response(response)

    def test_no_such_customer(self):
        path = self.path.format(code="invalid-code")
        response = self.get(path)
        self.verify_response(response)


class CustomerAddTest(APIView0TestCaseBase):
    path = "v0/customer/"

    @pytest.fixture(autouse=True)
    def _setup_customer(self):
        self.tariff = TariffFactory(name="Tariff")
        self.session.commit()
        yield

    def _get_defaults(self, **params):
        args = []
        if "serial" not in params:
            args.append(("serial", "sm5r-00-00000001"))
        if "meter_tariff_name" not in params:
            args.append(("meter_tariff_name", "Tariff"))
        data = OrderedMultiDict(args)
        for key, value in params.items():
            if value is unset:
                continue
            data[key] = value
        return data

    def _post_json(self, **kwargs):
        data = self._get_defaults(**kwargs)
        response = self.post(self.path, json=data)
        return response

    def _verify_response(self, response):
        r = response.json()
        customer_id = r.get("customer_id")
        ignore_values = []
        if customer_id is not None:
            ignore_values.append(customer_id)
        if request.headers["Content-Type"] == "application/json":
            variant = "json"
        else:
            variant = "form"
        self.verify_response(response, ignore_values=ignore_values, variant=variant, frame=2)
        if customer_id:
            return MeterView.query.filter_by(customer_id=customer_id).one()

        assert MeterView.query.filter_by(customer_id=customer_id).count() == 0

    def test_created_form(self):
        response = self.post(self.path, data=self._get_defaults())
        meter_view = self._verify_response(response)
        assert meter_view.active is True
        assert meter_view.serial == "SM5R-00-00000001"
        assert meter_view.code == 1
        assert meter_view.ground_id == self.ground.id
        assert meter_view.customer_name == "new customer"
        assert meter_view.customer_code is None
        assert meter_view.customer_phone_number is None
        assert meter_view.customer_phone_number_verified is False
        assert meter_view.tariff_id == self.tariff.id
        assert meter_view.tariff_name == "Tariff"
        assert meter_view.state == MeterConfig.STATE_OFF
        assert meter_view.address_street1 is None
        assert meter_view.credit_value == 0

    def test_created_json(self):
        response = self._post_json(
            name="customer name",
            code="customer code",
            phone_number="+4632112345",
            operating_mode="auto",
            address="123 Main Street",
            tariff=self.tariff.name,
            starting_credit_balance=123,
            tags=["test", "test1", "test2"],
        )
        meter_view = self._verify_response(response)
        assert meter_view.serial == "SM5R-00-00000001"
        assert meter_view.code == 1
        assert meter_view.ground_id == self.ground.id
        assert meter_view.customer_name == "customer name"
        assert meter_view.customer_code == "customer code"
        assert meter_view.customer_phone_number == "+4632112345"
        assert meter_view.customer_phone_number_verified is True
        assert meter_view.tariff_id == self.tariff.id
        assert meter_view.tariff_name == "Tariff"
        assert meter_view.state == MeterConfig.STATE_AUTO
        assert meter_view.address_street1 == "123 Main Street"
        assert meter_view.credit_value == 123
        assert meter_view.tags == ["test", "test1", "test2"]

    def test_created_json_with_escaped_tags(self):
        response = self._post_json(
            name="customer name",
            code="customer code",
            phone_number="+4632112345",
            operating_mode="auto",
            address="123 Main Street",
            tariff=self.tariff.name,
            starting_credit_balance=123,
            tags=[r"test\details", r"test1\test", r"test2\north", r"test3\south"],
        )
        meter_view = self._verify_response(response)
        assert meter_view.serial == "SM5R-00-00000001"
        assert meter_view.code == 1
        assert meter_view.ground_id == self.ground.id
        assert meter_view.customer_name == "customer name"
        assert meter_view.customer_code == "customer code"
        assert meter_view.customer_phone_number == "+4632112345"
        assert meter_view.customer_phone_number_verified is True
        assert meter_view.tariff_id == self.tariff.id
        assert meter_view.tariff_name == "Tariff"
        assert meter_view.state == MeterConfig.STATE_AUTO
        assert meter_view.address_street1 == "123 Main Street"
        assert meter_view.credit_value == 123
        assert meter_view.tags == ["test\\details", "test1\\test", "test2\\north", "test3\\south"]

    def test_created_address_object(self):
        response = self._post_json(
            name="customer name",
            code="customer code",
            phone_number="+4632112345",
            operating_mode="auto",
            street1="1616 H St Nw",
            street2="Suite 900",
            city="Washington",
            state="DC",
            postalcode="20006",
            country="USA",
            tariff=self.tariff.name,
            starting_credit_balance=123,
        )
        meter_view = self._verify_response(response)
        assert meter_view.address_street1 == "1616 H St Nw"
        assert meter_view.address_street2 == "Suite 900"
        assert meter_view.address_city == "Washington"
        assert meter_view.address_state == "DC"
        assert meter_view.address_postalcode == "20006"
        assert meter_view.address_country == "USA"
        assert meter_view.address_coords is None

    def test_partial_address_object(self):
        response = self._post_json(
            name="customer name",
            code="customer code",
            state="DC",
            postalcode="20006",
            country="USA",
        )
        meter_view = self._verify_response(response)
        assert meter_view is None
        assert "Missing:" in response.text
        for field in ["city", "street1", "street2"]:
            assert field in response.text

    def test_address_field_and_partial_address_object(self):
        response = self._post_json(
            name="customer name",
            code="customer code",
            address="123 Fake Street",
            state="DC",
            postalcode="20006",
            country="USA",
        )
        self._verify_response(response)

    def test_address_field_and_address_object(self):
        response = self._post_json(
            name="customer name",
            code="customer code",
            phone_number="+4632112345",
            operating_mode="auto",
            address="123 Fake Street",
            street1="1616 H St Nw",
            street2="Suite 900",
            city="Washington",
            state="DC",
            postalcode="20006",
            country="USA",
            tariff=self.tariff.name,
            starting_credit_balance=123,
        )
        meter_view = self._verify_response(response)
        assert meter_view.address_street1 == "1616 H St Nw"
        assert meter_view.address_street2 == "Suite 900"
        assert meter_view.address_city == "Washington"
        assert meter_view.address_state == "DC"
        assert meter_view.address_postalcode == "20006"
        assert meter_view.address_country == "USA"

    def test_address_field_allow_null(self):
        response = self._post_json(
            name="customer name",
            code="customer code",
            address=None,
        )
        self._verify_response(response)
        assert response.status_code == 201

    def test_address_field_type_validation(self):
        response = self._post_json(
            name="customer name",
            code="customer code",
            address={},
        )
        self._verify_response(response)
        assert response.status_code == 400
        assert "must be a string" in response.text

    def test_coords(self):
        response = self._post_json(
            name="customer name",
            code="customer code",
            coords="1,1",
        )
        meter_view = self._verify_response(response)
        assert meter_view.address_coords == "1,1"

    def test_serial_lower_case(self):
        response = self._post_json(tariff=self.tariff.name, serial="sm15r-00-00000001")
        meter_view = self._verify_response(response)
        assert meter_view.serial == "SM15R-00-00000001"

    @mock.patch("sparkmeter.api.customerviews0.MeterView")
    def test_unknown_server_error(self, MeterView):
        MeterView.create_meter.side_effect = MeterError("unknown", "Unknown message")
        response = self._post_json(tariff=self.tariff.name, serial="sm15r-00-00000001")
        meter_view = self._verify_response(response)
        assert meter_view is None

    def test_ground_multiple(self):
        g2 = GroundFactory()
        self.session.commit()
        response = self._post_json(ground_serial=g2.serial)
        meter_view = self._verify_response(response)
        assert meter_view.ground_serial == g2.serial

    def test_ground_serial_missing(self):
        GroundFactory()
        self.session.commit()
        response = self._post_json()
        meter_view = self._verify_response(response)
        assert meter_view is None

    def test_ground_serial_no_such_ground(self):
        GroundFactory()
        self.session.commit()
        response = self._post_json(ground_serial="does-not-exist")
        meter_view = self._verify_response(response)
        assert meter_view is None

    def test_serial_missing(self):
        response = self._post_json(serial=unset)
        meter_view = self._verify_response(response)
        assert meter_view is None

    def test_serial_invalid(self):
        response = self._post_json(serial="invalid-serial")
        meter_view = self._verify_response(response)
        assert meter_view is None

        response = self._post_json(serial="SM15R-01-FFFFFFFF")
        customer_id = response.json().get("customer_id")
        meter_view = MeterView.query.filter_by(customer_id=customer_id).one()
        assert meter_view is not None
        assert meter_view.code == 0xFFFF
        assert meter_view.serial == "SM15R-01-FFFFFFFF"

    def test_serial_already_exists(self):
        m = MeterFactory()
        self.session.commit()
        response = self._post_json(serial=m.serial)
        meter_view = self._verify_response(response)
        assert meter_view is None

    def test_32_bit_serial(self):
        response = self._post_json(
            name="customer name",
            code="customer code",
            phone_number="+4632112345",
            operating_mode="auto",
            address="123 Main Street",
            tariff=self.tariff.name,
            starting_credit_balance=123,
            serial="SM5R-00-00010001",
        )
        meter_view = self._verify_response(response)
        assert meter_view.serial == "SM5R-00-00010001"
        assert meter_view.code == 1

    def test_code_already_exists(self):
        m = MeterFactory(code=2, customer__code="customer-code")
        self.session.commit()
        response = self._post_json(code=m.customer.code)
        meter_view = self._verify_response(response)
        assert meter_view is None

    def test_code_bad_type(self):
        response = self._post_json(code=1234)
        meter_view = self._verify_response(response)
        assert meter_view is None

    def test_code_multiple_empty(self):
        m = MeterFactory(code=2)
        m.customer.code = None
        self.session.commit()
        response = self._post_json(code=None)
        meter_view = self._verify_response(response)
        assert meter_view is not None
        assert meter_view.customer_code is None

    def test_phone_number_invalid(self):
        response = self._post_json(phone_number="+55")
        meter_view = self._verify_response(response)
        assert meter_view is None

    def test_meter_tariff_name_missing(self):
        response = self._post_json(meter_tariff_name=unset)
        meter_view = self._verify_response(response)
        assert meter_view is None

    def test_meter_tariff_name_not_found(self):
        response = self._post_json(meter_tariff_name="Foobar")
        meter_view = self._verify_response(response)
        assert meter_view is None

    def test_state_invalid(self):
        response = self._post_json(operating_mode="sliff")
        meter_view = self._verify_response(response)
        assert meter_view is None

    def test_state_invalid_int(self):
        response = self._post_json(operating_mode=123)
        meter_view = self._verify_response(response)
        assert meter_view is None

    def test_starting_credit_balance_invalid(self):
        response = self._post_json(starting_credit_balance="sliff")
        meter_view = self._verify_response(response)
        assert meter_view is None

    def test_tags_invalid(self):
        response = self._post_json(tags="invalid-tags")
        meter_view = self._verify_response(response)
        assert meter_view is None

    def test_tags_invalid_with_commas(self):
        response = self._post_json(tags=["invalid,tags"])
        meter_view = self._verify_response(response)
        assert meter_view is None

    def test_tags_invalid_with_spaces(self):
        response = self._post_json(tags=["invalid tags"])
        meter_view = self._verify_response(response)
        assert meter_view is None

    def test_tags_invalid_with_non_strings(self):
        response = self._post_json(tags=[543, None])
        meter_view = self._verify_response(response)
        assert meter_view is None

    def test_tags_invalid_empty(self):
        response = self._post_json(tags=[""])
        meter_view = self._verify_response(response)
        assert meter_view is None


class CustomerEditTest(APIView0TestCaseBase):
    path = "v0/customers/{id}"

    @pytest.fixture(autouse=True)
    def _setup_customer(self):
        self.meter = MeterFactory()
        self.session.commit()
        yield

    def _test(self, frame=2, **kwargs):
        path = self.path.format(id=self.meter.customer.id)
        response = self.put(path, json=kwargs)
        self.verify_response(response, frame=frame)
        return MeterView.get_by_customer_id(self.meter.customer.id)

    def _test_form_data(self, data):
        path = self.path.format(id=self.meter.customer.id)
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        response = self.put(path, data=data, headers=headers)
        self.verify_response(response, frame=2)
        return MeterView.get_by_customer_id(self.meter.customer.id)

    def _check_modified(self, meter_view, **changes):
        kwargs = dict(
            customer_name=self.meter.customer.name,
            customer_code=self.meter.customer.code,
            customer_phone_number=self.meter.customer.phone_number,
            tariff_name=self.meter.tariff.name,
            state=self.meter.config.state,
            address_street1=self.meter.address.street1,
            active=not self.meter.config.hidden,
        )
        kwargs.update(changes)

        for key, expected_value in kwargs.items():
            current_value = getattr(meter_view, key)
            msg = "{} on meter view was different, expected {}, but got {}"
            assert current_value == expected_value, msg.format(key, expected_value, current_value)

    def test_invalid_customer_id(self):
        path = self.path.format(id="invalid-customer-id")
        response = self.put(path, json={})
        self.verify_response(response)

    def test_customer_not_found(self):
        path = self.path.format(id="e2b94357-4b34-4871-86ef-51745a6247d4")
        response = self.put(path, json={})
        self.verify_response(response)

    def test_missing_params(self):
        self._test()

    def test_invalid_params(self):
        self._test(this_is_not_a_real_param="yes")

    def test_mismatched_content_type(self):
        self._test_form_data(data='{"name": "new name"}')

    def test_update_name(self):
        meter_view = self._test(name="new name")
        self._check_modified(meter_view, customer_name="new name")

    def test_update_code(self):
        meter_view = self._test(code="new code")
        self._check_modified(meter_view, customer_code="new code")

    def test_update_code_already_exists(self):
        MeterFactory(customer__code="exists")
        self.session.commit()
        self._test(code="exists")

    def test_code_bad_type(self):
        meter_view = self._test(code=1234)
        self._check_modified(meter_view)

    def test_update_phone_number(self):
        meter_view = self._test(phone_number="+123456789")
        self._check_modified(meter_view, customer_phone_number="+123456789")

    def test_update_phone_number_wrong_type(self):
        meter_view = self._test(phone_number=+1234)
        assert meter_view is not None

    def test_update_meter_tariff_name(self):
        TariffFactory(name="T2")
        self.session.commit()
        meter_view = self._test(meter_tariff_name="t2")
        self._check_modified(meter_view, tariff_name="T2")

    def test_update_meter_tariff_events_cloud(self, config):
        TariffFactory(name="T2")
        self.session.commit()
        config["HEROKU"] = True
        meter_view = self._test(meter_tariff_name="t2")
        events = Event.query.all()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == Event.TYPE_METER_TARIFF_CHANGED
        assert event.object.id == meter_view.meter.id
        assert not event.processed

    def test_update_meter_tariff_events_ground(self, config, send_set_config):
        TariffFactory(name="T2")
        self.session.commit()
        config["HEROKU"] = False
        meter_view = self._test(meter_tariff_name="t2")
        events = Event.query.all()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == Event.TYPE_METER_TARIFF_CHANGED
        assert event.object.id == meter_view.meter.id
        assert event.processed

    def test_update_meter_tariff_no_events(self, config):
        config["HEROKU"] = True
        self._test(meter_tariff_name=self.meter.tariff.name)
        events = Event.query.all()
        assert len(events) == 0

    def test_update_meter_tariff_name_not_found(self):
        self._test(meter_tariff_name="not-found")

    def test_update_operating_mode_off(self):
        meter_view = self._test(operating_mode="off")
        self._check_modified(meter_view, state=0)

    def test_update_operating_mode_change_events_cloud(self, config):
        config["HEROKU"] = True
        meter_view = self._test(operating_mode="off")
        events = Event.query.all()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == Event.TYPE_METER_STATE_CHANGED
        assert event.object.id == meter_view.meter.id
        assert not event.processed

    def test_update_operating_mode_change_events_ground(self, send_set_config, config):
        config["HEROKU"] = False
        meter_view = self._test(operating_mode="off")
        events = Event.query.all()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == Event.TYPE_METER_STATE_CHANGED
        assert event.object.id == meter_view.meter.id
        assert event.processed

    def test_update_operating_mode_on(self):
        meter_view = self._test(operating_mode="on")
        self._check_modified(meter_view, state=1)

    def test_update_operating_mode_auto(self):
        meter_view = self._test(operating_mode="auto")
        self._check_modified(meter_view, state=2)

    def test_update_operating_mode_unchanged_events(self, config):
        config["HEROKU"] = True
        self._test(operating_mode="auto")
        events = Event.query.all()
        assert len(events) == 0

    def test_update_operating_mode_invalid(self):
        self._test(operating_mode="invalid")

    def test_update_address(self):
        meter_view = self._test(address="new address")
        self._check_modified(meter_view, address_street1="new address")

    def test_update_address_object(self):
        meter_view = self._test(
            street1="1616 H St Nw",
            street2="Suite 900",
            city="Washington",
            state="DC",
            postalcode="20006",
            country="usa",
            coords=None,
        )
        self._check_modified(meter_view, address_street1="1616 H St Nw")

    def test_update_partial_address_object(self):
        meter_view = self._test(street1="1616 H St Nw")
        self._check_modified(meter_view, address_street1="strëet")

    def test_update_address_field_and_address_object(self):
        meter_view = self._test(
            address="123 Fake Street",
            street1="1616 H St Nw",
            street2="Suite 900",
            city="Washington",
            state="DC",
            postalcode="20006",
            country="usa",
            coords=None,
        )
        self._check_modified(meter_view, address_street1="1616 H St Nw")

    def test_update_active(self):
        meter_view = self._test(active=False)
        self._check_modified(meter_view, active=False)

    def test_update_operating_mode_and_tariff_change_events(self, config):
        TariffFactory(name="T2")
        self.session.commit()
        config["HEROKU"] = True
        meter_view = self._test(operating_mode="on", meter_tariff_name="t2")
        events = Event.query.all()
        assert len(events) == 2
        operating_event = list(filter(lambda ev: ev.event_type == Event.TYPE_METER_STATE_CHANGED, events))
        assert len(operating_event) == 1
        assert operating_event[0].object.id == meter_view.meter.id
        tariff_event = list(filter(lambda ev: ev.event_type == Event.TYPE_METER_TARIFF_CHANGED, events))
        assert len(tariff_event) == 1
        assert operating_event[0].object.id == meter_view.meter.id

    def test_update_ignore_customer_code_if_same_customer(self, config):
        meter_view = self._test(name="New Name", code=self.meter.customer.code)
        self._check_modified(meter_view, customer_name="New Name")

    def _test_update_tags(self, old_tags, new_tags, frame=3):
        """A helper method to test updating customer tags, mainly saving on typing

        :param old_tags: Existing/Old set of tags associated to a meter
        :param old_tags: list

        :param new_tags: New set of tags to be added to a meter
        :param new_tags: list
        """
        for tag in old_tags:
            MeterTag.add(tag, self.meter)
        self.session.commit()
        meter_view = MeterView.get_by_customer_id(self.meter.customer.id)
        assert meter_view.tags == old_tags
        meter_view = self._test(tags=new_tags, frame=frame)
        assert sorted(meter_view.tags) == sorted(new_tags)

    def test_update_tags_remove_existing_add_new(self):
        existing_tags = ["existing-tag", "existing-tag1"]
        new_tags = ["existing-tag", "new-tag", "new-tag1"]
        self._test_update_tags(existing_tags, new_tags)

    def test_update_tags_replace_existing_with_new(self):
        existing_tags = ["existing-tag", "existing-tag1"]
        new_tags = ["new-tag", "new-tag1"]
        self._test_update_tags(existing_tags, new_tags)

    def test_update_tags_contains_whitespace(self):
        existing_tags = ["existing-tag", "existing-tag1"]
        new_tags = ["asdf\nasdf", "asdf\rasdf", "asdf\fadsf", "asdf\tasdf"]
        for tag in existing_tags:
            MeterTag.add(tag, self.meter)
        self.session.commit()
        meter_view = MeterView.get_by_customer_id(self.meter.customer.id)
        assert meter_view.tags == existing_tags
        self._test(tags=new_tags, frame=3)
        assert sorted(meter_view.tags) == sorted(["asdf\\nasdf", "asdf\\rasdf", "asdf\\fadsf", "asdf\\tasdf"])

    def test_update_tags_with_empty_list(self):
        existing_tags = ["existing-tag", "existing-tag1"]
        new_tags = []
        self._test_update_tags(existing_tags, new_tags)

    def test_update_tags_remove_existing_add_escaped_tags(self):
        existing_tags = ["existing-tag", "existing-tag1"]
        new_tags = [
            "existing-tag",
            "new\\south",
            "new\\north",
            "new\\west",
            "new\\test",
            "new\\asdf",
            "new\\bsdf",
        ]
        self._test_update_tags(existing_tags, new_tags)

    def test_update_tags_invalid(self):
        self._test(tags="invalid tags")

    def test_update_tags_invalid_spaces(self):
        self._test(tags=["invalid tags"])

    def test_update_tags_invalid_commas(self):
        self._test(tags=["invalid,tags"])

    def test_update_tags_invalid_non_string(self):
        self._test(tags=[540, None])

    def test_update_tags_invalid_empty_tag(self):
        self._test(tags=[""])

    def test_update_tags_invalid_unescaped_backslash(self):
        meter_view = self._test(tags=["asdf\asdf", "asdf\bsdf"])
        assert sorted(meter_view.tags) == sorted(["asdf\\asdf", "asdf\\bsdf"])


class CustomerWalletZeroTest(APIView0TestCaseBase):
    path = "v0/customers/{id}/wallet/{wallet}/zero-balance"

    @pytest.fixture(autouse=True)
    def _setup_customer(self):
        self.system_sales = SalesAccount.get_system()
        self.user_sales_account = self.user.api_sales_account
        self.user.api_sales_account = self.system_sales
        self.meter = MeterFactory()
        self.session.commit()
        yield

    def test_invalid_customer_id(self):
        path = self.path.format(id="invalid-customer-id", wallet="credit")
        response = self.post(path)
        self.verify_response(response)

    def test_customer_not_found(self):
        path = self.path.format(id="e2b94357-4b34-4871-86ef-51745a6247d4", wallet="credit")
        response = self.post(path)
        self.verify_response(response)

    def test_invalid_wallet(self):
        path = self.path.format(id=self.meter.customer.id, wallet="coinpurse")
        response = self.post(path)
        self.verify_response(response)

    def test_sales_account_cannot_sell(self):
        self.user.api_sales_account = self.user_sales_account
        self.session.commit()
        path = self.path.format(id=self.meter.customer.id, wallet="credit")
        response = self.post(path)
        self.verify_response(response)

    def test_successful(self):
        path = self.path.format(id=self.meter.customer.id, wallet="credit")
        response = self.post(path)
        data = response.json()
        self.verify_response(response, ignore_values=[data["event_id"]])
        event = Event.get_by_id(data["event_id"])
        assert event.id is not None
        assert event.event_type == Event.TYPE_CUSTOMER_WALLET_ZERO_REQUESTED


class CustomerResetMeterTest(APIView0TestCaseBase):
    path = "v0/customers/{id}/reset-meter"

    def _setup_customer(self, meter_type="customer"):
        self.meter = MeterFactory()
        self.meter.meter_type = meter_type
        self.session.commit()
        return MeterView.get_by_customer_id(self.meter.customer.id)

    def test_customer_id_invalid(self):
        path = self.path.format(id="invalid-customer-id")
        response = self.post(path)
        self.verify_response(response)

    def test_customer_not_found(self):
        path = self.path.format(id="e2b94357-4b34-4871-86ef-51745a6247d4")
        response = self.post(path)
        self.verify_response(response)

    def test_meter_type_invalid(self):
        customer = self._setup_customer(meter_type="custom_type")
        path = self.path.format(id=customer.customer_id)
        response = self.post(path)
        self.verify_response(response)

    def test_successful(self):
        customer = self._setup_customer()
        path = self.path.format(id=customer.customer_id)
        assert Event.query.filter(Event.event_type == Event.TYPE_METER_STATE_CHANGED).count() == 0
        response = self.post(path)
        self.verify_response(response)
        assert Event.query.filter(Event.event_type == Event.TYPE_METER_STATE_CHANGED).count() == 1
