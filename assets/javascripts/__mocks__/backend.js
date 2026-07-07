'use strict';

/* global jest */

const backend = jest.genMockFromModule('backend.js');

class BackendAPIMock {

    constructor() {
        this.mockCalls = Object.create(null);
    }

    mockCall(funcName, value) {
        if (!(funcName in this.mockCalls)) {
            this.mockCalls[funcName] = [];
        }
        let calls = this.mockCalls[funcName];
        calls.push(value);
    }

    _popReturnValue(funcName) {
        let mockCall = this.mockCalls[funcName];
        if (mockCall === undefined) {
            throw new Error("No mocks configured for " + funcName);
        }
        let d = $.Deferred();
        d.resolve(mockCall.pop());
        return d.promise();
    }

    getTariff(role) {
        return this._popReturnValue('getTariff');
    }

    getTariffs(role) {
        return this._popReturnValue('getTariffs');
    }

    getUsersByRole(role) {
        return this._popReturnValue('getUsersByRole');
    }

    getLatestReadings() {
        return this._popReturnValue('getLatestReadings');
    }

    getTransactions() {
        return this._popReturnValue('getTransactions');
    }

    getMessages() {
        return this._popReturnValue('getMessages');
    }

    getGrounds() {
        return this._popReturnValue('getGrounds');
    }

    getCustomerMeters() {
        return this._popReturnValue('getCustomerMeters');
    }

    getTotalizerMeters() {
        return this._popReturnValue('getTotalizerMeters');
    }

    getSalesAccounts(accountType) {
        return this._popReturnValue('getSalesAccounts');
    }

    resetCurrentCredentials() {
        return this._popReturnValue('resetCurrentCredentials');
    }

    setMeterState(state) {
        return this._popReturnValue('setMeterState');
    }

    verifyPhoneNumber() {
        return this._popReturnValue('verifyPhoneNumber');
    }
}

backend.backend = new BackendAPIMock();

module.exports = backend;
