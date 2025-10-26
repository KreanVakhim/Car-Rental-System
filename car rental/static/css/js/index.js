// static/js/index.js
$(document).ready(function () {
    // Initialize Datepicker
    $('.datepicker').datepicker({
        dateFormat: 'yy-mm-dd',
        minDate: 0, // Prevent past dates
        changeMonth: true,
        changeYear: true
    });

    // Search Form Submission
    $('.search-form').on('submit', function (e) {
        const $button = $(this).find('button[type="submit"]');
        const $spinner = $button.find('.spinner-border');
        $spinner.removeClass('d-none');
        $button.prop('disabled', true);
        setTimeout(() => {
            $spinner.addClass('d-none');
            $button.prop('disabled', false);
        }, 1000); // Simulate async submission
    });

    // Initialize Tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();
});