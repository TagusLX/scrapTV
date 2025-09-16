jQuery(document).ready(function($) {
    let scrapingInterval;

    $('#start-market-report-scraping').on('click', function() {
        const apiKey = is_scraper_data.api_key;
        const backendUrl = is_scraper_data.backend_url;

        if (!apiKey) {
            alert('Please set your ScraperAPI Key in the Idealista Scraper settings page first.');
            return;
        }

        $(this).prop('disabled', true).text('Scraping in Progress...');
        $('#scraping-status-display').html('Starting scraping process...');

        // Start the scraping task
        $.ajax({
            url: backendUrl + '/api/scrape/market-reports/start',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ api_key: apiKey }),
            success: function(response) {
                $('#scraping-status-display').html('Scraping process started. Waiting for first status update...');
                // Start polling for status
                scrapingInterval = setInterval(checkScrapingStatus, 5000);
            },
            error: function(xhr) {
                const error = xhr.responseJSON ? xhr.responseJSON.detail : 'An unknown error occurred.';
                $('#scraping-status-display').html('<strong>Error starting process:</strong> ' + error);
                $('#start-market-report-scraping').prop('disabled', false).text('Start Scraping');
            }
        });
    });

    function checkScrapingStatus() {
        const backendUrl = is_scraper_data.backend_url;

        $.ajax({
            url: backendUrl + '/api/scrape/market-reports/status',
            method: 'GET',
            success: function(response) {
                let statusHtml = '<strong>Status:</strong> ' + response.status + '<br>';
                statusHtml += '<strong>Progress:</strong> ' + response.progress + '<br>';
                statusHtml += '<strong>Last Updated:</strong> ' + new Date(response.last_updated).toLocaleString();

                if (response.error_message) {
                    statusHtml += '<br><strong>Error:</strong> <span style="color: red;">' + response.error_message + '</span>';
                }

                $('#scraping-status-display').html(statusHtml);

                if (response.status === 'completed' || response.status === 'failed') {
                    clearInterval(scrapingInterval);
                    $('#start-market-report-scraping').prop('disabled', false).text('Start Scraping');
                }
            },
            error: function() {
                $('#scraping-status-display').append('<br><span style="color: red;">Could not retrieve status.</span>');
            }
        });
    }
});
