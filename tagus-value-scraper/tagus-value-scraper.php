<?php
/**
 * Plugin Name:       Tagus Value Scraper
 * Description:       A plugin to scrape real estate data from Idealista.pt and display it in the admin panel.
 * Version:           2.0.0
 * Author:            Jules
 * License:           GPL-2.0-or-later
 * License URI:       https://www.gnu.org/licenses/gpl-2.0.html
 * Text Domain:       tagus-value-scraper
 */

if (!defined('ABSPATH')) {
    exit; // Exit if accessed directly
}

// Define plugin path for easier includes
define('TAGUS_VALUE_PLUGIN_PATH', plugin_dir_path(__FILE__));

// 1. Include all the necessary files in the correct order
require_once TAGUS_VALUE_PLUGIN_PATH . 'includes.php';
require_once TAGUS_VALUE_PLUGIN_PATH . 'data-structure.php';
require_once TAGUS_VALUE_PLUGIN_PATH . 'data-persistence.php';
require_once TAGUS_VALUE_PLUGIN_PATH . 'admin-actions.php';
require_once TAGUS_VALUE_PLUGIN_PATH . 'admin-ui.php';

/**
 * Adds the admin menu page for the plugin.
 *
 * @return void
 */
function tagus_value_add_admin_menu() {
    add_menu_page(
        'Tagus Value Scraper',          // Page title
        'Tagus Value',                  // Menu title
        'manage_options',               // Capability
        'tagus-value-scraper',          // Menu slug
        'tagus_value_admin_page',       // Callback function to render the page
        'dashicons-chart-area',         // Icon
        20                              // Position
    );
}
add_action('admin_menu', 'tagus_value_add_admin_menu');

/**
 * Hooks the admin action handler.
 *
 * @return void
 */
function tagus_value_init_handler() {
    tagus_value_handle_admin_actions();
}
add_action('admin_init', 'tagus_value_init_handler');