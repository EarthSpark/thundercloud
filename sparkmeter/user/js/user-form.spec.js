// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//

/* global afterEach,beforeEach,describe,expect,test */
const UserForm = require('user/js/user-form.js');
const base = require('base.js');

describe('UserForm', () => {
    var el;
    beforeEach(() => {
        el = $('<input id="ground_all_access" type="checkbox">' +
            '<select id="grounds">' +
            '<input id="account_all_access" type="checkbox">' +
            '<select id="accounts">' +
            '<input class="transaction_permission" id="transaction_permission" name="transaction_permission" type="checkbox" value="y">' +
            '<select class="api-sales-account">');
        $(document.body).append(el);
        $(document.body).attr('data-page-name', 'user-form');
    });

    afterEach(() => {
        el.remove();
        $(document.body).removeAttr('data-page-name');
        el = null;
    });

    describe('Transaction permission checkbox', () => {
        test('toggles visibilty of vendor select', () => {
            new UserForm.UserForm();

            // Default value, not set
            expect($('select.api-sales-account').prop('disabled')).toBe(false);

            // Add disabled
            $("input[type^=checkbox].transaction_permission").click();
            expect($('select.api-sales-account').prop('disabled')).toBe(false);

            // Removing disabled
            $("input[type^=checkbox].transaction_permission").click();
            expect($('select.api-sales-account').prop('disabled')).toBe(true);
        });
    });

    describe('Account all access', () => {
        test('toggles visibilty of accounts select', () => {
            new UserForm.UserForm();

            // Default value, not set
            expect($('select#accounts').prop('disabled')).toBe(false);

            // Add disabled
            $("#account_all_access").click();
            expect($('select#accounts').prop('disabled')).toBe(true);

            // Removing disabled
            $("#account_all_access").click();
            expect($('select#accounts').prop('disabled')).toBe(false);
        });
    });

    describe('Ground all access', () => {
        test('toggles visibilty of ground select', () => {
            require('user/js/user-pages.js');
            expect(base.loadPage('user-form')).toBe(true);

            // Default value, not set
            expect($('select#grounds').prop('disabled')).toBe(false);

            // Add disabled
            $("#ground_all_access").click();
            expect($('select#grounds').prop('disabled')).toBe(true);

            // Removing disabled
            $("#ground_all_access").click();
            expect($('select#grounds').prop('disabled')).toBe(false);
        });
    });
});
