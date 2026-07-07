// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//

/* global afterEach,beforeEach,describe,expect,test,jest */

jest.mock('backend.js');
jest.mock('datatables.js');

const backend = require('backend.js').backend;
const datatables = require('datatables.js');

const TransactionList = require('transaction/js/transaction-list.js');

const transactions = [
    {
        "acct_type": "credit",
        "amount": -100.0,
        "created": "2016-02-22T14:17:33.208570",
        "error": null,
        "external_id": null,
        "from_data": {"sales_account_id": "123", "sales_account_name": "DemoVendor2"},
        "ground_name": 'test_grid_1',
        "ground_serial": 111111,
        "has_reversal": false,
        "id": "83e34390-c4cc-46b4-a26e-d6c84324af73",
        "memo": null,
        "monetary": true,
        "origin": "reversal",
        "reference_id": "6e60d5b6-9ccd-4a4f-b041-d318dc04c0e6",
        "source_name": "cash",
        "state": "reversed",
        "to_data": {"customer_name": "Johans' desk meter", "meter_serial": "SM15R-01-00000002"},
        "username": "DemoOperator"
    },
    {
        "acct_type": "credit",
        "amount": 100.0,
        "created": "2016-02-22T14:01:06.531095",
        "error": null,
        "external_id": "an-external-id",
        "from_data": {"sales_account_id": "123", "sales_account_name": "DemoVendor2"},
        "ground_name": 'test_grid_1',
        "ground_serial": 111111,
        "has_reversal": true,
        "id": "3c1a7b18-5c17-4afb-9559-62b55f44c213",
        "memo": "a memo",
        "monetary": true,
        "origin": "user",
        "reference_id": null,
        "source_name": "cash",
        "state": "processed",
        "to_data": {"customer_name": "Johans' desk meter", "meter_serial": "SM15R-01-00000002"},
        "username": "DemoOperator"
    },
    {
        "acct_type": "credit",
        "amount": -100.0,
        "created": "2016-02-22T13:04:11.993897",
        "error": "The parent transaction has already been reversed.",
        "external_id": null,
        "from_data": {"sales_account_id": "123", "sales_account_name": "DemoVendor2"},
        "ground_name": 'test_grid_1',
        "ground_serial": 111111,
        "has_reversal": false,
        "id": "84192504-d4b3-4b98-8480-c4e9128b1e41",
        "memo": null,
        "monetary": true,
        "origin": "reversal",
        "reference_id": "a73e986f-52e8-4d9a-9fb1-17a95ad53153",
        "source_name": "cash",
        "state": "error",
        "to_data": {"customer_name": "Johans' desk meter", "meter_serial": "SM15R-01-00000002"},
        "username": "DemoOperator"
    },
    {
        "acct_type": "credit",
        "amount": 100.0,
        "created": "2016-02-19T15:48:08.788432",
        "error": null,
        "external_id": null,
        "from_data": {"sales_account_id": "123", "sales_account_name": "DemoVendor2"},
        "ground_name": 'test_grid_1',
        "ground_serial": 111111,
        "has_reversal": false,
        "id": "100dd50c-3e9b-440f-87e1-c2908c4d2616",
        "memo": null,
        "monetary": true,
        "origin": "system",
        "reference_id": null,
        "source_name": "cash",
        "state": "pending",
        "to_data": {"customer_name": "Johans' desk meter", "meter_serial": "SM15R-01-00000002"},
        "username": "DemoOperator"
    },
    {
        "acct_type": "credit",
        "amount": 100.0,
        "created": "2016-02-19T15:48:08.788432",
        "error": null,
        "external_id": null,
        "from_data": {"sales_account_id": "123", "sales_account_name": "DemoVendor2"},
        "ground_name": 'test_grid_1',
        "ground_serial": 111111,
        "has_reversal": false,
        "id": "100dd50c-3e9b-440f-87e1-c2908c4d2617",
        "memo": null,
        "monetary": true,
        "origin": "user",
        "reference_id": null,
        "source_name": "cash",
        "state": "processed",
        "to_data": {"customer_name": "Johans' desk meter", "meter_serial": "SM15R-01-00000002"},
        "username": "DemoOperator"
    },
    {
        "acct_type": "credit",
        "amount": 100.0,
        "created": "2016-02-19T15:48:08.788433",
        "error": null,
        "external_id": null,
        "from_data": {"sales_account_id": "123", "sales_account_name": "DemoVendor2"},
        "has_reversal": true,
        "ground_name": 'test_grid_1',
        "ground_serial": 111111,
        "id": "100dd50c-3e9b-440f-87e1-c2908c4d2618",
        "last_update": "2016-02-22T13:08:10.042047",
        "memo": null,
        "monetary": true,
        "origin": "reversal",
        "reference_id": null,
        "source_name": "cash",
        "state": "processed",
        "to_data": {
            "customer_name": "Johans' desk meter",
            "customer_code": "ABC123",
            "meter_serial": "SM15R-01-00000002"
        },
        "username": "DemoOperator"
    }
];

