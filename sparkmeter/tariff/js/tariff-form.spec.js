/* global beforeEach,describe,expect,it */
'use strict';

var TariffForm = require('tariff/js/tariff-form.js');

describe('TarrifForm', () => {
    describe('method: fieldRegEx', () => {
        var el;

        beforeEach(() => {
            el = '<input class="form-control numeric no-negative" id="flat_price" name="flat_price" type="text" value="-30">';
        });

        it('should remove negative symbols', () => {
            var result = TariffForm.fieldRegEx(el);
            var int = 30;
            expect($(result).val()).toBe(int.toString());
        });
    });
});
