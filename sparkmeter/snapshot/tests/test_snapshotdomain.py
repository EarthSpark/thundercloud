"""Test the snapshot domain."""

import json

import pytest

from sparkmeter.meter.meterdomain import Meter, MeterView
from sparkmeter.snapshot.snapshotdomain import Snapshot, _maybe_json, get_meter_view_snapshot
from sparkmeter.tests.base import SparkMeterTestCaseBase
from sparkmeter.tests.test_data_factory import (
    MeterFactory,
    SalesAccountFactory,
    TariffFactory,
    TotalizerMeterFactory,
)


class SnapshotTest(SparkMeterTestCaseBase):
    """Test snapshots."""

    def test_meter_view_snapshot_customer(self):
        MeterFactory(
            customer__name="Customer 1",
            customer__phone_number="+123456",
            customer__phone_number_verified=False,
        )
        TotalizerMeterFactory()
        self.session.commit()
        view = MeterView.query.filter_by(meter_type=Meter.TYPE_CUSTOMER).one()
        snapshot = get_meter_view_snapshot(view)
        assert snapshot["code"] == view.code
        assert snapshot["customer"]["name"] == "Customer 1"

    def test_meter_view_snapshot_totalizer(self):
        MeterFactory(
            customer__name="Customer 1",
            customer__phone_number="+123456",
            customer__phone_number_verified=False,
        )
        TotalizerMeterFactory()
        self.session.commit()
        view = MeterView.query.filter_by(meter_type=Meter.TYPE_TOTALIZER).one()
        snapshot = get_meter_view_snapshot(view)
        assert snapshot["code"] == view.code
        assert "customer" not in snapshot
        assert "tariff" not in snapshot

    def test_create_meter_snapshot_customer(self):
        meter = MeterFactory(
            customer__name="Customer 1",
            customer__phone_number="+123456",
            customer__phone_number_verified=False,
        )
        self.session.commit()
        snapshot = Snapshot.get_or_create_meter_snapshot(meter_id=meter.id)
        assert snapshot is not None
        assert str(snapshot.id) == "e4e1a5e3-caf0-2f32-ea1c-78b8c6a2d034"
        assert snapshot.hash_ == "a5d6b10b509b1140f29b8033d8a900e79d41353e64e466405af17f2e978fbad0"
        self.verify_json_content(snapshot.payload)

    def test_create_meter_snapshot_totalizer(self):
        totalizer = TotalizerMeterFactory()
        self.session.commit()
        snapshot = Snapshot.get_or_create_meter_snapshot(meter_id=totalizer.id)
        assert snapshot is not None
        assert str(snapshot.id) == "b0cfc850-e0fd-1c33-b4b2-561277224438"
        assert snapshot.hash_ == "dbb1cb4b82e3759cc892fee4fdef08052811bd786a07953707d93e0e2d24bd1d"
        self.verify_json_content(snapshot.payload)

    def test_create_meter_snapshot_get_by_code(self):
        meter = MeterFactory(
            customer__name="Customer 1",
            customer__phone_number="+123456",
            customer__phone_number_verified=False,
        )
        self.session.commit()
        snapshot = Snapshot.get_or_create_meter_snapshot(code=meter.code)
        assert snapshot is not None
        assert str(snapshot.id) == "e4e1a5e3-caf0-2f32-ea1c-78b8c6a2d034"
        assert snapshot.hash_ == "a5d6b10b509b1140f29b8033d8a900e79d41353e64e466405af17f2e978fbad0"

    def test_get_meter_snapshot_customer(self):
        meter = MeterFactory(
            customer__name="Customer 1",
            customer__phone_number="+123456",
            customer__phone_number_verified=False,
        )
        self.session.commit()
        created = Snapshot.get_or_create_meter_snapshot(meter_id=meter.id)
        self.session.add(created)
        self.session.commit()
        snapshot = Snapshot.get_or_create_meter_snapshot(meter_id=meter.id)
        assert len(Snapshot.get_all()) == 1
        assert snapshot is not None
        assert snapshot.id == created.id
        assert snapshot.hash_ == created.hash_
        assert snapshot.payload == created.payload

    def test_get_or_create_meter_snapshot_missing_selector(self):
        with pytest.raises(ValueError) as excinfo:
            Snapshot.get_or_create_meter_snapshot()
        assert "code or meter_id" in str(excinfo.value)

    def test_get_default_id(self):
        """Test the default ID assignment."""
        ret = Snapshot(hash_="462b60992c543e9bfe58d88b76168064128639d4568e0c1677a9987b6de243a3", payload="{}")
        self.session.add(ret)
        self.session.commit()
        assert ret.id is not None
        assert str(ret.id) == "7cf09e79-15cf-7fe8-859e-383d54a75ceb"

    def test_get_or_create_wallet_snapshot_meter(self):
        meter = MeterFactory(
            customer__name="Customer 1",
            customer__phone_number="+123456",
            customer__phone_number_verified=False,
        )
        self.session.commit()
        snapshot = Snapshot.get_or_create_wallet_snapshot(meter.credit_wallet)
        assert snapshot is not None
        assert str(snapshot.id) == "e4e1a5e3-caf0-2f32-ea1c-78b8c6a2d034"
        assert snapshot.hash_ == "a5d6b10b509b1140f29b8033d8a900e79d41353e64e466405af17f2e978fbad0"

    def test_get_or_create_wallet_snapshot_sales(self):
        salesaccount = SalesAccountFactory()
        self.session.commit()
        snapshot = Snapshot.get_or_create_wallet_snapshot(salesaccount.credit_wallet)
        assert snapshot is not None
        assert str(snapshot.id) == "068949e3-9343-f2d3-564c-8f43d82237ab"
        assert snapshot.hash_ == "3b6c316b914b9a4030e9aeb80e341ced54b4af7f4d71fa7452a755e3f464d482"

    def test_get_or_create_tariff_snapshot(self):
        tariff = TariffFactory()
        self.session.commit()
        snapshot = Snapshot.get_or_create_tariff_snapshot(tariff)
        assert snapshot is not None
        assert str(snapshot.id) == "afb517e7-0509-9c08-b7d9-95fc5fee29ef"
        assert snapshot.hash_ == "e954e1ee690970ea5796f3094f3eca40d34d453c023d12ca7d298be921c0ba70"
        assert json.loads(snapshot.payload)["_meta"]["version"] == 2
        assert json.loads(snapshot.payload)["plan_duration_unit"] == "m"

    def test_maybe_json(self):
        assert _maybe_json("""[{"field": "value"}]""") == [{"field": "value"}]
        assert _maybe_json("field") == "field"
