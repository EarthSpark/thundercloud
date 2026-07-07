// Copyright © 2013-2018 SparkMeter, Inc.
// All Rights Reserved.
//

/* global afterEach,beforeEach,describe,test,jest */

jest.mock('backend.js');

const backend = require('backend.js').backend;
const UserView = require('user/js/user-view.js');

describe('UserView', () => {
    let el = null;

    beforeEach(() => {
        el = $('<div class="modal fade" id="modal-api-reset-credentials" role="dialog">' +
            '<button class="btn btn-primary" href="#" id="reset-link" >Reset credentials</button>' +
            '</div>');
        $(document.body).append(el);
        $(document.body).attr('data-page-name', 'user-view');
    });

    afterEach(() => {
        if (el !== null) {
            el.remove();
            el = null;
        }
        $(document.body).removeAttr('data-page-name');
    });

    describe('Transaction permission checkbox', () => {
        test('toggles visibilty of vendor select', () => {
            backend.mockCall('resetCurrentCredentials', {});

            let userView = new UserView.UserView();
            userView._window = {
                location: {
                    reload: function() {
                    }
                }
            };

            $('button#reset-link').click();
        });
    });
});
