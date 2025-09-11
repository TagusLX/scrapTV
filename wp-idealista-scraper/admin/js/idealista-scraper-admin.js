(function( $ ) {
    'use strict';

    $(function() {
        // Start scraping button
        $('#start-scraping').on('click', function() {
            var $button = $(this);
            $button.prop('disabled', true).text('Fetching selected zones...');

            // First, get the list of selected zones from WordPress
            $.get(idealista_scraper_ajax.ajax_url, { action: 'get_selected_zones' })
                .done(function(response) {
                    if (!response.success || !Array.isArray(response.data) || response.data.length === 0) {
                        alert('No zones selected. Please select zones to scrape from the "Zone Management" page.');
                        $button.prop('disabled', false).text('Start New Scraping Session');
                        return;
                    }

                    var selectedZones = response.data;
                    $button.text('Starting scraping for ' + selectedZones.length + ' zones...');

                    // Now, send the list of zones to the backend to start scraping
                    $.ajax({
                        type: 'POST',
                        url: idealista_scraper_ajax.api_url + '/api/scrape/start',
                        data: JSON.stringify({ zones: selectedZones }), // Send zones in the body
                        contentType: 'application/json',
                        dataType: 'json',
                        success: function(backendResponse) {
                             alert('Scraping session started successfully. Session ID: ' + backendResponse.session_id);
                             updateScrapingStatus();
                        },
                        error: function(xhr, status, error) {
                            alert('Error starting scraping session: ' + (xhr.responseJSON ? xhr.responseJSON.detail : error));
                        },
                        complete: function() {
                            $button.prop('disabled', false).text('Start New Scraping Session');
                        }
                    });
                })
                .fail(function() {
                    alert('Error fetching selected zones from WordPress.');
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

        // Handle the main settings form submission to update the backend config
        $('form[action="options.php"]').on('submit', function(e) {
            e.preventDefault(); // Prevent the form from submitting immediately

            var $form = $(this);
            var $submitButton = $form.find('input[type="submit"]');

            $submitButton.prop('disabled', true).val('Updating backend...');

            var intensity = $('#idealista_scraper_scraping_intensity').val();
            // Fallback to defaults if elements don't exist, to prevent errors on other pages
            var proxiesElem = $('#idealista_scraper_proxy_list');
            var userAgentsElem = $('#idealista_scraper_user_agent_list');

            var proxies = proxiesElem.length ? proxiesElem.val().split('\n').map(s => s.trim()).filter(Boolean) : [];
            var userAgents = userAgentsElem.length ? userAgentsElem.val().split('\n').map(s => s.trim()).filter(Boolean) : [];

            var configData = {
                intensity: intensity,
                proxies: proxies,
                user_agents: userAgents
            };

            $.ajax({
                type: 'POST',
                url: idealista_scraper_ajax.api_url + '/api/config',
                data: JSON.stringify(configData),
                contentType: 'application/json',
                dataType: 'json',
                success: function(response) {
                    console.log('Backend configuration updated.', response);
                    $submitButton.val('Saving to WordPress...');
                    // Now that backend is updated, submit the form to save WP settings
                    $form.off('submit').submit();
                },
                error: function(xhr, status, error) {
                    console.error('Failed to update backend configuration.', error);
                    alert('CRITICAL ERROR: Could not update the scraper configuration. Please check the API URL and ensure the backend is running. WordPress settings were NOT saved.');
                    $submitButton.prop('disabled', false).val('Save Changes'); // Re-enable on error
                }
            });
        });
    });

})( jQuery );
