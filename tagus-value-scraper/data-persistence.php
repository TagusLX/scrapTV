<?php

if (!defined('ABSPATH')) {
    exit; // Exit if accessed directly
}

/**
 * Defines the path for the market data JSON file.
 *
 * @return string The full path to the market-data.json file.
 */
function tagus_value_get_data_file_path() {
    // Store the JSON file in the uploads directory to ensure it's writable
    // and persists between plugin updates.
    $upload_dir = wp_upload_dir();
    $data_dir = $upload_dir['basedir'] . '/tagus-value-scraper/';

    // Create the directory if it doesn't exist.
    if (!file_exists($data_dir)) {
        wp_mkdir_p($data_dir);
    }

    return $data_dir . 'market-data.json';
}

/**
 * Loads the market data from the JSON file.
 * If the file doesn't exist, it initializes it with the skeleton structure.
 *
 * @return array The market data.
 */
function tagus_value_load_market_data() {
    $file_path = tagus_value_get_data_file_path();

    if (!file_exists($file_path)) {
        // File doesn't exist, so we create it from the skeleton.
        $initial_data = tagus_value_get_location_skeleton();
        tagus_value_save_market_data($initial_data);
        return $initial_data;
    }

    $json_content = file_get_contents($file_path);
    $data = json_decode($json_content, true);

    if (json_last_error() !== JSON_ERROR_NONE) {
        // Handle JSON decoding error, maybe return an empty array or the skeleton
        return tagus_value_get_location_skeleton();
    }

    return $data;
}

/**
 * Saves the market data array to the JSON file.
 *
 * @param array $market_data The data to save.
 * @return bool|int False on failure, number of bytes written on success.
 */
function tagus_value_save_market_data($market_data) {
    $file_path = tagus_value_get_data_file_path();

    // Encode the data with pretty printing for readability.
    $json_data = json_encode($market_data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);

    if (json_last_error() !== JSON_ERROR_NONE) {
        // Handle JSON encoding error
        error_log('Tagus Value Scraper: JSON encoding error: ' . json_last_error_msg());
        return false;
    }

    return file_put_contents($file_path, $json_data);
}
