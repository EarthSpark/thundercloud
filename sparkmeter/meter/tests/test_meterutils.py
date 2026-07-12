"""Test the meter utilities."""

import json
import logging

import pytest
from testfixtures import LogCapture

from sparkmeter.exceptions import MeterError
from sparkmeter.meter.meterutils import (
    ModelMapper,
    get_x_variant_name,
    is_x_variant,
    merge_local_meter_models,
    rekey_serial,
)


@pytest.mark.parametrize("name,expected", (("SM5R", "SM5XR"), ("SM60RP", "SM60XRP"), ("SM200E", "SM200XE")))
def test_get_x_variant_name(name, expected):
    assert get_x_variant_name(name) == expected


def test_get_x_variant_name_already():
    with pytest.raises(ValueError):
        get_x_variant_name("SM5XR")


@pytest.mark.parametrize("name", ("SM5", "KM1234", "4R", "SMSR"))
def test_get_x_variant_name_unknown(name):
    with pytest.raises(MeterError):
        get_x_variant_name(name)


@pytest.mark.parametrize("name,result", (("SM5R", False), ("SM5XR", True), ("SM60RP", False)))
def test_is_x_variant(name, result):
    assert is_x_variant(name) == result


@pytest.mark.parametrize(
    "serial,model,expected",
    (
        ("SM5R-01-22200011", "SM5XR", "SM5XR-01-22200011"),
        ("SM5XR-01-22200011", "SM5XR", "SM5XR-01-22200011"),
        ("SM60RP-04-00000011", "SM5XR", "SM5XR-04-00000011"),
    ),
)
def test_rekey_serial(serial, model, expected):
    assert rekey_serial(serial, model) == expected


def test_rekey_serial_bad_serial():
    with pytest.raises(MeterError):
        rekey_serial("SMR-0-00", "SM5XR")


class TestModelMapper(object):
    """Test model-mapper related code"""

    def test_model_init(self):
        data = [{"name": "Foo", "data": "data2"}, {"name": "Bar", "data": "data2"}]
        mapper = ModelMapper(data)
        assert isinstance(mapper._models, dict)
        assert len(mapper._models) == 2
        assert "Foo" in mapper._models
        assert "Bar" in mapper._models
        assert mapper._models["Foo"] == data[0]
        assert mapper._models["Bar"] == data[1]

    def test_model_init_bad_type(self):
        data = {"Foo": {"name": "Foo", "data": "data2"}, "Bar": {"name": "Bar", "data": "data2"}}
        with pytest.raises(AssertionError):
            ModelMapper(data)

    def test_add_model(self):
        mapper = ModelMapper([])
        assert len(mapper._models) == 0
        mapper.add_model({"name": "Foo"})
        assert len(mapper._models) == 1
        assert "Foo" in mapper._models
        mapper.add_model({"name": "Bar"})
        assert len(mapper._models) == 2
        assert "Bar" in mapper._models

    def test_add_model_duplicate(self):
        mapper = ModelMapper([{"name": "Foo"}])
        assert len(mapper._models) == 1
        assert "Foo" in mapper._models
        with pytest.raises(ValueError):
            mapper.add_model({"name": "Foo"})

    def test_update_model(self):
        data = [{"name": "Foo", "data": "data1"}]
        mapper = ModelMapper(data)
        assert mapper._models["Foo"]["data"] == "data1"
        mapper.update_model({"name": "Foo", "data": "data2"})
        assert mapper._models["Foo"]["data"] == "data2"

    def test_update_model_missing(self):
        mapper = ModelMapper([])
        with pytest.raises(MeterError):
            mapper.update_model({"name": "Foo", "data": "data2"})

    def test_get_model(self):
        data = [{"name": "Foo", "data": "data1"}]
        mapper = ModelMapper(data)
        assert mapper.get_model("Foo") == data[0]

    def test_get_model_missing(self):
        data = [{"name": "Foo", "data": "data1"}]
        mapper = ModelMapper(data)
        with pytest.raises(MeterError):
            mapper.get_model("Bar")

    def test_get_x_model(self):
        data = [{"name": "SM5R", "data": "data1"}, {"name": "SM5XR", "data": "data2"}]
        mapper = ModelMapper(data)
        assert mapper.get_x_model("SM5R") == data[1]
        assert mapper.get_x_model("SM5XR") == data[1]

    def test_get_models(self):
        data = [{"name": "SM5R", "data": "data1"}, {"name": "SM5XR", "data": "data2"}]
        mapper = ModelMapper(data)
        models = mapper.get_models()
        assert len(models) == 2
        assert models == data

    def test_get_x_model_missing(self):
        data = [{"name": "SM5R", "data": "data1"}]
        mapper = ModelMapper(data)
        with pytest.raises(MeterError):
            mapper.get_x_model("SM5R")

    def test_get_serial_model(self):
        data = [{"name": "SM5R", "data": "data1"}]
        mapper = ModelMapper(data)
        assert mapper.get_serial_model("SM5R-01-01234567") == data[0]

    def test_get_serial_model_missing(self):
        data = [{"name": "SM5R", "data": "data1"}]
        mapper = ModelMapper(data)
        with pytest.raises(MeterError):
            mapper.get_serial_model("SM20R-01-01234567")

    def test_get_serial_model_malformed(self):
        data = [{"name": "SM5R", "data": "data1"}]
        mapper = ModelMapper(data)
        with pytest.raises(MeterError):
            mapper.get_serial_model("SM5R-01-101234567")


