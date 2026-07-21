// -*- coding: utf-8 -*-
// Copyright © 2013-2026 EarthSpark International Corp.
// SPDX-License-Identifier: Apache-2.0
//
/* global afterEach,beforeEach,describe,expect,it,jest */
'use strict';

const MeterTariffModal = require('meter/js/meter-tariff-modal.js');

const ADD_NEW = '__add_new__';
const BLANK = '__None';
const MODAL_URL = '/tariff/add-modal';

const TARIFF_ID = '4a2d8cf2-3d61-4a3f-9c4e-0f0f9b1f6c11';

// Cut-down stand-in for the fragment /tariff/add-modal returns: the form, the
// params element TariffForm reads, one type toggle with its section, and the
// block-rate editor modal the shared partial emits inside the fragment.
function fragment() {
    return (
        '<form class="form form-horizontal tariff" id="tariff-modal-form"' +
        '      method="POST" action="' + MODAL_URL + '">' +
        '  <div id="tariff-form-params"' +
        '       data-blockrates="[]" data-blockrates-title="&quot;Edit block rate&quot;"' +
        '       data-tous="[]" data-tous-title="Edit time of use"' +
        '       data-load-limits="[]" data-load-limits-title="Edit scheduled load limits"></div>' +
        '  <input id="name" name="name" type="text" value="">' +
        '  <input id="blockrates" name="blockrates" type="hidden" value="[]">' +
        '  <input id="tous" name="tous" type="hidden" value="[]">' +
        '  <input id="load_limits" name="load_limits" type="hidden" value="[]">' +
        '  <label><input type="radio" name="tariff_type" id="tariff_type" value="flat" checked>Flat</label>' +
        '  <label><input type="radio" name="tariff_type" id="tariff_type" value="blockrate">Block rate</label>' +
        '  <div class="form-group tariff_type flat">flat price</div>' +
        '  <div class="form-group tariff_type blockrate hide">' +
        '    <table id="tariff-blockrates"><tbody></tbody></table>' +
        '  </div>' +
        '  <label><input type="radio" name="load_limit_type" id="load_limit_type" value="flat" checked>Flat</label>' +
        '  <label><input type="radio" name="load_limit_type" id="load_limit_type" value="scheduled">Scheduled</label>' +
        '  <div class="form-group load_limit_type flat">flat load limit</div>' +
        '  <div class="form-group load_limit_type scheduled hide">' +
        '    <table id="tariff-load-limits"><tbody></tbody></table>' +
        '  </div>' +
        '  <input type="checkbox" id="tou_enabled" name="tou_enabled">' +
        '  <div class="form-group tou hide"><table id="tariff-tous"><tbody></tbody></table></div>' +
        '  <input type="checkbox" id="plan_enabled" name="plan_enabled">' +
        '  <div class="form-group plan-price hide">plan price</div>' +
        '  <div class="form-group plan-fixed-fee hide">plan fixed fee</div>' +
        '  <input type="checkbox" id="daily_energy_limit_enabled" name="daily_energy_limit_enabled">' +
        '  <div class="form-group daily-energy-limit-value hide">value</div>' +
        '  <div class="form-group daily-energy-limit-reset-hour hide">reset hour</div>' +
        '  <div class="modal" id="blockrateModal"><div class="modal-content">' +
        '    <input id="id" name="id" type="hidden" value="">' +
        '    <input id="lower" name="lower" type="text" value="">' +
        '    <input id="upper" name="upper" type="text" value="">' +
        '    <input id="value" name="value" type="text" value="">' +
        '    <button id="save" type="button"></button>' +
        '  </div></div>' +
        '  <div class="modal" id="touModal"><div class="modal-content">' +
        '    <button id="save" type="button"></button>' +
        '  </div></div>' +
        '  <div class="modal" id="loadLimitModal"><div class="modal-content">' +
        '    <button id="save" type="button"></button>' +
        '  </div></div>' +
        '</form>'
    );
}

const LOGIN_PAGE = '<html><body><form id="login_user_form"><input name="password"></form></body></html>';

