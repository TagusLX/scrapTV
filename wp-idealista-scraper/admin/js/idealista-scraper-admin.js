(function( $ ) {
    'use strict';

    $(function() {
        // Start scraping button
        $('#start-scraping').on('click', function() {
            var $button = $(this);
            $button.prop('disabled', true).text('Starting...');

            $.post(idealista_scraper_ajax.ajax_url, {
                action: 'start_scraping',
                security: idealista_scraper_ajax.start_scraping_nonce
            }, function(response) {
                if (response.success) {
                    alert('Scraping session started successfully. Session ID: ' + response.data.session_id);
                    updateScrapingStatus();
                } else {
                    alert('Error: ' + response.data);
                }
                $button.prop('disabled', false).text('Start New Scraping Session');
            });
        });

        // Submit CAPTCHA button
        $('#submit-captcha').on('click', function() {
            var $button = $(this);
            var solution = $('#captcha-solution').val();
            var sessionId = $('#captcha-session-id').val();

            if (!solution) {
                alert('Please enter the CAPTCHA solution.');
                return;
            }

            $button.prop('disabled', true).text('Submitting...');

            $.post(idealista_scraper_ajax.ajax_url, {
                action: 'solve_captcha',
                security: idealista_scraper_ajax.solve_captcha_nonce,
                session_id: sessionId,
                solution: solution
            }, function(response) {
                if (response.success && response.data.success) {
                    alert('CAPTCHA solved successfully. Scraping will resume.');
                    $('#captcha-solver').hide();
                    updateScrapingStatus();
                } else {
                    alert('Error: ' + (response.data.message || response.data));
                }
                $button.prop('disabled', false).text('Submit Solution');
            });
        });

        // Function to update scraping status
        function updateScrapingStatus() {
            var $statusContainer = $('#scraping-status');
            $statusContainer.html('Loading status...');

            $.get(idealista_scraper_ajax.ajax_url, {
                action: 'get_scraping_status'
            }, function(response) {
                if (response.success) {
                    var sessions = response.data;
                    var html = '<ul>';
                    var showCaptcha = false;

                    sessions.forEach(function(session) {
                        html += '<li>';
                        html += '<strong>Session ID:</strong> ' + session.id + ' - ';
                        html += '<strong class="session-' + session.status + '">Status:</strong> ' + session.status;
                        if (session.status === 'waiting_captcha') {
                            showCaptcha = true;
                            $('#captcha-session-id').val(session.id);
                            $('#captcha-image').attr('src', idealista_scraper_ajax.api_url + '/api/captcha/' + session.id);
                        }
                        html += '</li>';
                    });

                    html += '</ul>';
                    $statusContainer.html(html);

                    if (showCaptcha) {
                        $('#captcha-solver').show();
                    } else {
                        $('#captcha-solver').hide();
                    }

                    // Also update the scraped data
                    updateScrapedData();

                } else {
                    $statusContainer.html('Error loading status.');
                }
            });
        }

        // Function to update scraped data
        function updateScrapedData() {
            var $dataContainer = $('#scraped-data-container');
            $dataContainer.html('Loading data...');

             $.get(idealista_scraper_ajax.ajax_url, {
                action: 'get_scraped_data'
            }, function(response) {
                 if (response.success) {
                    var properties = response.data;
                    var html = '<table class="scraped-data-table"><thead><tr><th>Region</th><th>Location</th><th>Type</th><th>Operation</th><th>Price/sqm</th><th>URL</th></tr></thead><tbody>';

                    properties.forEach(function(prop) {
                        html += '<tr>';
                        html += '<td>' + prop.region + '</td>';
                        html += '<td>' + prop.location + '</td>';
                        html += '<td>' + prop.property_type + '</td>';
                        html += '<td>' + prop.operation_type + '</td>';
                        html += '<td>' + (prop.price_per_sqm ? prop.price_per_sqm.toFixed(2) + ' €' : 'N/A') + '</td>';
                        html += '<td><a href="' + prop.url + '" target="_blank">Link</a></td>';
                        html += '</tr>';
                    });

                    html += '</tbody></table>';
                    $dataContainer.html(html);
                } else {
                    $dataContainer.html('Error loading data.');
                }
            });
        }


        // Initial status update
        updateScrapingStatus();

        // Periodically update status
        setInterval(updateScrapingStatus, 15000); // every 15 seconds
    });

})( jQuery );
