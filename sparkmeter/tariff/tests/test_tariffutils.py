import json
import operator
from unittest import mock

import sparkmeter.tariff.tariffutils as tu
from sparkmeter.constants import MAX_SIGNED_INT
from sparkmeter.event.eventdomain import Event
from sparkmeter.meter.meterdomain import MeterConfig
from sparkmeter.tariff.tariffdomain import Tariff
from sparkmeter.tariff.tariffform import TariffForm
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import MeterFactory, TariffFactory


class TestTariffModification(SparkMeterTestCaseBase):
    def test_create(self):
        form = TariffForm.from_json(
            {
                "name": "TARIFF",
                "flat_load_limit": 150,
                "plan_price": 0,
                "cycle_start_day_of_month": 1,
                "tariff_type": "flat",
                "flat_price": 4,
            }
        )
        tariff = tu.add_tariff_from_form(form, session=self.session)
        assert tariff is not None
        assert tariff.name == "TARIFF"
        assert tariff.flat_load_limit == 150
        assert tariff.plan_price == 0
        assert tariff.cycle_start_day_of_month == 1
        assert tariff.tariff_type == "flat"
        assert tariff.flat_price == 4
        assert len(tariff.tous) == 0
        assert len(tariff.blockrates) == 0
        assert tariff.id is not None
        tariffs = Tariff.query.all()
        assert len(tariffs) == 1

    def test_create_error_validation(self):
        form = TariffForm.from_json(
            {
                "name": "TARIFF",
                "flat_load_limit": 150,
                "plan_price": 0,
                "plan_duration_and_start_day": "1m30",
                "tariff_type": "flat",
                "flat_price": 4,
            }
        )
        tariff = tu.add_tariff_from_form(form, session=self.session)
        assert tariff is None
        assert len(form.plan_duration_and_start_day.errors) == 1
        assert form.plan_duration_and_start_day.errors[0] == "Not a valid choice."
        assert len(Tariff.query.all()) == 0

    def test_update_cloud(self, config, send_set_config):
        config["HEROKU"] = True
        tariff = TariffFactory(name="Tariff", flat_price=3, flat_load_limit=30)
        MeterFactory(code=1, config__state=MeterConfig.STATE_AUTO, tariff=tariff)
        self.session.commit()
        form = TariffForm.from_json(
            {
                "name": "Tariff",
                "flat_price": 4,
                "flat_load_limit": 30,
                "load_limit_type": "flat",
            }
        )
        updated = tu.update_tariff_from_form(tariff, form, session=self.session)
        assert updated is not None, form.errors
        assert updated.name == "Tariff"
        assert updated.flat_price == 4
        assert updated.load_limit_type == "flat"
        assert updated.id == tariff.id
        assert not send_set_config.called
        events = Event.query.all()
        assert len(events) == 0

    def test_update_error_validation(self, config, send_set_config):
        config["HEROKU"] = True
        tariff = TariffFactory(name="Tariff", flat_price=3, flat_load_limit=30)
        MeterFactory(code=1, config__state=MeterConfig.STATE_AUTO, tariff=tariff)
        self.session.commit()
        form = TariffForm.from_json(
            {"name": "Tariff", "flat_price": -1, "flat_load_limit": 30, "load_limit_type": "flat"}
        )
        updated = tu.update_tariff_from_form(tariff, form, session=self.session)
        assert updated is None
        assert len(form.flat_price.errors) == 1
        assert form.flat_price.errors[0] == "Flat Rate cannot be negative"
        events = Event.query.all()
        assert len(events) == 0

    def test_update_cloud_load_limit_change(self, config, send_set_config):
        config["HEROKU"] = True
        tariff = TariffFactory(name="Tariff", flat_price=3, flat_load_limit=30)
        MeterFactory(code=1, config__state=MeterConfig.STATE_AUTO, tariff=tariff)
        MeterFactory(code=2, config__state=MeterConfig.STATE_AUTO, tariff=tariff)
        MeterFactory(code=3, config__state=MeterConfig.STATE_AUTO)
        self.session.commit()
        form = TariffForm.from_json(
            {"name": "Tariff", "flat_price": 4, "flat_load_limit": 20, "load_limit_type": "flat"}
        )
        updated = tu.update_tariff_from_form(tariff, form, session=self.session)
        assert updated is not None
        assert updated.flat_load_limit == 20
        assert updated.id == tariff.id
        events = Event.query.all()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == Event.TYPE_TARIFF_POWER_LIMIT_CHANGED
        assert event.object.id == updated.id
        assert not event.processed
        assert not send_set_config.called

    def test_update_ground_load_limit_change(self, config, send_set_config):
        config["HEROKU"] = False
        tariff = TariffFactory(name="Tariff", flat_price=3, flat_load_limit=30)
        MeterFactory(code=1, config__state=MeterConfig.STATE_AUTO, tariff=tariff)
        MeterFactory(code=2, config__state=MeterConfig.STATE_AUTO, tariff=tariff)
        MeterFactory(code=3, config__state=MeterConfig.STATE_AUTO)
        self.session.commit()
        form = TariffForm.from_json(
            {"name": "Tariff", "flat_price": 4, "flat_load_limit": 20, "load_limit_type": "flat"}
        )
        updated = tu.update_tariff_from_form(tariff, form, session=self.session)
        assert updated is not None
        assert updated.flat_load_limit == 20
        assert updated.id == tariff.id
        events = Event.query.all()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == Event.TYPE_TARIFF_POWER_LIMIT_CHANGED
        assert event.object.id == updated.id
        assert event.processed
        # Config is sent to all meters using this tariff (meters 1 and 2)
        assert send_set_config.call_count == 2


