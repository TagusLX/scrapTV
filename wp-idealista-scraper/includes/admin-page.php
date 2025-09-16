<?php

if (!defined('ABSPATH')) {
    exit; // Exit if accessed directly
}

function is_render_dashboard_page() {
    ?>
    <div class="wrap">
        <h1>Dashboard</h1>
        <p>Welcome to the Idealista Scraper dashboard.</p>
    </div>
    <?php
}

function is_render_zone_management_page() {
    ?>
    <div class="wrap">
        <h1>Zone Management</h1>
        <p>This is the zone management page. Content to be added.</p>
    </div>
    <?php
}

function is_render_market_data_page() {
    ?>
    <div class="wrap">
        <h1>Market Data Management</h1>

        <div id="scraper-controls" style="padding: 15px; border: 1px solid #ccc; margin-bottom: 20px; background-color: #fff;">
            <h2>Run Price Report Scraper</h2>
            <p>Click the button below to start scraping the latest market prices from Idealista's public reports. This process can take a very long time.</p>
            <button id="start-market-report-scraping" class="button button-primary">Start Scraping</button>
            <div id="scraping-status-display" style="margin-top: 15px; padding: 10px; border: 1px solid #eee; background-color: #f9f9f9; max-height: 300px; overflow-y: auto;">
                Scraping status will appear here...
            </div>
        </div>

        <h2>View Market Data</h2>
        <p>Select an administrative level to view its market data.</p>

        <table class="form-table">
            <tbody>
                <tr>
                    <th scope="row"><label for="is-distrito-select">Distrito</label></th>
                    <td>
                        <select name="distrito" id="is-distrito-select">
                            <option value="">Select a Distrito</option>
                        </select>
                    </td>
                </tr>
                <tr>
                    <th scope="row"><label for="is-concelho-select">Concelho</label></th>
                    <td>
                        <select name="concelho" id="is-concelho-select" disabled>
                            <option value="">Select a Concelho</option>
                        </select>
                    </td>
                </tr>
                <tr>
                    <th scope="row"><label for="is-freguesia-select">Freguesia</label></th>
                    <td>
                        <select name="freguesia" id="is-freguesia-select" disabled>
                            <option value="">Select a Freguesia</option>
                        </select>
                    </td>
                </tr>
            </tbody>
        </table>

        <div id="is-market-data-form-container" style="display: none;">
            <!-- Form will be dynamically generated here -->
        </div>
    </div>
    <?php
}

function is_render_settings_page() {
    ?>
    <div class="wrap">
        <h1>Scraper Settings</h1>
        <form method="post" action="options.php">
            <?php
            settings_fields('idealista-scraper-settings-group');
            do_settings_sections('idealista-scraper-settings-group');
            ?>
            <table class="form-table">
                <tr valign="top">
                    <th scope="row">ScraperAPI Key</th>
                    <td><input type="text" name="is_scraper_api_key" value="<?php echo esc_attr(get_option('is_scraper_api_key')); ?>" style="width: 400px;"/></td>
                </tr>
            </table>
            <?php submit_button(); ?>
        </form>
    </div>
    <?php
}
