// -*- coding: utf-8 -*-
// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//
// SMSTemplateExampleRenderer unittests
/* global beforeEach,describe,expect,test */

require('vendor/angular-1.4.9.js');
require('vendor/angular-resource-1.4.9.js');
require('vendor/ng-textcomplete-0.6.0.js');
require('vendor/ui-bootstrap-custom-tpls-1.1.1.js');
require('../../../scripts/config/node_modules/angular-mocks/angular-mocks.js');

require('core.app.js');
require('./sms.app.js');
require('./smsexamplerenderer.js');

describe('SMSTemplateExampleRenderer', () => {
    beforeEach(window.module('sparkmeter.event.sms', function($provide) {
        let eventTypes = {
            getKeywordsForEventType: function() {
                return [{name: 'xxx', example: 'yyy'},
                    {name: 'amount', example: 'zzz'}];
            }
        };
        let svc = {
            query: function() {
                return {
                    then: function(done) {
                        done(eventTypes);
                    }
                };
            }
        };
        $provide.value('SMSEventTypesService', svc);
    }));

    test('should render', window.inject(function(templateExampleRendererFilter) {
        expect(templateExampleRendererFilter('{xxx}', 'customer-low-balance')).toBe('yyy');
    }));

    test('should render multiple', window.inject(function(templateExampleRendererFilter) {
        expect(templateExampleRendererFilter('{xxx} {xxx} {xxx}',
            'customer-low-balance')).toBe('yyy yyy yyy');
    }));

    test('should render empty', window.inject(function(templateExampleRendererFilter) {
        expect(templateExampleRendererFilter('', 'customer-low-balance')).toBe('');
    }));

    test('should render undefined', window.inject(function(templateExampleRendererFilter) {
        expect(templateExampleRendererFilter(undefined, 'customer-low-balance')).toBe('');
    }));
});