const grounds = [
    {
        "id": "a72edb40-3bee-453c-ba50-dfa122619d7a",
        "name": "test_grid_1",
        "serial": "111111"
    },
    {
        "id": "8bf81789-46bc-4d06-afab-0f4e2663399a",
        "name": "test_grid_2",
        "serial": "222222"
    },
    {
        "id": "7ea1c2b9-dd25-4a2a-8f15-03a34e6f9039",
        "name": "test_grid_3",
        "serial": "333333"
    }
];

const transactionsResponse = {
    data: transactions,
    draw: 1,
    recordsTotal: transactions.length,
    recordsFiltered: transactions.length
};

let el = null;

describe('TransactionList', () => {
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
            '<table id="message-list"/></div>' +
            '</div>' + // box

            // Box and Table
            '<div class="box">' +
            '<div class="box-header">' +
            '<span class="title"></span>' +
            '</div>' + // box-header
            '<table id="transaction-list"/></div>' +
            '</div>' + // box

            // Modal dialog
            '<div id="reverse-modal"><a id="reverse-link"><p id="reverse-help"></p></div>');
        $(document.body).append(el);
        $(document.body).attr('data-page-name', 'salesaccount-view');
    });

    afterEach(() => {
        if (el !== null) {
            el.remove();
        }
        $(document.body).removeAttr('data-page-name');
        el = null;
    });

    describe('Rendering', () => {
        test('should render dropdown', () => {
            backend.mockCall('getTransactions', transactionsResponse);
            backend.mockCall('getGrounds', grounds);
            new TransactionList.TransactionList();
            expect(datatables.GroundDropDown.mock.calls.length).toBe(1);
        });

        test('show table title', () => {
            backend.mockCall('getTransactions', transactionsResponse);
            var transactionList = new TransactionList.TransactionList();
            transactionList._setTableTitle('test-ground');
            var tableElement = transactionList._table.table().node();
            var titleElement = $(tableElement).parents('.box').find('.box-header span.title');
            expect(titleElement.text()).toMatchSnapshot();
        });

        // test('adds listen events finds row', done => {
        //     backend.mockCall('getTransactions', transactions);
        //     new TransactionList.TransactionList();
        //     let button = $('table#transaction-list').find('.btn-info').closest('tr');
        //     expect($(button).html()).toBe('<td>83e34390-c4cc-46b4-a26e-d6c84324af73</td>' +
        //         '<td>-100</td>' +
        //         '<td>credit</td>' +
        //         '<td><a href="/sales-account/123/">DemoVendor2</a></td>' +
        //         '<td><a href="/meter/SM15R-01-00000002/">SM15R-01-00000002</a></td>' +
        //         '<td><a href="/user/DemoOperator/">DemoOperator</a></td>' +
        //         '<td>6e60d5b6-9ccd-4a4f-b041-d318dc04c0e6</td>' +
        //         '<td class="sorting_1">2016-02-22T14:17:33.208570</td>' +
        //         '<td class=" ground">test_grid_1</td>' +
        //         '<td>' +
        //         '<button class="btn btn-info" data-action="view" data-toggle="collapse" data-target="83e34390-c4cc-46b4-a26e-d6c84324af73">View</button>' +
        //         '</td>'
        //     );
        // });
    });
    describe('Actions', () => {
        test('show details should work', () => {
            backend.mockCall('getTransactions', transactionsResponse);
            let table = new TransactionList.TransactionList();
            expect(table._renderDetails(transactions[0])).toMatchSnapshot();
            expect(table._renderDetails(transactions[1])).toMatchSnapshot();
            expect(table._renderDetails(transactions[2])).toMatchSnapshot();
            expect(table._renderDetails(transactions[3])).toMatchSnapshot();
            expect(table._renderDetails(transactions[4])).toMatchSnapshot();
        });
        test('reverse modal should work', () => {
            backend.mockCall('getTransactions', transactionsResponse);
            $('meta[itemprop=config-operator]').attr('content', 'true');
            $('meta[itemprop=config-vendor]').remove();
            let table = new TransactionList.TransactionList();
            Object.getPrototypeOf(table._table)['row'] = () => {
                return {
                    data: () => {
                        return {
                            amount: 100,
                            from_data: { sales_account_id: 123,
                                         sales_account_name: 'DemoVendor2' },
                            to_data: { meter_serial: 'SM15R-01-00000002' }
                        };
                    }
                };
            };

            $('table#transaction-list').append(`
               <tbody>
                 <tr>
                   <td>
                     <a href="#" class="pull-right" data-toggle="modal"
                        data-target="#reverse-modal"
                        data-transaction-id="100dd50c-3e9b-440f-87e1-c2908c4d2617">
                       <i class="icon-remove-circle"></i>
                     </a>
                    </td>
                  </tr>
               </tbody>`);
            // Test modal action
            let button = $("table#transaction-list a[data-target='#reverse-modal']");
            expect(button.length).toBe(1);
            button.click();
            expect($("#reverse-modal").html()).toMatchSnapshot();
        });
        test('Rendering table should work', () => {
            backend.mockCall('getTransactions', transactionsResponse);
            const data = datatables.popMockTable().display;
            expect(data).toMatchSnapshot();
        });
        test('CSV export should work', () => {
            backend.mockCall('getTransactions', transactionsResponse);
            const data = datatables.popMockTable().export;
            expect(data).toMatchSnapshot();
        });
    });
});