class TestTariffValidation(SparkMeterTestCaseBase):
    @staticmethod
    def get_form(data):
        return TariffForm.from_json(data)

    @staticmethod
    def get_tariff(data):
        form = TestTariffValidation.get_form(data)
        tariff = Tariff()
        form.populate_obj(tariff)
        return form, tariff

    def test_validate_name(
        self,
    ):
        form, tariff = self.get_tariff({"name": "TARIFF"})
        tu._validate_name(form, tariff)
        assert len(form.name.errors) == 0

    def test_validate_name_error_empty(self):
        form, tariff = self.get_tariff({"name": ""})
        tu._validate_name(form, tariff)
        assert len(form.name.errors) == 1
        assert form.name.errors[0] == "Please set a name for this tariff"

    def test_validate_name_error_existing_same_id(self):
        t = TariffFactory(name="TARIFF")
        self.session.commit()
        form, tariff = self.get_tariff({"id": t.id, "name": "TARIFF"})
        tu._validate_name(form, tariff)
        assert len(form.name.errors) == 0, [str(err) for err in form.name.errors]

    def test_validate_name_error_existing_different_id(self):
        TariffFactory(name="TARIFF")
        self.session.commit()
        form, tariff = self.get_tariff({"id": "709e44f3-baa0-42f5-8481-9e77f0143302", "name": "TARIFF"})
        tu._validate_name(form, tariff)
        assert len(form.name.errors) == 1
        assert form.name.errors[0] == 'A tariff with the name "TARIFF" already exists'

    def test_validate_name_error_multiple_existing(self):
        t1 = TariffFactory(name="TARIFF")
        TariffFactory(name="TARIFF")
        self.session.commit()
        form, tariff = self.get_tariff({"id": t1.id, "name": "TARIFF"})
        tu._validate_name(form, tariff)
        assert len(form.name.errors) == 1
        assert form.name.errors[0] == 'A tariff with the name "TARIFF" already exists'

    def test_validate_plan_duration_and_start_day(self):
        form, _ = self.get_tariff(
            {
                "plan_duration_and_start_day": "1m2",
            }
        )
        tu._validate_plan_duration_and_start_day(form)
        assert len(form.plan_duration_and_start_day.errors) == 0

    def test_validate_start_day_of_month_out_of_range(self):
        form, _ = self.get_tariff(
            {
                "plan_duration_and_start_day": "1m30",
            }
        )
        tu._validate_plan_duration_and_start_day(form)
        assert len(form.plan_duration_and_start_day.errors) == 1
        assert form.plan_duration_and_start_day.errors[0] == "Not a valid choice."

    def test_validate_start_day_of_month_noninteger(self):
        form = self.get_form(
            {
                "plan_duration_and_start_day": "1m1.5",
            }
        )
        tu._validate_plan_duration_and_start_day(form)
        assert len(form.plan_duration_and_start_day.errors) == 1
        assert form.plan_duration_and_start_day.errors[0] == "Not a valid choice."

    def test_validate_load_limits_flat(self):
        form, tariff = self.get_tariff({"load_limit_type": "flat", "flat_load_limit": 5})
        tu._validate_load_limits(form, tariff)
        assert len(form.flat_load_limit.errors) == 0
        assert len(tariff.load_limits) == 0

    def test_validate_load_limits_flat_missing(self):
        form, tariff = self.get_tariff(
            {
                "load_limit_type": "flat",
            }
        )
        tu._validate_load_limits(form, tariff)
        assert len(form.flat_load_limit.errors) == 1
        assert form.flat_load_limit.errors[0] == "Please enter a Load Limit for this tariff"

    def test_validate_load_limits_flat_overflow(self):
        form, tariff = self.get_tariff(
            {
                "load_limit_type": "flat",
                "flat_load_limit": MAX_SIGNED_INT + 1,
            }
        )
        tu._validate_load_limits(form, tariff)
        assert len(form.flat_load_limit.errors) == 1
        assert form.flat_load_limit.errors[0] == "Load Limit must be less than or equal to {}".format(
            MAX_SIGNED_INT
        )  # noqa

    def test_validate_load_limits_flat_negative(self):
        form, tariff = self.get_tariff({"load_limit_type": "flat", "flat_load_limit": -5})
        tu._validate_load_limits(form, tariff)
        assert len(form.flat_load_limit.errors) == 1
        assert form.flat_load_limit.errors[0] == "Load Limits cannot be negative"

    @mock.patch.object(Tariff, "validate_load_limits")
    def test_validate_load_limits_scheduled(self, validate_method):
        form, tariff = self.get_tariff(
            {
                "load_limit_type": "scheduled",
                "load_limits": json.dumps(
                    [
                        {"start": "00:00", "end": "18:00", "value": 1},
                        {"start": "18:00", "end": "22:00", "value": 2},
                        {"start": "22:00", "end": "24:00", "value": 3.5},
                    ]
                ),
            }
        )
        tu._validate_load_limits(form, tariff)
        assert len(form.load_limits.errors) == 0
        validate_method.assert_called_once()
        assert len(tariff.load_limits) == 3
        limits = list(sorted(tariff.get_load_limits(), key=operator.attrgetter("value")))
        assert limits[0].start == "00:00"
        assert limits[0].end == "18:00"
        assert limits[0].value == 1
        assert limits[1].start == "18:00"
        assert limits[1].end == "22:00"
        assert limits[1].value == 2
        assert limits[2].start == "22:00"
        assert limits[2].end == "00:00"
        assert limits[2].value == 3.5

    @mock.patch.object(Tariff, "validate_load_limits", side_effect=ValueError)
    def test_validate_load_limits_scheduled_invalid(self, validate_method):
        form, tariff = self.get_tariff(
            {
                "load_limit_type": "scheduled",
            }
        )
        tu._validate_load_limits(form, tariff)
        assert len(form.load_limits.errors) == 1
        assert isinstance(form.load_limits.errors[0], ValueError)
        validate_method.assert_called_once()
        assert len(tariff.load_limits) == 0

    def test_validate_plan(self):
        form, _ = self.get_tariff(
            {
                "plan_price": 0,
                "plan_fixed_fee": 0,
            }
        )
        tu._validate_plan(form)
        assert len(form.plan_price.errors) == 0
        assert len(form.plan_fixed_fee.errors) == 0

    def test_validate_plan_errors(self):
        form, _ = self.get_tariff(
            {
                "plan_price": -1,
                "plan_fixed_fee": -1,
            }
        )
        tu._validate_plan(form)
        assert len(form.plan_price.errors) == 1
        assert form.plan_price.errors[0] == "Number must be at least 0."
        assert len(form.plan_fixed_fee.errors) == 1
        assert form.plan_fixed_fee.errors[0] == "Number must be at least 0."

    def test_validate_tariff_type_flat(self):
        form, tariff = self.get_tariff(
            {
                "tariff_type": "flat",
                "flat_price": 4,
            }
        )
        tu._validate_tariff_type(form, tariff)
        assert len(form.flat_price.errors) == 0

    def test_validate_tariff_type_flat_no_price(self):
        form, tariff = self.get_tariff(
            {
                "tariff_type": "flat",
            }
        )
        tu._validate_tariff_type(form, tariff)
        assert len(form.flat_price.errors) == 1
        assert form.flat_price.errors[0] == "Please set a Flat Rate"

    @mock.patch.object(Tariff, "validate_blockrates")
    def test_validate_tariff_type_blockrate(self, validate_method):
        form, tariff = self.get_tariff(
            {
                "tariff_type": "blockrate",
            }
        )
        tu._validate_tariff_type(form, tariff)
        validate_method.assert_called_once()
        assert len(form.blockrates.errors) == 0

    @mock.patch.object(Tariff, "validate_blockrates", side_effect=ValueError)
    def test_validate_tariff_type_blockrate_invalid(self, validate_method):
        form, tariff = self.get_tariff(
            {
                "tariff_type": "blockrate",
            }
        )
        tu._validate_tariff_type(form, tariff)
        validate_method.assert_called_once()
        assert len(form.blockrates.errors) == 1
        assert isinstance(form.blockrates.errors[0], ValueError)

    def test_validate_flat_price(self):
        form, tariff = self.get_tariff({"flat_price": 1})
        tu._validate_flat_price(form, tariff)
        assert len(form.flat_price.errors) == 0

    def test_validate_flat_price_negative(self):
        form, tariff = self.get_tariff({"flat_price": -1})
        tu._validate_flat_price(form, tariff)
        assert len(form.flat_price.errors) == 1
        assert form.flat_price.errors[0] == "Flat Rate cannot be negative"

    @mock.patch.object(Tariff, "validate_tous")
    def test_validate_tous(self, validate_method):
        form, tariff = self.get_tariff(
            {
                "tous": json.dumps(
                    [
                        {
                            "end": "24:00",
                            "id": "612aaccf-a86f-486e-82b4-3abd136f34ef",
                            "start": "00:00",
                            "value": 100,
                        }
                    ]
                ),
                "tou_enabled": True,
            }
        )
        tu._validate_tous(form, tariff)
        assert len(form.tous.errors) == 0
        assert tariff.tous[0]["end"] == "00:00"
        validate_method.assert_called_once()

    @mock.patch.object(Tariff, "validate_tous")
    def test_validate_tous_disabled(self, validate_method):
        form, tariff = self.get_tariff(
            {
                "tous": json.dumps(
                    [
                        {
                            "end": "24:00",
                            "id": "612aaccf-a86f-486e-82b4-3abd136f34ef",
                            "start": "00:00",
                            "value": 100,
                        }
                    ]
                ),
                "tou_enabled": False,
            }
        )
        tu._validate_tous(form, tariff)
        assert len(form.tous.errors) == 0
        assert tariff.tous[0]["end"] == "00:00"
        assert not validate_method.called

    @mock.patch.object(Tariff, "validate_tous", side_effect=ValueError)
    def test_validate_tous_validation_error(self, validate_method):
        form, tariff = self.get_tariff(
            {
                "tous": json.dumps(
                    [
                        {
                            "end": "24:00",
                            "id": "612aaccf-a86f-486e-82b4-3abd136f34ef",
                            "start": "00:00",
                            "value": 100,
                        }
                    ]
                ),
                "tou_enabled": True,
            }
        )
        tu._validate_tous(form, tariff)
        assert len(form.tous.errors) == 1
        assert isinstance(form.tous.errors[0], ValueError)

    def test_validate_daily_energy_limit(self):
        form, tariff = self.get_tariff(
            {
                "daily_energy_limit_enabled": True,
                "daily_energy_limit_value": 1,
                "daily_energy_limit_reset_hour": 10,
            }
        )
        tu._validate_daily_energy_limit(form, tariff)
        assert len(form.daily_energy_limit_value.errors) == 0
        assert len(form.daily_energy_limit_reset_hour.errors) == 0

    def test_validate_daily_energy_limit_negative_value(self):
        form, tariff = self.get_tariff(
            {
                "daily_energy_limit_enabled": True,
                "daily_energy_limit_value": -1,
                "daily_energy_limit_reset_hour": 0,
            }
        )
        tu._validate_daily_energy_limit(form, tariff)
        assert len(form.daily_energy_limit_value.errors) == 1
        error_msg = "Daily Energy Limit Value must be greater than or equal to 0"
        assert form.daily_energy_limit_value.errors[0] == error_msg

    def test_validate_daily_energy_limit_hour_less_than_0(self):
        form, tariff = self.get_tariff(
            {
                "daily_energy_limit_enabled": True,
                "daily_energy_limit_value": 1,
                "daily_energy_limit_reset_hour": -1,
            }
        )
        tu._validate_daily_energy_limit(form, tariff)
        assert len(form.daily_energy_limit_reset_hour.errors) == 1
        error_msg = "Daily Energy Limit Reset Hour must be between 0 and 23 hours"
        assert form.daily_energy_limit_reset_hour.errors[0] == error_msg

    def test_validate_daily_energy_limit_hour_more_than_23(self):
        form, tariff = self.get_tariff(
            {
                "daily_energy_limit_enabled": True,
                "daily_energy_limit_value": 1,
                "daily_energy_limit_reset_hour": 24,
            }
        )
        tu._validate_daily_energy_limit(form, tariff)
        assert len(form.daily_energy_limit_reset_hour.errors) == 1
        error_msg = "Daily Energy Limit Reset Hour must be between 0 and 23 hours"
        assert form.daily_energy_limit_reset_hour.errors[0] == error_msg
