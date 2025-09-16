<?php
/**
 * Plugin Name: Idealista Scraper
 * Description: A plugin to scrape data from Idealista and display it.
 * Version: 1.0
 * Author: Jules
 */

if (!defined('ABSPATH')) {
    exit; // Exit if accessed directly
}

define('IS_PLUGIN_PATH', plugin_dir_path(__FILE__));
define('IS_PLUGIN_URL', plugin_dir_url(__FILE__));

// Include necessary files
require_once IS_PLUGIN_PATH . 'includes/admin-page.php';
require_once IS_PLUGIN_PATH . 'includes/ajax-handlers.php';

// Add the admin menu
add_action('admin_menu', 'is_add_admin_menu');
add_action('admin_init', 'is_register_settings');
add_action('admin_enqueue_scripts', 'is_enqueue_scripts');

function is_register_settings() {
    register_setting(
        'idealista-scraper-settings-group', // Option group
        'is_scraper_api_key', // Option name
        ['sanitize_callback' => 'sanitize_text_field'] // Sanitize
    );
}

// Define the backend server URL
define('IS_BACKEND_URL', 'http://localhost:8000');

function is_enqueue_scripts($hook) {
    // Only load on our plugin's pages
    if (strpos($hook, 'idealista-scraper') === false) {
        return;
    }

    // Enqueue the existing market-data.js on its page
    if ($hook === 'idealista-scraper_page_idealista-scraper-market-data') {
        wp_enqueue_script(
            'is-market-data',
            IS_PLUGIN_URL . 'assets/js/market-data.js',
            ['jquery'],
            '1.0',
            true
        );
    }

    // Enqueue the new admin scraper script on the market data page
    if ($hook === 'idealista-scraper_page_idealista-scraper-market-data') {
        wp_enqueue_script(
            'is-admin-scraper',
            IS_PLUGIN_URL . 'assets/js/admin-scraper.js',
            ['jquery'],
            '1.0',
            true
        );

        // Pass data to the scraper script
        wp_localize_script(
            'is-admin-scraper',
            'is_scraper_data',
            [
                'api_key' => get_option('is_scraper_api_key'),
                'backend_url' => IS_BACKEND_URL
            ]
        );
    }
}

function is_add_admin_menu() {
    add_menu_page(
        'Idealista Scraper',
        'Idealista Scraper',
        'manage_options',
        'idealista-scraper',
        'is_render_dashboard_page',
        'dashicons-admin-site-alt3',
        20
    );

    add_submenu_page(
        'idealista-scraper',
        'Dashboard',
        'Dashboard',
        'manage_options',
        'idealista-scraper',
        'is_render_dashboard_page'
    );

    add_submenu_page(
        'idealista-scraper',
        'Zone Management',
        'Zone Management',
        'manage_options',
        'idealista-scraper-zone-management',
        'is_render_zone_management_page'
    );

    add_submenu_page(
        'idealista-scraper',
        'Market Data',
        'Market Data',
        'manage_options',
        'idealista-scraper-market-data',
        'is_render_market_data_page'
    );

    add_submenu_page(
        'idealista-scraper',
        'Settings',
        'Settings',
        'manage_options',
        'idealista-scraper-settings',
        'is_render_settings_page'
    );
}
