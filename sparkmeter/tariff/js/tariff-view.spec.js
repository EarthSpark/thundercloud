// -*- coding: utf-8 -*-
// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//

/* global vg,afterEach,beforeEach,describe,expect,test,jest */

jest.mock('backend.js');
jest.mock('location.js');

const backend = require('backend.js').backend;
const location = require('location.js');
const TariffView = require('tariff/js/tariff-view.js');
const Tariff = require('tariff/js/tariff-domain.js').Tariff;

const tariffs = [{
    "blockrates": [],
    "flat_load_limit": 100,
    "flat_price": 10.0,
    "id": "00000004-0000-0000-0000-000000000001",
    "load_limit_type": "flat",
    "load_limits": [],
    "plan_enabled": false,
    "plan_duration": "1m",
    "plan_price": 0.0,
    "plan_fixed_fee": 0.0,
    "cycle_start_day_of_month": 1,
    "name": "tar\u00efff01",
    "tariff_type": "flat",
    "tou_enabled": false,
    "tous": []
}];

describe('TariffView', () => {
    let el = null;
    let tariffViewDiv = null;

    beforeEach(function() {
        $(document.head).append('<meta itemprop="config-currency" content="USD">');

        el = $('<div class="tariff-details hidden">');
        $(document.body).append(el);
        tariffViewDiv = $('.tariff-details');
        global.vg = {
            parse: {
                spec: jest.fn()
            }
        };
    });

    afterEach(function() {
        if (el !== null) {
            el.remove();
            el = null;
        }
    });

    describe("Loading tariff", () => {
        let tariff = null;
        beforeEach(function() {
            tariff = new Tariff();
            tariff.load(tariffs[0]);
            backend.mockCall('getTariff', tariff);
            location.href = 'http://localhost:5000/tariff/abc/';
            tariffViewDiv.append(`
                    <dt>'Tariff Name:</dt>
                    <dd class="tariff-name"></dd>
                    <dt>'Warning on Low Balance:</dt>
                    <dd class="tariff-warning-on-low-balance">0</dd>
                    <dt>'Plan minimum spend:</dt>
                    <dd class="tariff-plan-price"></dd>
                    <dt>'Plan fixed fee:</dt>
                    <dd class="tariff-plan-fixed-fee"></dd>
                    <dt>'Cycle Start Day:</dt>
                    <dd class="tariff-cycle-start-day-of-month"></dd>
                    <dt>'Load Limit Type:</dt>
                    <dd class="tariff-load-limit-type"></dd>
                    <dt>'Load Limit in Watts:</dt>
                    <dd class="tariff-load-limit"></dd>
                    <dt>Tariff Type:</dt>
                    <dd class="tariff-type"></dd>
                    <dt class="tariff-blockrates">Block rates:</dt>
                    <dd class="tariff-blockrates"></dd>
                    <dt class="tariff-flatrate">Flat rate:</dt>
                    <dd class="tariff-flatrate"></dd>
                    <div class="tou-graph"></div>
                    <div class="load-limits-graph"></div>`);
        });

        afterEach(function() {
            tariff = null;
        });

        test('name', () => {
            tariff.name = 'tarïff01';
            new TariffView.TariffView();
            expect($('.tariff-name').text()).toMatchSnapshot();
        });

        test('warning on low balance', () => {
            tariff.low_balance_threshold = 20;
            new TariffView.TariffView();
            expect($('.tariff-warning-on-low-balance').text()).toMatchSnapshot();
        });

        test('cycle start day of month', () => {
            tariff.cycle_start_day = 17;
            new TariffView.TariffView();
            expect($('.tariff-cycle-start-day-of-month').text()).toMatchSnapshot();
        });

        test('warning on low balance turned off', () => {
            tariff.monthly_plan_enabled = false;

            tariff.low_balance_threshold = 0;
            new TariffView.TariffView();
            expect($('.tariff-warning-on-low-balance').text()).toMatchSnapshot();
        });

        test('monthly plan enabled', () => {
            tariff.plan_enabled = true;
            tariff.plan_price = 30;
            new TariffView.TariffView();
            expect($('.tariff-plan-price').text()).toMatchSnapshot();
            expect($('.tariff-plan-fixed-fee').text()).toMatchSnapshot();
        });

        test('monthly plan disabled', () => {
            tariff.plan_enabled = false;
            new TariffView.TariffView();
            expect($('.tariff-plan-price').text()).toMatchSnapshot();
            expect($('.tariff-plan-fixed-fee').text()).toMatchSnapshot();
        });

        test('daily plan enabled', () => {
            tariff.plan_enabled = true;
            tariff.plan_duration_span = 'd';
            tariff.plan_price = 30;
            new TariffView.TariffView();
            expect($('.tariff-plan-price').text()).toMatchSnapshot();
            expect($('.tariff-plan-fixed-fee').text()).toMatchSnapshot();
        });

        test('flat rate', () => {
            tariff.tariff_type = 'flat';
            tariff.flat_rate = 85;
            new TariffView.TariffView();
            expect($('dd.tariff-blockrates').text()).toMatchSnapshot();
            expect($('dd.tariff-flatrate').text()).toMatchSnapshot();
        });

        test('block rate', () => {
            tariff.tariff_type = 'blockrate';
            tariff.blockrates.push(...[{
                lower: 0,
                upper: 10,
                value: 1
            }, {
                lower: 10,
                upper: 100,
                value: 2
            }, {
                lower: 100,
                upper: 0,
                value: 3
            }]);
            new TariffView.TariffView();
            expect($('dd.tariff-blockrates').html()).toMatchSnapshot();
            expect($('dd.tariff-flatrate').text()).toMatchSnapshot();
        });

        test('load limits', () => {
            tariff.load_limit_type = 'scheduled';
            tariff.load_limits.push(...[{
                start: '00:00',
                end: '10:00',
                value: 200
            }, {
                start: '10:00',
                end: '18:00',
                value: 300
            }, {
                start: '18:00',
                end: '00:00',
                value: 180
            }]);
            new TariffView.TariffView();
            expect($('.tariff-load-limit-type').text()).toMatchSnapshot();
            expect($('.tariff-load-limit').html()).toMatchSnapshot();
            expect(vg.parse.spec.mock.calls.length).toBe(1);
            let calls = vg.parse.spec.mock.calls;
            expect(calls[0][0].data[0].values).toMatchSnapshot();
        });

        test('load limits crossing midnight', () => {
            tariff.load_limit_type = 'scheduled';
            tariff.load_limits = [{
                start: '22:00',
                end: '02:00',
                value: 200
            }, {
                start: '08:00',
                end: '10:00',
                value: 300
            }, {
                start: '18:00',
                end: '20:00',
                value: 180
            }];
            new TariffView.TariffView();
            expect($('.tariff-load-limit-type').text()).toMatchSnapshot();
            expect($('.tariff-load-limit').html()).toMatchSnapshot();
            expect(vg.parse.spec.mock.calls.length).toBe(1);
            let calls = vg.parse.spec.mock.calls;
            expect(calls[0][0].data[0].values).toMatchSnapshot();
        });

        test('tou periods', () => {
            tariff.tou_enabled = true;
            tariff.tous = [{
                start: '00:00',
                end: '10:00',
                value: 50
            }, {
                start: '10:00',
                end: '18:00',
                value: 80
            }, {
                start: '18:00',
                end: '00:00',
                value: 100
            }];
            new TariffView.TariffView();
            expect(vg.parse.spec.mock.calls.length).toBe(2);
            let calls = vg.parse.spec.mock.calls;
            expect(calls[1][0].data[0].values).toMatchSnapshot();
        });

        test('tou periods crossing midnight', () => {
            tariff.tou_enabled = true;
            tariff.tous = [{
                start: '22:00',
                end: '02:00',
                value: 50
            }, {
                start: '08:00',
                end: '10:00',
                value: 120
            }, {
                start: '18:00',
                end: '20:00',
                value: 80
            }];
            new TariffView.TariffView();
            expect(vg.parse.spec.mock.calls.length).toBe(2);
            let calls = vg.parse.spec.mock.calls;
            expect(calls[1][0].data[0].values).toMatchSnapshot();
        });

        test('tou periods disabled', () => {
            tariff.tou_enabled = false;
            tariff.tous = [];
            new TariffView.TariffView();
        });
    });
});