class TestMergeLocalMeterModels(object):
    def test_inrush_within_limits(self, sample_meter_models):
        local_limits = {model["name"]: model["inrush_limit"] for model in sample_meter_models}
        merged = merge_local_meter_models(sample_meter_models, local_limits)
        assert sort_by_name(sample_meter_models) == sort_by_name(merged)

    def test_all_inrush_outside_limits(self, sample_meter_models):
        """
        Verify that X variants are created, or updated if they exist, and that base model inrush limits don't
        get updated
        """
        sample_dict = {model["name"]: model for model in sample_meter_models}
        local_limits = {model["name"]: model["inrush_limit"] + 1 for model in sample_meter_models}
        # Verify X meters are updated and created accordingly
        with LogCapture("sparkmeter.meter.meterutils", level=logging.WARNING) as cap:
            merged = merge_local_meter_models(sample_meter_models, local_limits)
            assert len(cap.records) == 7
            for log, expected in zip(
                cap.records,
                ["Raising", "Creating", "Raising", "Creating", "Creating", "Creating", "Creating"],
            ):
                assert log.getMessage().startswith(expected), log
        assert len(sample_meter_models) < len(merged)
        for local_model in merged:  # iterate over the resultant model set
            local_name = local_model["name"]
            if is_x_variant(local_name):  # if this is an X variant...
                if local_name in sample_dict:  # if it existed, verify its inrush was updated
                    assert sample_dict[local_name]["inrush_limit"] + 1 == local_model["inrush_limit"], (
                        json.dumps(local_model)
                    )
                else:  # if it didn't exist, compare it to the non-X variant's inrush
                    assert (
                        sample_dict[local_name.replace("X", "")]["inrush_limit"] + 1
                        == (local_model["inrush_limit"])
                    ), json.dumps(local_model)
            else:  # if this isn't an X variant, verify the inrush wasn't changed
                assert sample_dict[local_name]["inrush_limit"] == local_model["inrush_limit"], json.dumps(
                    local_model
                )


@pytest.fixture
def sample_meter_models():
    return [
        {
            "name": "SM5R",
            "inrush_limit": 10.0,
            "continuous_limit": 6.0,
            "scalars": "2x",
            "enabled": True,
        },
        {
            "name": "SM5XR",
            "inrush_limit": 10.0,
            "continuous_limit": 6.0,
            "scalars": "2x",
            "enabled": True,
        },
        {
            "name": "SM15R",
            "inrush_limit": 20.0,
            "continuous_limit": 20.0,
            "scalars": "2x",
            "enabled": True,
        },
        {
            "name": "SM20R",
            "inrush_limit": 20.0,
            "continuous_limit": 20.0,
            "scalars": "2x",
            "enabled": True,
        },
        {
            "name": "SM20XR",
            "inrush_limit": 50.0,
            "continuous_limit": 20.0,
            "scalars": "2x",
            "enabled": True,
        },
        {
            "name": "SM60R",
            "inrush_limit": 61.0,
            "continuous_limit": 61.0,
            "scalars": "2x",
            "enabled": True,
        },
        {
            "name": "SM60RP",
            "inrush_limit": 61.0,
            "continuous_limit": 61.0,
            "scalars": "2x",
            "enabled": True,
        },
        {
            "name": "SM100E",
            "inrush_limit": 2.0,
            "continuous_limit": 1.0,
            "scalars": "2x",
            "enabled": True,
        },
        {
            "name": "SM200E",
            "inrush_limit": 2.0,
            "continuous_limit": 1.0,
            "scalars": "4x",
            "enabled": True,
        },
    ]


def sort_by_name(iterable):
    return sorted(iterable, key=lambda item: item["name"])
