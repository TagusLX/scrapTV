<?php

if (!defined('ABSPATH')) exit;

/**
 * Generates the final market-data.php file from the JSON data store.
 */
function tagus_value_generate_php_data_file() {
    $json_path = plugin_dir_path(__FILE__) . 'market-data.json';
    if (!file_exists($json_path)) {
        // Create an empty file if it doesn't exist, to avoid errors
        $initial_data = tagus_value_get_location_skeleton();
        file_put_contents($json_path, json_encode($initial_data, JSON_PRETTY_PRINT));
    }

    $data = json_decode(file_get_contents($json_path), true);
    if (json_last_error() !== JSON_ERROR_NONE) {
        error_log('Tagus Value Scraper: Error decoding market-data.json: ' . json_last_error_msg());
        return;
    }

    $array_export = var_export($data, true);
    $timestamp = wp_date('d-m-Y (H:i)');

    $file_content = <<<EOD
<?php
/**
 * Market prices data for Portugal
 * Last update {$timestamp}
 * @link       https://tagusvalue.com
 * @since      2.0.0
 *
 * @package    Tagus_Value
 * @subpackage Tagus_Value/data
 */

if (!defined('ABSPATH')) exit;

if (!function_exists('tagus_value_get_market_data')) {
    function tagus_value_get_market_data() {
        return {$array_export};
    }
}
EOD;

    $php_file_path = plugin_dir_path(__FILE__) . 'market-data.php';
    file_put_contents($php_file_path, $file_content);
}
?>
