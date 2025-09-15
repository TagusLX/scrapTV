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
add_action('admin_enqueue_scripts', 'is_enqueue_scripts');

function is_enqueue_scripts($hook) {
    if ($hook !== 'idealista-scraper_page_idealista-scraper-market-data') {
        return;
    }
    wp_enqueue_script(
        'is-market-data',
        IS_PLUGIN_URL . 'assets/js/market-data.js',
        [],
        '1.0',
        true
    );
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
