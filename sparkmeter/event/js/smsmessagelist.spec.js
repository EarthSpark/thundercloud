// -*- coding: utf-8 -*-
// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//

/* global afterEach,beforeEach,describe,expect,test,jest */

jest.mock('backend.js');
jest.mock('datatables.js');

const backend = require('backend.js').backend;
const datatables = require('datatables.js');

const MessageList = require('event/js/smsmessagelist.js');

const messages = [
    // Two-way SMS received and the code (e.g. BAL) has been recognized
    {
        "customer_name": "m1",
        "direction": "in",
        "phone_number": "+5516994648080",
        "processed": true,
        "text": "BAL",
        "timestamp": "2016-02-18T13:53:24.292177",
        "code": "BAL",
        "alert_label": null,
        "message_type": null,
        "event_type": null,
        "ground_name": "Ground",
        "ground_serial": "ground-serial",
        "origin": "command"
    },
    // Response to a valid Two-way SMS code (e.g. BAL) from a valid number
    {
        "customer_name": "m1",
        "direction": "out",
        "phone_number": "+5516994648080",
        "processed": false,
        "text": "Your current balance is 273.0",
        "timestamp": "2016-02-18T13:53:24.292177",
        "code": "BAL",
        "alert_label": null,
        "message_type": null,
        "event_type": null,
        "ground_name": "Ground",
        "ground_serial": "ground-serial",
        "origin": "command"
    },
    // Any system message (verify number, error message, etc)
    {
        "customer_name": null,
        "direction": "in",
        "phone_number": "+5516991787541",
        "processed": false,
        "text": "This SMS code is not recognized by SparkMeter.",
        "timestamp": "2016-02-18T13:52:11.410646",
        "code": null,
        "alert_label": null,
        "message_type": "wrong-code",
        "event_type": null,
        "ground_name": "Ground",
        "ground_serial": "ground-serial",
        "origin": "system"
    },
    // Message sent as the result of an alert (e.g. Successful payment)
    {
        "customer_name": "m1",
        "direction": "out",
        "phone_number": "+5516994648080",
        "processed": true,
        "text": "Thank you for buying 65.0 of energy",
        "timestamp": "2016-02-18T13:52:11.410646",
        "code": null,
        "alert_label": "Successful payment",
        "message_type": null,
        "event_type": "customer-credit-transaction-processed",
        "ground_name": "Ground",
        "ground_serial": "ground-serial",

        "origin": "alert"
    },
    // Two-way SMS received but not recognized (unrecognized code)
    {
        "customer_name": null,
        "direction": "in",
        "phone_number": "+5516991787542",
        "processed": false,
        "text": "BADCODE",
        "timestamp": "2016-02-18T13:52:11.410646",
        "code": null,
        "alert_label": null,
        "message_type": null,
        "event_type": null,
        "ground_name": "Ground",
        "ground_serial": "ground-serial",
        "origin": "unknown"
    }
];

const messagesResponse = {
    data: messages,
    draw: 1,
    recordsTotal: messages.length,
    recordsFiltered: messages.length
};

describe('MessagesList', () => {
    let el = null;
    beforeEach(() => {
        el = $(
            // Header
            '<head>' +
            '<meta itemprop="config-ground" content="null">' +
            '<meta itemprop="config-vendor" content="true"/>' +
            '</head>' +

            // Filter
            '<li>' +
            '<select id="transaction" class="select-filter transaction">' +
            '<option value="">All</option>' +
            '</select>' +
            '</li>' +

            // Another table which should not be touched
            '<div class="box">' +
            '<div class="box-header">' +
            '<span class="title"></span>' +
            '</div>' + // box-header
            '<table id="transaction-list"/></div>' +
            '</div>' + // box

            // Box and Table
            '<div class="box">' +
            '<div class="box-header">' +
            '<span class="title"></span>' +
            '</div>' + // box-header
            '<table id="message-list"/></div>' +
            '</div>' // box
        );

        $(document.body).append(el);
        backend.mockCall('getMessages', messagesResponse);
    });

    afterEach(() => {
        if (el !== null) {
            el.remove();
            el = null;
        }
    });

    describe('AJAX requests', () => {
        test('phone numbers', () => {
            new MessageList.MessageList();
            const data = datatables.popMockTable().display;
            expect(data).toMatchSnapshot();
        });
    });

    describe('Message List', () => {
        test('CSV Export should work', () => {
            new MessageList.MessageList();
            const data = datatables.popMockTable().export;
            expect(data).toMatchSnapshot();
        });

        test('table title should appear', () => {
            let messageList = new MessageList.MessageList();

            messageList._setTableTitle('test-ground');
            let tableElement = messageList._table.table().node();
            let titleElement = $(tableElement).parents('.box').find('.box-header span.title');
            expect(titleElement.text()).toMatchSnapshot();
        });

        // test('Hidden to-from column should appear on the ground page', () => {
        //     new MessageList.MessageList();
        //     expect($('thead > tr > th:eq(3)').text()).toBe('To/From');
        // });

        // test('Hidden to-from column should not appear on the meter page', () => {
        //     el.remove();
        //     el = $('<div class="icon-dashboard"><table id="message-list"/></div>');
        //     $(document.body).append(el);
        //     new MessageList.MessageList();
        //     const data = datatables.popMockTable().display;
        //     expect(data.header).toBe([
        //         "Date",
        //         "Type",
        //         "In/Out",
        //         "To/From",
        //         "Message",
        //         "Processed",
        //         "Ground",
        //     ]);
        // });
    });
});
