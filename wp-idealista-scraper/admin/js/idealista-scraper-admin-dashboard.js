(function( $ ) {
    'use strict';

    $(function() {
        const apiUrl = idealista_scraper_ajax.api_url;

        if (!apiUrl) {
            $('#dashboard-container').html('<div class="error"><p><strong>Error:</strong> API URL is not configured. Please set it in the Idealista Scraper settings.</p></div>');
            return;
        }

        // Fetch all data on page load
        fetchAllDashboardData();

        function fetchAllDashboardData() {
            fetchSummaryData();
            fetchCoverageStats();
            fetchRecentSessions();
            fetchRegionalStats();
        }

        function fetchSummaryData() {
            // Use stats/regions to calculate summary
            $.get(apiUrl + '/api/stats/regions')
                .done(function(data) {
                    let totalProperties = 0;
                    let totalSalePriceSqm = 0;
                    let saleCount = 0;
                    let totalRentPriceSqm = 0;
                    let rentCount = 0;

                    if(Array.isArray(data)) {
                        data.forEach(function(region) {
                            totalProperties += region.total_properties;
                            if (region.avg_sale_price_per_sqm) {
                                totalSalePriceSqm += region.avg_sale_price_per_sqm;
                                saleCount++;
                            }
                            if (region.avg_rent_price_per_sqm) {
                                totalRentPriceSqm += region.avg_rent_price_per_sqm;
                                rentCount++;
                            }
                        });
                    }

                    const avgSale = saleCount > 0 ? (totalSalePriceSqm / saleCount).toFixed(2) + ' €' : 'N/A';
                    const avgRent = rentCount > 0 ? (totalRentPriceSqm / rentCount).toFixed(2) + ' €' : 'N/A';

                    $('#summary-total-properties').text(totalProperties);
                    $('#summary-avg-sale').text(avgSale);
                    $('#summary-avg-rent').text(avgRent);
                })
                .fail(function() {
                    $('#dashboard-summary').find('p').text('Error');
                });

            // Get last session status
             $.get(apiUrl + '/api/scraping-sessions?limit=1')
                .done(function(data) {
                    if (data && data.length > 0) {
                        const lastSession = data[0];
                        $('#summary-last-session').html(`<span class="status-${lastSession.status}">${lastSession.status}</span>`);
                    } else {
                        $('#summary-last-session').text('No sessions found');
                    }
                })
                .fail(function() {
                    $('#summary-last-session').text('Error');
                });
        }

        function fetchCoverageStats() {
            const $container = $('#coverage-stats-container');
            $container.html('Loading coverage data...');

            $.get(apiUrl + '/api/coverage/stats')
                .done(function(data) {
                    if (!data) {
                        $container.html('Could not load coverage data.');
                        return;
                    }
                    let html = '<div class="coverage-grid">';

                    // Overall
                    html += createProgressBar('Overall Parishes', data.covered_parishes, data.total_parishes, data.overall_coverage_percentage);
                    html += createProgressBar('Municipalities', data.covered_municipalities, data.total_municipalities, (data.covered_municipalities / data.total_municipalities * 100));
                    html += createProgressBar('Districts', data.covered_districts, data.total_districts, (data.covered_districts / data.total_districts * 100));

                    html += '</div>';
                    $container.html(html);
                })
                .fail(function() {
                    $container.html('Error loading coverage data.');
                });
        }

        function createProgressBar(title, current, total, percentage) {
            let perc = percentage ? percentage.toFixed(1) : 0;
             return `
                <div class="coverage-item">
                    <div class="label">
                        <span>${title}</span>
                        <span>${current} / ${total}</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-bar-inner" style="width: ${perc}%;">${perc}%</div>
                    </div>
                </div>
            `;
        }

        function fetchRecentSessions() {
            const $container = $('#sessions-container');
            $container.html('Loading recent sessions...');

            $.get(apiUrl + '/api/scraping-sessions')
                .done(function(data) {
                     if (!data || data.length === 0) {
                        $container.html('No scraping sessions found.');
                        return;
                    }

                    let html = '<table><thead><tr><th>Session ID</th><th>Status</th><th>Started</th><th>Completed</th><th>Properties</th></tr></thead><tbody>';
                    data.slice(0, 5).forEach(function(session) { // Show latest 5
                        html += `
                            <tr>
                                <td>${session.id}</td>
                                <td><span class="session-${session.status}">${session.status}</span></td>
                                <td>${new Date(session.started_at).toLocaleString()}</td>
                                <td>${session.completed_at ? new Date(session.completed_at).toLocaleString() : 'N/A'}</td>
                                <td>${session.total_properties}</td>
                            </tr>
                        `;
                    });
                    html += '</tbody></table>';
                    $container.html(html);
                })
                .fail(function() {
                    $container.html('Error loading session data.');
                });
        }

        function fetchRegionalStats() {
            const $container = $('#regional-stats-container');
            $container.html('Loading regional data...');

            $.get(apiUrl + '/api/stats/detailed')
                .done(function(data) {
                    if (!data || data.length === 0) {
                        $container.html('No regional data found.');
                        return;
                    }

                    let html = '<table><thead><tr><th>Region</th><th>Location</th><th>Type</th><th>Operation</th><th>Avg. Price/m²</th><th>Count</th></tr></thead><tbody>';
                    data.forEach(function(region) {
                        if(region.detailed_stats) {
                            region.detailed_stats.forEach(function(stat) {
                                html += `
                                    <tr>
                                        <td>${region.display_info.distrito}</td>
                                        <td>${region.display_info.concelho} > ${region.display_info.freguesia}</td>
                                        <td>${stat.property_type}</td>
                                        <td>${stat.operation_type}</td>
                                        <td>${stat.avg_price_per_sqm ? stat.avg_price_per_sqm.toFixed(2) + ' €' : 'N/A'}</td>
                                        <td>${stat.count}</td>
                                    </tr>
                                `;
                            });
                        }
                    });
                    html += '</tbody></table>';
                    $container.html(html);
                })
                .fail(function() {
                    $container.html('Error loading regional data.');
                });
        }

    });
})( jQuery );
