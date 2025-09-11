(function( $ ) {
    'use strict';

    $(function() {

        // Handle expand/collapse of distritos
        $('.distrito-title').on('click', function() {
            $(this).siblings('.concelhos-container').slideToggle();
        });

        // Handle expand/collapse of concelhos
        $('.concelho-title').on('click', function() {
            $(this).siblings('.freguesias-list').slideToggle();
        });

        // Handle distrito checkbox
        $('.distrito-checkbox').on('change', function() {
            var isChecked = $(this).is(':checked');
            var distritoCode = $(this).data('distrito');
            $('.freguesia-checkbox[data-distrito="' + distritoCode + '"]').prop('checked', isChecked);
            $('.concelho-checkbox[data-distrito="' + distritoCode + '"]').prop('checked', isChecked);
        });

        // Handle concelho checkbox
        $('.concelho-checkbox').on('change', function() {
            var isChecked = $(this).is(':checked');
            var distritoCode = $(this).data('distrito');
            var concelhoCode = $(this).data('concelho');
            $('.freguesia-checkbox[data-distrito="' + distritoCode + '"][data-concelho="' + concelhoCode + '"]').prop('checked', isChecked);
        });

        // Handle individual freguesia checkbox changes to update parent checkboxes
        $('.freguesia-checkbox').on('change', function() {
            var distritoCode = $(this).data('distrito');
            var concelhoCode = $(this).data('concelho');

            // Update concelho checkbox
            var allFreguesiasInConcelho = $('.freguesia-checkbox[data-distrito="' + distritoCode + '"][data-concelho="' + concelhoCode + '"]');
            var checkedFreguesiasInConcelho = allFreguesiasInConcelho.filter(':checked');
            var concelhoCheckbox = $('.concelho-checkbox[data-distrito="' + distritoCode + '"][data-concelho="' + concelhoCode + '"]');
            concelhoCheckbox.prop('checked', allFreguesiasInConcelho.length === checkedFreguesiasInConcelho.length);

            // Update distrito checkbox
            var allFreguesiasInDistrito = $('.freguesia-checkbox[data-distrito="' + distritoCode + '"]');
            var checkedFreguesiasInDistrito = allFreguesiasInDistrito.filter(':checked');
            var distritoCheckbox = $('.distrito-checkbox[data-distrito="' + distritoCode + '"]');
            distritoCheckbox.prop('checked', allFreguesiasInDistrito.length === checkedFreguesiasInDistrito.length);
        });

    });

})( jQuery );
