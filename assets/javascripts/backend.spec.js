/* global afterEach,beforeEach,describe,expect,test */

let BackendAPI = require('./backend.js').BackendAPI;
let jQuery = require('vendor/jquery-1.10.2.js');

let responses = [];
let requests = [];

// Mock of jQuerys ajax call
global.jQuery = {
    ajax: (options) => {
        return jQuery.Deferred(function(d) {
            if (responses.length === 0) {
                throw new Error("Missing a request for: " + JSON.stringify(options));
            }
            requests.push(options);
            let r = responses.pop();
            if (r.reject === true) {
                d.reject(r.response);
            } else {
                d.resolve(r.response);
            }
            return d;
        });
    },
    Deferred: jQuery.Deferred
};

// localStorage mock API
let storage = Object.create(null);
global.localStorage = {
    getItem: (key) => key in storage ? storage[key] : null,
    setItem: (key, value) => storage[key] = value,
    removeItem: (key, value) => delete storage[key]
};

function verifyAPICall(options) {
    options = options || {};
    if (options.args === undefined) {
        options.args = [];
    }
    if (options.response === undefined) {
        options.response = {status: 'success'};
    }
    if (options.reject === undefined) {
        options.reject = false;
    }
    return (done) => {
        storage['token'] = 'existing-token';
        responses.push({
            response: options.response,
            reject: options.reject
        });

        let backend = new BackendAPI();
        let fn = backend[options.fn];
        fn.apply(backend, options.args).then((response) => {
            expect({
                response: response,
                requests: requests,
                storage: storage
            }).toMatchSnapshot();
            done();
        });
    };
}

describe('BackendAPI', () => {
    beforeEach(function() {
        responses = [];
    });

    afterEach(function() {
        expect(responses).toEqual([]);
        requests = [];
        storage = Object.create(null);
    });

    test('get(/foo) no token', (done) => {
        responses.push({response: {'foo-response': true}});
        responses.push({response: {token: 'my-token'}});
        let backend = new BackendAPI();
        backend.get('/foo').then((response) => {
            expect({
                response: response,
                requests: requests,
                storage: storage
            }).toMatchSnapshot();
            done();
        });
    });

    test('get(/foo) with bad token', (done) => {
        storage['token'] = 'bad-token';
        responses.push({response: {'foo-response': true}});
        responses.push({response: {'token': 'new-token'}});
        responses.push({
            response: {'unauthorized': true},
            reject: true
        });
        let backend = new BackendAPI();
        backend.get('/foo').then((response) => {
            expect({
                response: response,
                requests: requests,
                storage: storage
            }).toMatchSnapshot();
            done();
        });
    });

    test('get(/foo, value)',
        verifyAPICall({
            fn: 'get',
            args: ['/foo'],
            response: {'foo-response': true}
        }));

    test('put(/foo, value)',
        verifyAPICall({
            fn: 'put',
            args: ['/foo', 'value'],
            response: {'foo-response': true}
        }));

    test('listConfigParameters()',
        verifyAPICall({
            fn: 'listConfigParameters',
            response: {status: 'success', parameters: 'parameters'}
        }));

    test('saveConfigParameter(config, value)',
        verifyAPICall({
            fn: 'saveConfigParameter',
            args: ['config', 'value']
        }));

    test('getTariff()',
        verifyAPICall({
            fn: 'getTariff',
            args: ['tariff'],
            response: {status: 'success', tariff: 'tariff'}
        }));

    test('getTariffs()',
        verifyAPICall({
            fn: 'getTariffs',
            response: {status: 'success', tariffs: [{}]}
        }));

    test('getUsersByRole(operator)',
        verifyAPICall({
            fn: 'getUsersByRole',
            args: ['operator'],
            response: {status: 'success', users: 'users'}
        }));

    test('getTransactions()',
        verifyAPICall({
            fn: 'getTransactions',
            args: ['datatableData'],
            response: {status: 'success', transactions: 'transactions', draw: 1, total: 7}
        }));

    test('getMessages()',
        verifyAPICall({
            fn: 'getMessages',
            response: {status: 'success', messages: 'messages', draw: 1, total: 7}
        }));

    test('getLatestReadings()',
        verifyAPICall({fn: 'getLatestReadings'}));

    test('getCustomerMeters()',
        verifyAPICall({
            fn: 'getCustomerMeters',
            response: {meters: 'meters', status: 'success'}
        }));

    test('getTotalizerMeters()',
        verifyAPICall({
            fn: 'getTotalizerMeters',
            response: {meters: 'meters', status: 'success'}
        }));

    test('getGrounds()',
        verifyAPICall({
            fn: 'getGrounds',
            response: {grounds: 'grounds', status: 'success'}
        }));

    test('getSalesAccounts(all, operator)',
        verifyAPICall({
            fn: 'getSalesAccounts',
            args: ['all', 'operator'],
            response: {sales_accounts: 'accounts', status: 'success'}
        }));

    test('getSalesAccounts(my, operator)',
        verifyAPICall({
            fn: 'getSalesAccounts',
            args: ['my', 'operator'],
            response: {sales_accounts: 'accounts', status: 'success'}
        }));

    test('getSalesAccounts(user, operator)',
        verifyAPICall({
            fn: 'getSalesAccounts',
            args: ['user', 'operator'],
            response: {sales_accounts: 'accounts', status: 'success'}
        }));

    test('getSalesAccounts(all, vendor)',
        verifyAPICall({
            fn: 'getSalesAccounts',
            args: ['all', 'vendor'],
            response: {sales_accounts: 'accounts', status: 'success'}
        }));

    test('getSalesAccounts(my, vendor)',
        verifyAPICall({
            fn: 'getSalesAccounts',
            args: ['my', 'vendor'],
            response: {sales_accounts: 'accounts', status: 'success'}
        }));

    test('getSalesAccounts(user, vendor)',
        verifyAPICall({
            fn: 'getSalesAccounts',
            args: ['user', 'vendor'],
            response: {sales_accounts: 'accounts', status: 'success'}
        }));

    test('resetCurrentCredentials()',
        verifyAPICall({fn: 'resetCurrentCredentials'}));

    test('verifyPhoneNumber(',
        verifyAPICall({fn: 'verifyPhoneNumber'}));

    test('setMeterState(off)',
        verifyAPICall({fn: 'setMeterState', args: ['off']}));
});
