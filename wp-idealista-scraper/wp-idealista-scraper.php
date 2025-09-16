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
require_once IS_PLUGIN_PATH . 'includes/db-manager.php';

// Activation hook
register_activation_hook(__FILE__, ['Idealista_Scraper_DB_Manager', 'create_table']);

// Add the admin menu
add_action('admin_menu', 'is_add_admin_menu');
add_action('admin_init', 'is_register_settings');
add_action('admin_enqueue_scripts', 'is_enqueue_scripts');

function is_register_settings() {
    register_setting('idealista-scraper-settings-group', 'idealista_scraper_api_url');
}

function is_enqueue_scripts($hook) {
    if ($hook === 'idealista-scraper_page_idealista-scraper-market-data') {
        wp_enqueue_script(
            'is-market-data',
            IS_PLUGIN_URL . 'assets/js/market-data.js',
            [],
            '1.0',
            true
        );
    } elseif ($hook === 'idealista-scraper_page_idealista-scraper-zone-management') {
        wp_enqueue_script(
            'is-zone-management',
            IS_PLUGIN_URL . 'assets/js/zone-management.js',
            [],
            '1.0',
            true
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

add_action('rest_api_init', 'is_register_rest_routes');

function is_register_rest_routes() {
    register_rest_route('idealista-scraper/v1', '/structure', [
        'methods' => 'GET',
        'callback' => 'is_get_structure_data',
        'permission_callback' => '__return_true'
    ]);

    register_rest_route('idealista-scraper/v1', '/structure', [
        'methods' => 'POST',
        'callback' => 'is_save_structure_data',
        'permission_callback' => function () {
            return current_user_can('manage_options');
        }
    ]);
}

function is_get_structure_data() {
    $file_path = IS_PLUGIN_PATH . 'includes/data/portugal_administrative_structure.json';
    if (file_exists($file_path)) {
        $content = file_get_contents($file_path);
        $data = json_decode($content, true);
        if (json_last_error() === JSON_ERROR_NONE) {
            return new WP_REST_Response($data, 200);
        } else {
            return new WP_REST_Response(['error' => 'Failed to parse JSON file.'], 500);
        }
    } else {
        return new WP_REST_Response(['error' => 'Data file not found.'], 404);
    }
}

function is_save_structure_data($request) {
    $data = $request->get_json_params();
    if (empty($data)) {
        return new WP_REST_Response(['error' => 'No data provided.'], 400);
    }

    $file_path = IS_PLUGIN_PATH . 'includes/data/portugal_administrative_structure.json';
    $json_data = json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);

    if (file_put_contents($file_path, $json_data)) {
        return new WP_REST_Response(['success' => 'Data saved successfully.'], 200);
    } else {
        return new WP_REST_Response(['error' => 'Failed to save data to file.'], 500);
    }
}
