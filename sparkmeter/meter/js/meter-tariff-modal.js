// -*- coding: utf-8 -*-
// Copyright © 2013-2026 EarthSpark International Corp.
// All Rights Reserved.
//
// Lets the customer meter form create a tariff without leaving the page: the
// tariff select carries an extra option that loads /tariff/add-modal into a
// modal, posts it over AJAX, and inserts the created tariff into the select.

var base = require('base.js');
var TariffForm = require('tariff/js/tariff-form.js');

var MODAL_ID = 'meter-tariff-modal';
var MODAL_SELECTOR = '#' + MODAL_ID;
var FORM_SELECTOR = 'form#tariff-modal-form';

// QuerySelectField(allow_blank=True) renders its blank option with this value,
// so this is what "no tariff chosen" means to the select. Restoring the select
// to '' instead would match no option and render it empty.
var BLANK_VALUE = '__None';

// The tariff form partial emits one editor modal per collection field. Bootstrap
// 3 does not support a modal nested inside another modal, so these are moved out
// of the fragment and appended to <body> as siblings of the tariff modal.
var EDITOR_MODAL_SELECTOR = '#loadLimitModal, #blockrateModal, #touModal';

// Bootstrap 3 gives every modal the same z-index, so a second modal opened on
// top of the first lands under the first one's backdrop. Each stacked modal is
// raised above the one below it, with its own backdrop just underneath.
// The first modal keeps Bootstrap's own values (1050 dialog / 1040 backdrop).
var BASE_MODAL_Z_INDEX = 1050;
var MODAL_Z_INDEX_STEP = 20;
var BACKDROP_Z_INDEX_OFFSET = 10;

// Bootstrap 3 marks an open modal with `in`. `:visible` would be equivalent in
// a browser, but it is layout-dependent, and `in` is what Bootstrap itself
// toggles around the `show`/`hidden` events.
var OPEN_MODAL_SELECTOR = '.modal.in';

function MeterTariffModal() {
    this._init();
}

exports.MeterTariffModal = MeterTariffModal;

