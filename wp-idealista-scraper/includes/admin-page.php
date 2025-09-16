<?php

if (!defined('ABSPATH')) {
    exit; // Exit if accessed directly
}

function is_render_dashboard_page() {
    ?>
    <div class="wrap">
        <h1>Dashboard</h1>
        <p>Welcome to the Idealista Scraper dashboard.</p>
        <p>Statistics about the scraped data will be displayed here once you have run a scraping session.</p>

        <div id="dashboard-stats-container">
            <!-- Stats will be loaded here via AJAX -->
            <p>Loading statistics...</p>
        </div>
    </div>
    <?php
}

function is_render_zone_management_page() {
    ?>
    <div class="wrap">
        <h1>Zone Management</h1>
        <p>Select the zones you want to scrape.</p>
        <?php wp_nonce_field('idealista_scraper_nonce', 'is_nonce'); ?>
        <div id="is-zone-tree-container"></div>
        <p class="submit">
            <button id="is-save-zones-button" class="button button-primary">Save Selected Zones</button>
        </p>
    </div>
    <?php
}

function is_render_market_data_page() {
    ?>
    <div class="wrap">
        <h1>Market Data Management</h1>
        <p>Select an administrative level to view and edit its market data.</p>

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
        <h1>Settings</h1>
        <form method="post" action="options.php">
            <?php
                settings_fields('idealista-scraper-settings-group');
                do_settings_sections('idealista-scraper-settings-group');
            ?>
            <table class="form-table">
                <tr valign="top">
                    <th scope="row">API URL</th>
                    <td><input type="text" name="idealista_scraper_api_url" value="<?php echo esc_attr(get_option('idealista_scraper_api_url')); ?>" class="regular-text" /></td>
                </tr>
            </table>
            <?php submit_button(); ?>
        </form>
    </div>
    <?php
}
