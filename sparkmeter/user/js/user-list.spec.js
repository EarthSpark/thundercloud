// -*- coding: utf-8 -*-
// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//

/* global afterEach,beforeEach,describe,expect,jest,test,setTimeout */

jest.mock('backend.js');
jest.mock('datatables.js');

const backend = require('backend.js').backend;
const datatables = require('datatables.js');

const UserList = require('user/js/user-list.js');

const OPERATOR_USERS = [
    {
        "accounts": [],
        "active": true,
        "email": "operator@earthsparkinternational.org",
        "id": "00000000-0000-0000-0000-000000000003",
        "username": "operator-1"
    }
];
const VENDOR_USERS = [
    {
        "accounts": [],
        "active": false,
        "email": "vendor@earthsparkinternational.org",
        "id": "00000000-0000-0000-0000-000000000001",
        "username": "vendor-1"
    }
];
const API_USERS = [
    {
        "accounts": [],
        "active": true,
        "email": null,
        "id": "00000000-0000-0000-0000-000000000001",
        "username": "api-user-1"
    },
    {
        "accounts": [{
            id: "00000000-0000-0000-0000-000000000003",
            name: "Sales Account #1"
        }],
        "active": true,
        "email": null,
        "id": "00000000-0000-0000-0000-000000000002",
        "username": "api-user-2"
    }
];

let el = null;

beforeEach(() => {
    $(document.body).attr('data-page-name', 'user-list');
});

afterEach(() => {
    if (el !== null) {
        el.remove();
        el = null;
    }
    $(document.body).removeAttr('data-page-name');
});

describe('Operator Box', () => {
    test('rendering should work', () => {
        el = $('<table class="user-list" data-role="operator"/>');
        $(document.body).append(el);
        backend.mockCall('getUsersByRole', OPERATOR_USERS);
        new UserList.UserList();
        const data = datatables.popMockTable().display;
        expect(data).toMatchSnapshot();
    });
    test('export CSV should work', () => {
        el = $('<table class="user-list" data-role="operator"/></div>');
        $(document.body).append(el);
        backend.mockCall('getUsersByRole', OPERATOR_USERS);
        new UserList.UserList();
        const data = datatables.popMockTable().export;
        expect(data).toMatchSnapshot();
    });
});

describe('Vendor Box', () => {
    test('rendering should work', () => {
        el = $('<table class="user-list" data-role="vendor"/></div>');
        $(document.body).append(el);
        backend.mockCall('getUsersByRole', VENDOR_USERS);
        new UserList.UserList();
        const data = datatables.popMockTable().display;
        expect(data).toMatchSnapshot();
    });
    test('export CSV should work', () => {
        el = $('<table class="user-list" data-role="vendor"/></div>');
        $(document.body).append(el);
        backend.mockCall('getUsersByRole', VENDOR_USERS);
        new UserList.UserList();
        const data = datatables.popMockTable().export;
        expect(data).toMatchSnapshot();
    });
});

describe('API User Box', () => {
    test('rendering should work', () => {
        el = $('<table class="user-list" data-role="api"/></div>');
        $(document.body).append(el);
        backend.mockCall('getUsersByRole', API_USERS);
        new UserList.UserList();
        const data = datatables.popMockTable().display;
        expect(data).toMatchSnapshot();
    });
    test('export CSV should work', () => {
        el = $('<table class="user-list" data-role="api"/></div>');
        $(document.body).append(el);
        backend.mockCall('getUsersByRole', API_USERS);
        new UserList.UserList();
        const data = datatables.popMockTable().export;
        expect(data).toMatchSnapshot();
    });
});
