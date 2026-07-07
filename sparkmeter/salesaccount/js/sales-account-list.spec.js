// -*- coding: utf-8 -*-
// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//
/* global afterEach,beforeEach,describe,expect,test,jest */
jest.mock('backend.js');
jest.mock('datatables.js');

const backend = require('backend.js').backend;
const datatables = require('datatables.js');

const SalesAccountList = require('salesaccount/js/sales-account-list.js');

const GLOBAL_SALES_ACCOUNTS = [
    {
        "active": true,
        "id": "00000000-0000-0000-0000-000000000001",
        "name": "Sales Account #1",
        "transaction_count": 10,
        "transaction_total": 1024
    }
];

const RESTRICTED_SALES_ACCOUNTS = [
    {
        "active": true,
        "credit": 0,
        "debt": 0,
        "id": "00000000-0000-0000-0000-000000000001",
        "markup": 0.05,
        "ground_name": "Ground",
        "ground_serial": "ground-serial",
        "name": "Sales Account #1"
    }
];

describe('Sales Accounts List', () => {
    let el = null;
    beforeEach(() => {
        $(document.body).attr('data-page-name', 'salesaccount-list');
    });

    afterEach(() => {
        if (el !== null) {
            el.remove();
            el = null;
        }
        $(document.body).removeAttr('data-page-name');
    });

    describe('Global', () => {
        test('renders properly', () => {
            el = $('<meta itemprop="config-currency" content="USD"/>' +
                '<meta itemprop="config-username" content="username"/>' +
                '<table class="sales-account-list" data-account-type="global"/></div>');
            $(document.body).append(el);
            backend.mockCall('getSalesAccounts', GLOBAL_SALES_ACCOUNTS);
            new SalesAccountList.SalesAccountList({page: SalesAccountList.PAGE_SALES_ACCOUNT});

            const data = datatables.popMockTable().display;
            expect(data).toMatchSnapshot();
        });
    });

    describe('Restricted', () => {
        test('my rendering should work', () => {
            el = $('<meta itemprop="config-currency" content="USD"/>' +
                '<meta itemprop="config-username" content="username"/>' +
                '<table class="sales-account-list" data-account-type="restricted"/></div>');
            $(document.body).append(el);
            backend.mockCall('getSalesAccounts', RESTRICTED_SALES_ACCOUNTS);
            new SalesAccountList.SalesAccountList({page: SalesAccountList.PAGE_MY});
            const data = datatables.popMockTable().display;
            expect(data).toMatchSnapshot();
        });
    });
});