MeterTariffModal.prototype = {
    _init: function() {
        this.params = $('#meter-tariff-modal-params');
        this.select = $('select#tariff');
        if (!this.select.length || !this.params.length) {
            return;
        }

        this.addNewValue = this.params.attr('data-add-new-value');
        this.previousValue = this.select.val();
        this.requestSeq = 0;
        this.pendingRequestId = null;
        this.editorModals = $();
        // The body carries no scrollbar compensation until a modal is open.
        this.scrollbarPad = '';

        this.ensureSelectOptions();
        this.ensureModal();
        this.bindEvents();
    },

    text: function(name) {
        return this.params.attr('data-text-' + name);
    },

    bindEvents: function() {
        var self = this;

        this.select.on('focusin', function() {
            // Focus can land here again while the modal is open; the sentinel
            // is not a value worth remembering.
            if ($(this).val() === self.addNewValue) {
                return;
            }
            self.previousValue = self.currentTariffValue();
        });

        this.select.on('change', function() {
            if ($(this).val() === self.addNewValue) {
                self.openModal();
            } else {
                self.previousValue = self.currentTariffValue();
            }
        });

        this.modal.on('hidden.bs.modal', function() {
            self.abortPendingRequest();
            self.restoreTariffSelection();
        });

        this.modal.on('click', '#meter-tariff-modal-save', function(event) {
            event.preventDefault();
            self.submitModal();
        });

        // The fragment is a real <form>, so Enter in any of its fields would
        // otherwise submit it as a full-page POST and navigate away from the
        // half-filled meter form.
        this.modal.on('submit', FORM_SELECTOR, function(event) {
            event.preventDefault();
            self.submitModal();
        });

        // Bootstrap 3 gives every modal the same z-index and unwinds the whole
        // body scroll lock whenever any modal closes, which breaks the tariff
        // modal while one of its editors is open on top of it.
        $(document).on('show.bs.modal.metertariff', '.modal', function(event) {
            self.onAnyModalShow(event.currentTarget);
        });
        $(document).on('hide.bs.modal.metertariff', '.modal', function() {
            self.rememberScrollbarPad();
        });
        $(document).on('hidden.bs.modal.metertariff', '.modal', function() {
            self.onAnyModalHidden();
        });
    },

    onAnyModalShow: function(modal) {
        // Bootstrap adds `in` after this event, so this counts the modals that
        // are already open underneath the one being shown.
        var zIndex = BASE_MODAL_Z_INDEX + MODAL_Z_INDEX_STEP * $(OPEN_MODAL_SELECTOR).length;
        $(modal).css('z-index', zIndex);
        // The backdrop for this modal does not exist yet; Bootstrap appends it
        // while handling the same event. `modal-stack` marks the ones already
        // placed, so each new backdrop is the only unmarked one.
        setTimeout(function() {
            $('.modal-backdrop:not(.modal-stack)')
                .css('z-index', zIndex - BACKDROP_Z_INDEX_OFFSET)
                .addClass('modal-stack');
        }, 0);
    },

    rememberScrollbarPad: function() {
        // While a modal holds the scroll lock, Bootstrap pads <body> by the
        // width of the scrollbar it just hid. Read that padding before the
        // modal being hidden takes it back off.
        this.scrollbarPad = document.body.style.paddingRight;
    },

    onAnyModalHidden: function() {
        // Bootstrap drops `modal-open` off <body> and clears the scrollbar
        // compensation whenever any modal closes, which unlocks scrolling
        // behind a modal that is still open and shifts the page sideways.
        if (!$(OPEN_MODAL_SELECTOR).length) {
            return;
        }
        $(document.body).addClass('modal-open').css('padding-right', this.scrollbarPad);
    },

    ensureSelectOptions: function() {
        if (!this.select.find('option[value="' + this.addNewValue + '"]').length) {
            this.select.append(
                $('<option></option>')
                    .val(this.addNewValue)
                    .text(this.params.attr('data-add-new-label'))
            );
        }
    },

    ensureModal: function() {
        $('body').append(
            $('<div></div>')
                .addClass('modal fade')
                .attr({id: MODAL_ID, tabindex: '-1', role: 'dialog', 'aria-hidden': 'true'})
                .html(
                    '<div class="modal-dialog">' +
                    '  <div class="modal-content">' +
                    '    <div class="modal-header">' +
                    '      <button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>' +
                    '      <h4 class="modal-title"></h4>' +
                    '    </div>' +
                    '    <div class="modal-body"></div>' +
                    '    <div class="modal-footer">' +
                    '      <button type="button" class="btn btn-default" data-dismiss="modal"></button>' +
                    '      <button type="button" class="btn btn-primary" id="meter-tariff-modal-save"></button>' +
                    '    </div>' +
                    '  </div>' +
                    '</div>'
                )
        );
        this.modal = $(MODAL_SELECTOR);
        this.saveButton = this.modal.find('#meter-tariff-modal-save');
        this.modal.find('.modal-title').text(this.text('title'));
        this.modal.find('.modal-body').html($('<p></p>').text(this.text('loading')));
        this.modal.find('.modal-footer .btn-default').text(this.text('cancel'));
        this.saveButton.text(this.text('save'));
    },

    openModal: function() {
        var self = this;
        $.get(this.params.attr('data-modal-url'))
            .done(function(html) {
                if (!self.renderModal(html)) {
                    self.sessionExpired();
                    return;
                }
                self.modal.modal('show');
            })
            .fail(function() {
                base.flashText(self.text('load-error'), 'danger');
                self.restoreTariffSelection();
            });
    },

    /**
     * Inject a tariff form fragment into the modal body.
     *
     * @returns {boolean} false when the response is not a tariff form -- an
     *     expired session redirects to the login page, and jQuery follows the
     *     redirect, so the login page arrives here with a 200.
     */
    renderModal: function(html) {
        var fragment = $('<div></div>').html(html);
        if (!fragment.find(FORM_SELECTOR).length) {
            return false;
        }

        this.discardEditorModals();
        this.modal.find('.modal-body').html(fragment.contents());
        // Move the collection editors out of the tariff modal so Bootstrap can
        // stack them instead of nesting them. Hold on to them: the ids come
        // from a shared partial, so nothing else identifies them as ours.
        this.editorModals = this.modal.find(EDITOR_MODAL_SELECTOR).appendTo('body');
        this.setupModalWidgets();
        // Wire up the type toggles and the collection editors; TariffForm's
        // delegated handlers are namespaced and rebound, so re-rendering the
        // fragment after a 400 does not double-bind them.
        new TariffForm.TariffForm();
        return true;
    },

    discardEditorModals: function() {
        this.editorModals.remove();
        this.editorModals = $();
    },

    setupModalWidgets: function() {
        this.modal.find('select.select2').select2();
        this.modal.find('input.numeric').numeric();
        this.modal.find('.iButton').iButton();
        this.modal.find('.iButton-icons').iButton({
            labelOn: "<i class='icon-ok'></i>",
            labelOff: "<i class='icon-remove'></i>",
            handleWidth: 30
        });
        this.editorModals.find('input.timepicker').datetimepicker({
            datepicker: false,
            closeOnTimeSelect: true,
            format: 'H:i',
            mask: '29:00',
            allowTimes: [
                '00:00', '01:00', '02:00', '03:00', '04:00', '05:00',
                '06:00', '07:00', '08:00', '09:00', '10:00', '11:00',
                '12:00', '13:00', '14:00', '15:00', '16:00', '17:00',
                '18:00', '19:00', '20:00', '21:00', '22:00', '23:00', '00:00'
            ]
        });
    },

    submitModal: function() {
        var self = this;
        var form = this.modal.find(FORM_SELECTOR);
        // `tariff.name` has no unique constraint, so a second request would
        // happily create a duplicate tariff.
        if (!form.length || this.pendingRequestId !== null) {
            return;
        }

        var requestId = ++this.requestSeq;
        this.pendingRequestId = requestId;
        this.setSaving(true);
        $.ajax({
            url: form.attr('action'),
            method: 'POST',
            data: form.serialize()
        }).done(function(data) {
            if (!self.claimResponse(requestId)) {
                return;
            }
            if (!data || !data.tariff) {
                self.sessionExpired();
                return;
            }
            self.addTariffOption(data.tariff.id, data.tariff.name);
            self.previousValue = String(data.tariff.id);
            self.select.val(self.previousValue);
            self.modal.modal('hide');
            base.flashText(data.message || self.text('created'), 'success');
        }).fail(function(xhr) {
            if (!self.claimResponse(requestId)) {
                return;
            }
            if (xhr.status === 400 && xhr.responseText) {
                if (!self.renderModal(xhr.responseText)) {
                    self.sessionExpired();
                }
                return;
            }
            base.flashText(self.text('save-error'), 'danger');
        });
    },

    /**
     * Decide whether a settled request may still touch the meter form.
     *
     * @returns {boolean} false when the modal was dismissed while this request
     *     was in flight, in which case it must not touch the meter form.
     */
    claimResponse: function(requestId) {
        if (this.pendingRequestId !== requestId) {
            return false;
        }
        this.pendingRequestId = null;
        this.setSaving(false);
        return true;
    },

    abortPendingRequest: function() {
        this.pendingRequestId = null;
        this.setSaving(false);
    },

    setSaving: function(saving) {
        this.saveButton.prop('disabled', saving);
        this.saveButton.text(saving ? this.text('saving') : this.text('save'));
    },

    sessionExpired: function() {
        this.modal.modal('hide');
        this.restoreTariffSelection();
        base.flashText(this.text('session-expired'), 'danger');
    },

    addTariffOption: function(value, label) {
        var option = this.select.find('option[value="' + value + '"]');
        if (!option.length) {
            option = $('<option></option>').val(value).text(label);
            var addNewOption = this.select.find('option[value="' + this.addNewValue + '"]');
            if (addNewOption.length) {
                addNewOption.before(option);
            } else {
                this.select.append(option);
            }
        } else {
            option.text(label);
        }
    },

    restoreTariffSelection: function() {
        if (this.select.val() !== this.addNewValue) {
            return;
        }
        this.select.val(this.previousValue);
    },

    currentTariffValue: function() {
        var value = this.select.val();
        return value === this.addNewValue ? BLANK_VALUE : value;
    }
};
