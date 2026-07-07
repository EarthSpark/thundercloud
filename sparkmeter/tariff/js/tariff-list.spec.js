// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//

/* global afterEach,beforeEach,describe,expect,test,jest */

jest.mock('backend.js');
jest.mock('datatables.js');

const backend = require('backend.js').backend;
const datatables = require('datatables.js');
const Tariff = require('tariff/js/tariff-domain.js').Tariff;
const TariffList = require('tariff/js/tariff-list.js');

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
    "name": "Normal flat",
    "tariff_type": "flat",
    "tou_enabled": false,
    "tous": []
}, {
    "blockrates": [],
    "flat_load_limit": 100,
    "flat_price": 10.0,
    "id": "00000004-0000-0000-0000-000000000002",
    "load_limit_type": "flat",
    "load_limits": [],
    "plan_enabled": true,
    "plan_duration": "1m",
    "plan_price": 20.0,
    "plan_fixed_fee": 0.0,
    "name": "Monthly plan",
    "tariff_type": "flat",
    "tou_enabled": false,
    "tous": []
}, {
    "blockrates": [],
    "flat_load_limit": 100,
    "flat_price": 10.0,
    "id": "00000004-0000-0000-0000-000000000003",
    "load_limit_type": 'scheduled',
    "load_limits": [{
        start: '00:00',
        end: '10:00',
        value: 1
    }, {
        start: '10:00',
        end: '18:00',
        value: 2
    }, {
        start: '18:00',
        end: '00:00',
        value: 3
    }],
    "plan_enabled": false,
    "plan_duration": "1m",
    "plan_price": 0.0,
    "plan_fixed_fee": 0.0,
    "name": "Scheduled Load limits",
    "tariff_type": "flat",
    "tou_enabled": false,
    "tous": []
}, {
    "blockrates": [{
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
    }],
    "flat_load_limit": 100,
    "flat_price": 0.0,
    "id": "00000004-0000-0000-0000-000000000004",
    "load_limit_type": "flat",
    "load_limits": [],
    "plan_enabled": false,
    "plan_duration": "1m",
    "plan_price": 0.0,
    "plan_fixed_fee": 0.0,
    "name": "Block rates",
    "tariff_type": "blockrate",
    "tou_enabled": false,
    "tous": []
}, {
    "blockrates": [],
    "flat_load_limit": 100,
    "flat_price": 10.0,
    "id": "00000004-0000-0000-0000-000000000005",
    "load_limit_type": "flat",
    "load_limits": [],
    "plan_enabled": false,
    "plan_duration": "1m",
    "plan_price": 0.0,
    "plan_fixed_fee": 0.0,
    "name": "TOUs",
    "tariff_type": "flat",
    "tou_enabled": true,
    "tous": [{
        start: '00:00',
        end: '10:00',
        value: 1
    }, {
        start: '10:00',
        end: '18:00',
        value: 2
    }, {
        start: '18:00',
        end: '00:00',
        value: 3
    }]
}];

describe('TariffList', () => {
    let el = null;
    beforeEach(() => {
        el = $(
            // Header
            '<head>' +
            '<meta itemprop="config-ground" content="null">' +
            '<meta itemprop="config-vendor" content="true"/>' +
            '<meta itemprop="config-currency" content="USD">' +
            '</head>' +

            // Box and Table
            '<div class="box">' +
            '<div class="box-header">' +
            '<span class="title"></span>' +
            '</div>' + // box-header
            '<table class="tariff-list"/></div>' +
            '</div>'
        );
        $(document.body).append(el);
        backend.mockCall('getTariffs', tariffs.map((tariff) => new Tariff().load(tariff)));
        new TariffList.TariffList();
    });

    afterEach(() => {
        if (el !== null) {
            el.remove();
        }
        el = null;
    });

    test('Rendering', () => {
        backend.mockCall('getTariffs', tariffs.map((tariff) => new Tariff().load(tariff)));
        new TariffList.TariffList();
        const data = datatables.popMockTable().display;
        expect(data).toMatchSnapshot();
    });

    test('CSV export', () => {
        backend.mockCall('getTariffs', tariffs.map((tariff) => new Tariff().load(tariff)));
        new TariffList.TariffList();
        const data = datatables.popMockTable().export;
        expect(data).toMatchSnapshot();
    });
});
