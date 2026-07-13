// -*- coding: utf-8 -*-
// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//

/* global afterEach,beforeEach,describe,expect,test,jest,spyOn */

jest.mock('backend.js');
jest.mock('datatables.js');

const backend = require('backend.js').backend;
const datatables = require('datatables.js');

const LatestReadings = require('reading/js/latest-readings.js');
const DateUtils = require('dateutils.js');

window.$.fn.dataTable = { ext: {} };

const latest_readings = [
    {
        "address": "123 Street apt 1",
        "age": "",
        "customer_code": "123",
        "customer_name": "customer1",
        "current_avg": "",
        "current_max": "",
        "current_min": "",
        "energy": "",
        "frequency": "",
        "ground_name": "test_grid_2",
        "ground_serial": "",
        "heartbeat_end": "2013-01-01T01:00:15",
        "serial": "SM15R-01-00000001",
        "state": "",
        "true_power_avg": "",
        "true_power_inst": "",
        "uptime": "1000",
        "user_power_limit": "",
        "voltage_avg": "",
        "voltage_max": "",
        "voltage_min": ""
    },
    {
        "address": "",
        "age": "",
        "customer_code": "456",
        "customer_name": "customer2",
        "current_avg": "",
        "current_max": "",
        "current_min": "",
        "energy": "",
        "frequency": "",
        "ground_name": "test_grid_1",
        "ground_serial": "",
        "heartbeat_end": "2013-01-01T01:00:15",
        "serial": "SM15R-01-00000002",
        "state": "",
        "true_power_avg": "",
        "true_power_inst": "",
        "uptime": "1000",
        "user_power_limit": "",
        "voltage_avg": "",
        "voltage_max": "",
        "voltage_min": ""
    },
    {
        "address": "",
        "age": "",
        "customer_code": "789",
        "customer_name": "customer3",
        "current_avg": "",
        "current_max": "",
        "current_min": "",
        "energy": "",
        "frequency": "",
        "ground_name": "test_grid_3",
        "ground_serial": "",
        "heartbeat_end": "",
        "serial": "SM15R-01-00000003",
        "state": "",
        "true_power_avg": "",
        "true_power_inst": "",
        "uptime": "",
        "user_power_limit": "",
        "voltage_avg": "",
        "voltage_max": "",
        "voltage_min": ""
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

const readings = {
    heartbeat_seconds: 90,
    readings: latest_readings
};

describe('LastestReadings', () => {
    let el = null;
    beforeEach(() => {
        el = $('<meta itemprop="config-ground" content="null">' +
            '<select id="transaction" class="select-filter latest-readings">' +
            '<option value="">All</option>' +
            '</select>' +
            '<span class="title"></span>' +
            '<input id="Auto-refresh" class="iButton-icons" type="checkbox" checked="checked">' +
            '<input id="Color" class="iButton-icons" type="checkbox">' +
            '<table id="latestreadings" class="table-striped table-hover"/><tbody>' +
            '<tr">' + '<td></td>' + '</tr>' +
            '</tbody></table>');
        $(document.body).append(el);
    });

    afterEach(() => {
        if (el !== null) {
            el.remove();
            el = null;
        }
    });

    describe('Rendering', () => {
        test('should render dropdown', () => {
            backend.mockCall('getLatestReadings', readings);
            backend.mockCall('getGrounds', grounds);
            new LatestReadings.LatestReadings();

            expect(datatables.GroundDropDown.mock.calls.length).toBe(2);
        });

        test('should create a datatable', () => {
            backend.mockCall('getLatestReadings', readings);
            let latestReadings = new LatestReadings.LatestReadings();

            expect(latestReadings.table).toBeDefined();
        });

        test('should update a datatable', () => {
            backend.mockCall('getLatestReadings', readings);
            let latestReadings = new LatestReadings.LatestReadings();
            let tableAjax = latestReadings.table.ajax;
            spyOn(tableAjax, 'reload');
            latestReadings.update();

            expect(tableAjax.reload).toHaveBeenCalled();
        });

        describe('Tooltip tests', () => {
            backend.mockCall('getLatestReadings', readings);
            let latestReadings = new LatestReadings.LatestReadings();
            test('Should format frequency display to two decimals', () => {
                expect(latestReadings.columns[4].render(49.959999084472656, "display")).toBe(
                    "49.96"
                );
            });
            test('Should format voltage display to two decimals', () => {
                expect(latestReadings.columns[5].render(240.1599884033203, "display")).toBe(
                    "240.16"
                );
            });
            test('Should format current display to three decimals', () => {
                expect(latestReadings.columns[6].render(0.09800000488758087, "display")).toBe(
                    "0.098"
                );
            });
            test('Should format totalizer meter serial tooltip property', () => {
                expect(latestReadings._formatTooltipForField("serial",
                    {"customer_name": null, "customer_code": "123"})).toBe(
                        ''
                );
                expect(latestReadings._formatTooltipForField("serial",
                    {"customer_name": null, "customer_code": null})).toBe(
                        ''
                );
            });
            test('Should format voltage tooltip property', () => {
                expect(latestReadings._formatTooltipForField("voltage_avg",
                    {voltage_min: "210", voltage_max: "230"})).toBe(
                    "Min: 210<br>Max: 230<br>"
                );
            });
            test('Should format current tooltip property', () => {
                expect(latestReadings._formatTooltipForField("current_avg",
                    {current_min: "0.1", current_max: "0.7"})).toBe(
                    "Min: 0.1<br>Max: 0.7<br>"
                );
            });
            test('Should format uptime tooltip property', () => {
                expect(latestReadings._formatTooltipForField("uptime",
                    {uptime: "42807", heartbeat_end: "2017-03-15 20:30:00"})).toBe(
                    "Boot time: 2017-03-15 08:36:33<br>Run time: 11 hours"
                );
            });
            test('Should format age tooltip property', () => {
                spyOn(DateUtils, 'utcnow').and.returnValue(
                    DateUtils.astimestamp("2017-03-16T02:00:00"));
                expect(latestReadings._formatTooltipForField("heartbeat_end",
                    {heartbeat_end: "2017-03-15 20:30:00"})).toBe(
                    "Received: 2017-03-15 20:30:00<br>5 hours<br>22 heartbeat(s) ago."
                );
            });
        });

        describe('Color row function tests', () => {
            let latestReadings;
            let age;

            beforeEach(() => {
                backend.mockCall('getLatestReadings', readings);
                latestReadings = new LatestReadings.LatestReadings();
                $('table').append('<tbody><tr></tr></tbody>');
            });

            test('should add class heartbeat-never', () => {
                age = '';
                latestReadings.color_row($('tr')[0], age);

                expect($('tr').attr('class')).toBe('heartbeat-never');
            });

            test('should add class heartbeat-current', () => {
                age = 1;
                latestReadings.heartbeat_seconds = 3;
                latestReadings.color_row($('tr')[0], age);

                expect($('tr').attr('class')).toBe('heartbeat-current');
            });

            test('should add class heartbeat-day-old', () => {
                age = 90000;
                latestReadings.color_row($('tr')[0], age);

                expect($('tr').attr('class')).toBe('heartbeat-day-old');
            });

            test('should add class heartbeat-hour-old', () => {
                age = 4000;
                latestReadings.color_row($('tr')[0], age);

                expect($('tr').attr('class')).toBe('heartbeat-hour-old');
            });

            test('should add class heartbeat-last', () => {
                age = 1;
                latestReadings.heartbeat_seconds = 1;
                latestReadings.color_row($('tr')[0], age);

                expect($('tr').attr('class')).toBe('heartbeat-last');
            });

            test('should add class heartbeat-lost', () => {
                age = 3;
                latestReadings.heartbeat_seconds = 1.1;
                latestReadings.color_row($('tr')[0], age);

                expect($('tr').attr('class')).toBe('heartbeat-lost');
            });
        });
    });

    describe('Action', () => {
        test('should disable refresh', () => {
            backend.mockCall('getLatestReadings', readings);
            let latestReadings = new LatestReadings.LatestReadings();
            spyOn(latestReadings, 'disable_auto_refresh');

            $('#Auto-refresh').click();
            expect(latestReadings.disable_auto_refresh).toHaveBeenCalled();
        });

        test('should disable refresh', () => {
            backend.mockCall('getLatestReadings', readings);
            let latestReadings = new LatestReadings.LatestReadings();
            spyOn(latestReadings, 'enable_auto_refresh');

            $('#Auto-refresh').click();
            $('#Auto-refresh').click();

            expect(latestReadings.enable_auto_refresh).toHaveBeenCalled();
        });

        test('should set refresh interval', () => {
            backend.mockCall('getLatestReadings', readings);
            let latestReadings = new LatestReadings.LatestReadings();
            latestReadings.enable_auto_refresh();

            expect(latestReadings.refresh_interval).toBeDefined();
            expect(latestReadings.refresh_interval).toBeGreaterThan(0);
        });

        test('should clear refresh interval', () => {
            backend.mockCall('getLatestReadings', readings);
            let latestReadings = new LatestReadings.LatestReadings();
            latestReadings.disable_auto_refresh();

            expect(latestReadings.refresh_interval).toBeUndefined();
        });

        test('should add color', () => {
            backend.mockCall('getLatestReadings', readings);
            let latestReadings = new LatestReadings.LatestReadings();
            spyOn(latestReadings, 'color_row');
            $('table').append('<tbody><tr></tr></tbody>');
            $('#Color').click();
            expect($('#Color').prop("checked")).toBe(true);
            expect(latestReadings.color_row).toHaveBeenCalled();
            expect($('#latestreadings').hasClass('table-striped table-hover')).toBe(false);
        });

        test('should remove color', () => {
            backend.mockCall('getLatestReadings', readings);
            let latestReadings = new LatestReadings.LatestReadings();

            spyOn(latestReadings, 'remove_colors');

            $('#Color').click();
            $('#Color').click();

            expect($('#Color').prop("checked")).toBe(false);
            expect(latestReadings.remove_colors).toHaveBeenCalled();
            // expect($('#latestreadings').hasClass('table-striped table-hover')).toBe(true);
        });

        test('should remove table row classes', () => {
            backend.mockCall('getLatestReadings', readings);
            let latestReadings = new LatestReadings.LatestReadings();
            latestReadings.remove_colors();
            expect($("tr").hasClass('heartbeat-never heartbeat-current heartbeat-day-old heartbeat-hour-old heartbeat-last heartbeat-lost')).toBe(false);
        });
    });
});