function pageHtml() {
    return (
        '<div class="alerts"></div>' +
        '<form id="meter-form">' +
        '  <div id="meter-tariff-modal-params"' +
        '       data-modal-url="' + MODAL_URL + '"' +
        '       data-add-new-value="' + ADD_NEW + '"' +
        '       data-add-new-label="&lt;Add New&gt;"' +
        '       data-text-title="Add a New Tariff"' +
        '       data-text-loading="Loading tariff form..."' +
        '       data-text-cancel="Cancel"' +
        '       data-text-save="Save"' +
        '       data-text-saving="Saving..."' +
        '       data-text-created="Tariff created."' +
        '       data-text-load-error="Could not load the tariff form."' +
        '       data-text-save-error="Could not save the tariff."' +
        '       data-text-session-expired="Session expired."></div>' +
        '  <select id="tariff" name="tariff">' +
        '    <option value="' + BLANK + '">Select a tariff</option>' +
        '    <option value="11111111-1111-1111-1111-111111111111">Existing</option>' +
        '  </select>' +
        '</form>'
    );
}

describe('MeterTariffModal', () => {
    let getDeferred;
    let ajaxDeferred;

    beforeEach(() => {
        document.body.innerHTML = pageHtml();
        document.body.className = '';

        // Widget plugins are attached by startup.js in the browser; the modal
        // only ever calls them, so no-ops are enough here.
        ['select2', 'numeric', 'iButton', 'datetimepicker'].forEach((plugin) => {
            $.fn[plugin] = jest.fn(function() { return this; });
        });

        getDeferred = $.Deferred();
        ajaxDeferred = $.Deferred();
        $.get = jest.fn(() => getDeferred.promise());
        $.ajax = jest.fn(() => ajaxDeferred.promise());
    });

    afterEach(() => {
        $(document).off('.metertariff');
        $(document).off('.tariffform');
        document.body.innerHTML = '';
    });

    function open() {
        const modal = new MeterTariffModal.MeterTariffModal();
        $('select#tariff').val(ADD_NEW).trigger('change');
        return modal;
    }

    function openWithFragment() {
        const modal = open();
        getDeferred.resolve(fragment());
        return modal;
    }

    function alerts() {
        return $('.alerts').text();
    }

    it('appends the add-new option with its decoded label', () => {
        new MeterTariffModal.MeterTariffModal();

        const option = $('select#tariff option[value="' + ADD_NEW + '"]');
        expect(option.length).toBe(1);
        expect(option.text()).toBe('<Add New>');
    });

    it('does nothing on a page without the params element', () => {
        $('#meter-tariff-modal-params').remove();
        new MeterTariffModal.MeterTariffModal();

        expect($('#meter-tariff-modal').length).toBe(0);
    });

    it('loads the fragment into the modal when add-new is picked', () => {
        openWithFragment();

        expect($.get).toHaveBeenCalledWith(MODAL_URL);
        expect($('#meter-tariff-modal form#tariff-modal-form').length).toBe(1);
    });

    describe('tariff form behavior inside the modal (F2)', () => {
        it('reveals the block-rate section when block rate is selected', () => {
            openWithFragment();

            expect($('#meter-tariff-modal div.tariff_type.blockrate').hasClass('hide')).toBe(true);

            $('#meter-tariff-modal input:radio[value="blockrate"]').prop('checked', true).trigger('change');

            expect($('#meter-tariff-modal div.tariff_type.blockrate').hasClass('hide')).toBe(false);
            expect($('#meter-tariff-modal div.tariff_type.flat').hasClass('hide')).toBe(true);
        });

        it('reveals the scheduled load limit section', () => {
            openWithFragment();

            $('#meter-tariff-modal input:radio[name="load_limit_type"][value="scheduled"]')
                .prop('checked', true).trigger('change');

            expect($('#meter-tariff-modal div.load_limit_type.scheduled').hasClass('hide')).toBe(false);
            expect($('#meter-tariff-modal div.load_limit_type.flat').hasClass('hide')).toBe(true);
        });

        [
            ['tou_enabled', '.tou'],
            ['plan_enabled', '.plan-price'],
            ['plan_enabled', '.plan-fixed-fee'],
            ['daily_energy_limit_enabled', '.daily-energy-limit-value'],
            ['daily_energy_limit_enabled', '.daily-energy-limit-reset-hour']
        ].forEach((toggle) => {
            const checkbox = toggle[0];
            const section = toggle[1];

            it('reveals ' + section + ' when ' + checkbox + ' is checked', () => {
                openWithFragment();

                $('#meter-tariff-modal #' + checkbox).prop('checked', true).trigger('change');

                expect($('#meter-tariff-modal ' + section).hasClass('hide')).toBe(false);
            });
        });

        it('populates the hidden collection field from the editor', () => {
            openWithFragment();

            $('#blockrateModal input#id').val('a-block-rate');
            $('#blockrateModal input#lower').val('0');
            $('#blockrateModal input#upper').val('20');
            $('#blockrateModal input#value').val('1.5');
            $('#blockrateModal button#save').trigger('click');

            expect($('#meter-tariff-modal #tariff-blockrates tbody tr').length).toBe(1);
            const blockrates = JSON.parse($('#meter-tariff-modal #blockrates').val());
            expect(blockrates).toEqual([{id: 'a-block-rate', lower: 0, upper: 20, value: 1.5}]);
        });

        it('binds the toggles once when the fragment is re-rendered', () => {
            openWithFragment();

            // A 400 re-renders the fragment; the delegated handlers must not
            // stack up on `document`.
            const handlers = () => $._data(document, 'events').change.length;
            const before = handlers();
            $('#meter-tariff-modal-save').trigger('click');
            ajaxDeferred.reject({status: 400, responseText: fragment()});

            expect(handlers()).toBe(before);
        });
    });

    describe('nested editors (F5)', () => {
        it('moves the collection editors out of the tariff modal', () => {
            openWithFragment();

            ['blockrateModal', 'touModal', 'loadLimitModal'].forEach((id) => {
                expect($('#meter-tariff-modal #' + id).length).toBe(0);
                expect($('body').children('#' + id).length).toBe(1);
            });
        });

        it('drops editors from a previous render instead of stacking them', () => {
            openWithFragment();
            $('#meter-tariff-modal-save').trigger('click');
            ajaxDeferred.reject({status: 400, responseText: fragment()});

            expect($('body').children('#blockrateModal').length).toBe(1);
        });

        it('leaves an editor it did not relocate alone', () => {
            openWithFragment();
            // The ids come from a shared partial, so anything else on the page
            // may carry them too.
            $('body').append('<div class="modal" id="touModal" data-owner="page"></div>');

            $('#meter-tariff-modal-save').trigger('click');
            ajaxDeferred.reject({status: 400, responseText: fragment()});

            expect($('body').children('#touModal[data-owner="page"]').length).toBe(1);
        });

        it('keeps the body scroll lock while the tariff modal is still open', () => {
            openWithFragment();
            $('#blockrateModal').modal('show');

            $('#blockrateModal').modal('hide');

            expect($(document.body).hasClass('modal-open')).toBe(true);
        });
    });

    describe('stacked modals (F5)', () => {
        beforeEach(() => {
            // The backdrop does not exist yet when the module reacts to
            // `show.bs.modal`, so it is placed from a zero-delay timeout.
            jest.useFakeTimers();
        });

        afterEach(() => {
            jest.useRealTimers();
        });

        function zIndexes(selector) {
            return $(selector).map(function() { return this.style.zIndex; }).get();
        }

        function openEditorOnTop() {
            openWithFragment();
            jest.runAllTimers();
            $('#blockrateModal').modal('show');
            jest.runAllTimers();
        }

        it('raises an editor opened on top of the tariff modal above it', () => {
            openEditorOnTop();

            expect(zIndexes('#meter-tariff-modal')).toEqual(['1050']);
            expect(zIndexes('#blockrateModal')).toEqual(['1070']);
        });

        it('gives each stacked modal its own backdrop just underneath it', () => {
            openEditorOnTop();

            // Document order: the tariff modal's backdrop, then the editor's.
            expect(zIndexes('.modal-backdrop')).toEqual(['1040', '1060']);
        });

        it('leaves a backdrop that was already placed where it is', () => {
            openEditorOnTop();
            $('#blockrateModal').modal('hide');
            $('#touModal').modal('show');
            jest.runAllTimers();

            expect(zIndexes('.modal-backdrop')).toEqual(['1040', '1060']);
        });
    });

    describe('submitting (F4, F8)', () => {
        it('submits through AJAX when the form is submitted with Enter', () => {
            openWithFragment();

            const event = $.Event('submit');
            $('#tariff-modal-form').trigger(event);

            expect(event.isDefaultPrevented()).toBe(true);
            expect($.ajax).toHaveBeenCalledTimes(1);
            expect($.ajax.mock.calls[0][0].url).toBe(MODAL_URL);
            expect($.ajax.mock.calls[0][0].method).toBe('POST');
        });

        it('refuses a second request while one is in flight', () => {
            openWithFragment();

            $('#meter-tariff-modal-save').trigger('click');
            $('#meter-tariff-modal-save').trigger('click');
            $('#tariff-modal-form').trigger('submit');

            expect($.ajax).toHaveBeenCalledTimes(1);
            expect($('#meter-tariff-modal-save').prop('disabled')).toBe(true);
            expect($('#meter-tariff-modal-save').text()).toBe('Saving...');
        });

        it('adds the created tariff and selects it', () => {
            openWithFragment();
            $('#meter-tariff-modal-save').trigger('click');

            ajaxDeferred.resolve({
                message: 'Tariff created.',
                tariff: {id: TARIFF_ID, name: 'MODAL TARIFF'}
            });

            const option = $('select#tariff option[value="' + TARIFF_ID + '"]');
            expect(option.text()).toBe('MODAL TARIFF');
            // The created tariff sorts before the add-new option.
            expect(option.next().val()).toBe(ADD_NEW);
            expect($('select#tariff').val()).toBe(TARIFF_ID);
            expect(alerts()).toContain('Tariff created.');
            expect($('#meter-tariff-modal-save').prop('disabled')).toBe(false);
        });

        it('ignores a response that arrives after the modal was dismissed', () => {
            openWithFragment();
            $('#meter-tariff-modal-save').trigger('click');

            $('#meter-tariff-modal').trigger(
                $.Event('hidden.bs.modal', {target: $('#meter-tariff-modal')[0]})
            );
            ajaxDeferred.resolve({tariff: {id: TARIFF_ID, name: 'MODAL TARIFF'}});

            expect($('select#tariff option[value="' + TARIFF_ID + '"]').length).toBe(0);
            expect($('select#tariff').val()).toBe(BLANK);
        });

        it('re-renders the fragment with its errors on a 400', () => {
            openWithFragment();
            $('#meter-tariff-modal-save').trigger('click');

            const invalid = fragment().replace(
                '<input id="name"',
                '<span class="help-block note">Please set a name for this tariff</span><input id="name"'
            );
            ajaxDeferred.reject({status: 400, responseText: invalid});

            expect($('#meter-tariff-modal').text()).toContain('Please set a name for this tariff');
            expect($('#meter-tariff-modal-save').prop('disabled')).toBe(false);
        });

        it('reports a failure that is not a validation error', () => {
            openWithFragment();
            $('#meter-tariff-modal-save').trigger('click');

            ajaxDeferred.reject({status: 500, responseText: ''});

            expect(alerts()).toContain('Could not save the tariff.');
        });
    });

    describe('expired session (F6)', () => {
        it('does not inject the login page the GET redirected to', () => {
            open();
            getDeferred.resolve(LOGIN_PAGE);

            expect($('#meter-tariff-modal #login_user_form').length).toBe(0);
            expect(alerts()).toContain('Session expired.');
            expect($('select#tariff').val()).toBe(BLANK);
        });

        it('does not throw when the POST comes back as a login page', () => {
            openWithFragment();
            $('#meter-tariff-modal-save').trigger('click');

            ajaxDeferred.resolve(LOGIN_PAGE);

            expect(alerts()).toContain('Session expired.');
            expect($('select#tariff').val()).toBe(BLANK);
        });

        it('reports a failed load', () => {
            open();
            getDeferred.reject();

            expect(alerts()).toContain('Could not load the tariff form.');
            expect($('select#tariff').val()).toBe(BLANK);
        });
    });

    describe('restoring the selection (F7)', () => {
        it('restores the blank option when nothing was selected', () => {
            open();
            getDeferred.reject();

            const select = $('select#tariff')[0];
            expect(select.value).toBe(BLANK);
            expect(select.selectedIndex).toBe(0);
        });

        it('restores the previously selected tariff', () => {
            const existing = '11111111-1111-1111-1111-111111111111';
            new MeterTariffModal.MeterTariffModal();
            $('select#tariff').val(existing).trigger('focusin').trigger('change');

            $('select#tariff').val(ADD_NEW).trigger('focusin').trigger('change');
            getDeferred.resolve(fragment());
            $('#meter-tariff-modal').trigger(
                $.Event('hidden.bs.modal', {target: $('#meter-tariff-modal')[0]})
            );

            expect($('select#tariff').val()).toBe(existing);
        });
    });
});
