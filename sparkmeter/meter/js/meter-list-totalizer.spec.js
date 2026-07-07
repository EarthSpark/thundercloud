// -*- coding: utf-8 -*-
// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//
/* global afterEach,beforeEach,describe,expect,test,jest */

jest.mock('backend.js');
jest.mock('datatables.js');

const backend = require('backend.js').backend;
const datatables = require('datatables.js');
const TotalizerMeterList = require('meter/js/meter-list-totalizer.js');

const meters = [
    {
        "address_city": "city",
        "address_state": "state",
        "address_street1": "str\u00ebet",
        "address_street2": "street1",
        "address_coords": "",
        "customer_code": "code1",
        "customer_name": "visiblecustomer1",
        "customer_phone_number": "+123456",
        "customer_phone_number_verified": true,
        "meter_credit_value": 0.0,
        "meter_active": true,
        "meter_is_running_plan": false,
        "meter_plan_value": 0.0,
        "meter_serial": "SM15R-01-00000001",
        "meter_state": 2,
        "meter_tags": "tag1",
        "ground_name": "test_grid_1",
        "tariff_name": "tar\u00efff01",
        "tariff_plan_enabled": true
    },
    {
        "address_city": "city",
        "address_state": "state",
        "address_street1": "str\u00ebet",
        "address_street2": "street2",
        "address_coords": "0, 0",
        "customer_code": "code2",
        "customer_name": "visiblecustomer2",
        "customer_phone_number": "+123456",
        "customer_phone_number_verified": true,
        "meter_credit_value": 0.0,
        "meter_active": true,
        "meter_is_running_plan": false,
        "meter_plan_value": 0.0,
        "meter_serial": "SM15R-01-00000002",
        "meter_state": 2,
        "meter_tags": "tag1,tag2",
        "ground_name": "test_grid_2",
        "tariff_name": "tar\u00efff01",
        "tariff_plan_enabled": false
    },
    {
        "address_city": "",
        "address_state": "",
        "address_street1": "",
        "address_street2": "",
        "address_coords": "",
        "customer_code": "code3",
        "customer_name": "visiblecustomer3",
        "customer_phone_number": "+123456",
        "customer_phone_number_verified": false,
        "meter_credit_value": 10.0,
        "meter_active": true,
        "meter_is_running_plan": false,
        "meter_plan_value": 0.0,
        "meter_serial": "SM15R-01-00000003",
        "meter_state": 2,
        "meter_tags": "",
        "ground_name": "test_grid_3",
        "tariff_name": "tar\u00efff01",
        "tariff_plan_enabled": false
    },
    {
        "address_city": "city",
        "address_state": "state",
        "address_street1": "str\u00ebet",
        "address_street2": "street4",
        "address_coords": "0, 0",
        "customer_code": "code4",
        "customer_name": "hiddencustomer",
        "customer_phone_number": "+123456",
        "customer_phone_number_verified": false,
        "meter_credit_value": 10.0,
        "meter_active": false,
        "meter_is_running_plan": false,
        "meter_plan_value": 0.0,
        "meter_serial": "SM15R-01-00000004",
        "meter_state": 2,
        "meter_tags": "",
        "ground_name": "test_grid_1",
        "tariff_name": "tar\u00efff01",
        "tariff_plan_enabled": false
    }
];

describe('TotalizerMeterList', () => {
    let el = null;
    beforeEach(() => {
        el = $('<div class="box">' +
            '<input id="active" class="iButton-icons" type="checkbox"></input>' +
            '<table class="totalizer-meter-list"/></div>');
        $(document.body).append(el);
    });

    afterEach(() => {
        if (el !== null) {
            el.remove();
            el = null;
        }
    });

    describe('Totalizer meter', () => {
        test('should work', () => {
            backend.mockCall('getTotalizerMeters', meters);
            new TotalizerMeterList.TotalizerMeterList();
            const data = datatables.popMockTable().display;
            expect(data).toMatchSnapshot();
        });
        test('csv export should work', () => {
            backend.mockCall('getTotalizerMeters', meters);
            new TotalizerMeterList.TotalizerMeterList();
            const data = datatables.popMockTable().export;
            expect(data).toMatchSnapshot();
        });
    });

    // FIXME: Need a better Table/Column abstraction
    // describe('hide meters', () => {
    //     test('should work', () => {
    //         backend.mockCall('getTotalizerMeters', meters);
    //         new TotalizerMeterList.TotalizerMeterList();
    //         datatables.onActiveTogggled({
    //             data: {table: jest.fn()},
    //             target: $("<input value=false>")
    //         });
    //         expect($('tr:eq(1) > td:eq(0)').html()).toEqual(
    //             '<a href="/meter/SM15R-01-00000004/">SM15R-01-00000004</a>');
    //     });
    // });

    describe('list summarization', () => {
        test('should work', () => {
            let many_meters = [];
            for (let i = 0; i < 10; i++) {
                many_meters = many_meters.concat(meters);
            }
            backend.mockCall('getTotalizerMeters', many_meters);
            new TotalizerMeterList.TotalizerMeterList();
            expect($('.datables_info').text()).toMatchSnapshot();
        });
    });
});
