function groundOverride() {
    $('.override-button').click(function(button) {
        var modalName = $(this).attr('data-confirm');
        $('#override-button').prop('disabled', true);
        $('#' + modalName + '_confirm').modal('show');
    });
}

exports.groundOverride = groundOverride;
