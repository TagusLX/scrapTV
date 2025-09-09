<?php
/**
 * Plugin Name:     Idealista Scraper
 * Plugin URI:      https://example.com/
 * Description:     A plugin to interact with the Idealista scraper backend.
 * Author:          Jules
 * Author URI:      https://example.com/
 * Text Domain:     idealista-scraper
 * Domain Path:     /languages
 * Version:         1.0.0
 *
 * @package         Idealista_Scraper
 */

// If this file is called directly, abort.
if ( ! defined( 'WPINC' ) ) {
    die;
}

define( 'IDEALISTA_SCRAPER_VERSION', '1.0.0' );
define( 'IDEALISTA_SCRAPER_PLUGIN_DIR', plugin_dir_path( __FILE__ ) );
define( 'IDEALISTA_SCRAPER_PLUGIN_URL', plugin_dir_url( __FILE__ ) );

// Include the main plugin class.
require_once IDEALISTA_SCRAPER_PLUGIN_DIR . 'includes/class-idealista-scraper.php';

/**
 * Begins execution of the plugin.
 *
 * Since everything within the plugin is registered via hooks,
 * kicking off the plugin from this point in the file does
 * not affect the page life cycle.
 *
 * @since    1.0.0
 */
function run_idealista_scraper() {

    $plugin = new Idealista_Scraper();
    $plugin->run();

}
run_idealista_scraper();
