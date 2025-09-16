<?php

if (!defined('ABSPATH')) {
    exit; // Exit if accessed directly
}

function is_render_dashboard_page() {
    ?>
    <div class="wrap">
        <h1>Dashboard</h1>
        <p>This is the dashboard page. Content to be added.</p>
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
        <p>This is the settings page. Content to be added.</p>
    </div>
    <?php
}
