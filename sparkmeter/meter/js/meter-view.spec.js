// -*- coding: utf-8 -*-
// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//
/* global afterEach,beforeEach,describe,expect,test,jest */

jest.mock('backend.js');

const backend = require('backend.js').backend;

const MeterView = require('meter/js/meter-view.js');

describe('MeterView', () => {
    let el = null;
    beforeEach(() => {
        el = $('<div>' +
            '<div class="dropdown-menu meter-state">' +
            '<li><a data-meter-state="on">On</a></li>' +
            '<li><a data-meter-state="off">Off</a></li>' +
            '</div>' +
            '<span class="meter-state-text"></span>' +
            '<span id="meter-state-color"></span>' +
            '<button id="verify-phone-number" class=""></button>' +
            '<div class="alerts"></div>' +
            '</div>');
        $(document.body).append(el);
    });

    afterEach(() => {
        if (el !== null) {
            el.remove();
            el = null;
        }
    });

    describe('State', () => {
        test('can be turned on', done => {
            backend.mockCall('setMeterState', {
                state_value: 2,
                state_text: "Auto (On)"
            });
            new MeterView.MeterView();

            $(".dropdown-menu.meter-state > li > a[data-meter-state='on']").click();
            setTimeout(function() {
                expect($(".meter-state-text").text()).toBe("Auto (On)");
                expect($("#meter-state-color").attr('class')).toBe("triangle-button green");
                done();
            }, 0);
        });
        test('can be turned off', done => {
            backend.mockCall('setMeterState', {
                state_value: 0,
                state_text: "Off"
            });
            new MeterView.MeterView();

            $(".dropdown-menu.meter-state > li > a[data-meter-state='off']").click();
            setTimeout(function() {
                expect($(".meter-state-text").text()).toBe("Off");
                expect($("#meter-state-color").attr('class')).toBe("triangle-button red");
                done();
            }, 0);
        });
    });

    describe('Phone Number', () => {
        test('can be verified', done => {
            backend.mockCall('verifyPhoneNumber', {phone_number: "+1234"});
            new MeterView.MeterView();
            $("button#verify-phone-number").click();

            expect($("button#verify-phone-number").attr("disabled")).toBe("disabled");

            setTimeout(function() {
                expect($(".alerts").html()).toBe(
                    '<div class="alert alert-success" style="opacity: 0;">Verification sent to +1234</div>');
                done();
            }, 0);
        });
    });

    describe('Tags', () => {
        test('are rendered properly', () => {
        });
    });
});
