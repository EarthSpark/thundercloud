// -*- coding: utf-8 -*-
// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//
/* global afterEach,beforeEach,describe,expect,test,jest */

jest.mock('backend.js');
jest.mock('datatables.js');

const backend = require('backend.js').backend;
const datatables = require('datatables.js');
const CustomerMeterList = require('meter/js/meter-list-customer.js');

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
        "meter_debt_value": 0.0,
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
        "meter_debt_value": 0.0,
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
        "meter_debt_value": 0.0,
        "meter_active": true,
        "meter_is_running_plan": false,
        "meter_plan_value": 33.0,
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
        "meter_debt_value": 8.0,
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

describe('CustomerMeterList', () => {
    let el = null;
    beforeEach(() => {
        el = $('<div class="box">' +
            '<input id="active" class="iButton-icons" type="checkbox"></input>' +
            '<table class="customer-meter-list"/></div>');
        $(document.body).append(el);
    });

    afterEach(() => {
        if (el !== null) {
            el.remove();
            el = null;
        }
    });

    describe('AJAX requests', () => {
        test('state rendering', () => {
            backend.mockCall('getCustomerMeters', meters);
            new CustomerMeterList.CustomerMeterList();
            const data = datatables.popMockTable().display;
            expect(data).toMatchSnapshot();
        });

        test('tag rendering', () => {
            backend.mockCall('getCustomerMeters', meters);
            let table = new CustomerMeterList.CustomerMeterList();
            let html = table._renderDetails({
                meter_credit_value: 0,
                meter_tags: 'foo,bar,baz'
            });
            expect(html).toMatchSnapshot();
        });
    });

    // describe('hide meters', () => {
    //     test('should work', () => {
    //         backend.mockCall('getCustomerMeters', meters);
    //         new CustomerMeterList.CustomerMeterList();
    //         var input = $("<input value=false>");
    //         var event = {};
    //         event.target = input;
    //         base.onActiveTogggled(event);
    //         expect($('tr:eq(1) > td:eq(0)').html()).toEqual(
    //             '<a href="/meter/SM15R-01-00000004/">SM15R-01-00000004</a>');
    //     });
    // });

    describe('Customer meter', () => {
        test('csv export should work', () => {
            backend.mockCall('getCustomerMeters', meters);
            new CustomerMeterList.CustomerMeterList();
            const data = datatables.popMockTable().export;
            expect(data).toMatchSnapshot();
        });
    });

    describe('list summarization', () => {
        test('should work', () => {
            let many_meters = [];
            for (let i = 0; i < 10; i++) {
                many_meters = many_meters.concat(meters);
            }
            backend.mockCall('getCustomerMeters', many_meters);
            new CustomerMeterList.CustomerMeterList();
            expect($('.datables_info').text()).toMatchSnapshot();
        });
    });

    describe('Events', () => {
        // test('should toggle row class', () => {
        //     backend.mockCall('getCustomerMeters', meters);
        //
        //     let customerMeterList = new CustomerMeterList.CustomerMeterList();
        //
        //     let tr = $('table tr:eq(1)');
        //     customerMeterList._toggleDetailsClicked(tr);
        //
        //     $('table').find('.btn-info').click();
        //         expect($(tr).hasClass('shown')).toBe(false);
        // });

        // test('should listen for details click event', () => {
        //     backend.mockCall('getCustomerMeters', meters);
        //     let customerMeterList = new CustomerMeterList.CustomerMeterList();
        //     customerMeterList._listenEvents();
        //
        //     customerMeterList._toggleDetailsClicked = jest.fn();
        //     $('table').find('.btn-info').click();
        //     expect(customerMeterList._toggleDetailsClicked).toBeCalled();
        // });

        test('render details', () => {
            let row = {};
            row.address_street1 = 'address1';
            row.address_street2 = 'address2';
            row.address_city = 'city';
            row.address_state = 'state';
            row.address_coords = 'coords';
            row.meter_credit_value = 10;
            row.meter_debt_value = 20;
            row.meter_plan_value = 30;
            backend.mockCall('getCustomerMeters', meters);
            let customerMeterList = new CustomerMeterList.CustomerMeterList();
            let renderResult = customerMeterList._renderDetails(row);
            expect(renderResult).toMatchSnapshot();
        });
    });
});
