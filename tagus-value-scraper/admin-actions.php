<?php

if (!defined('ABSPATH')) {
    exit; // Exit if accessed directly
}

/**
 * Handles form submissions from the Tagus Value Scraper admin page.
 * Hooked into 'admin_init'.
 */
function tagus_value_handle_admin_actions() {
    // Check if our form has been submitted and the nonce is valid.
    if (!isset($_POST['tagus_value_nonce_field']) || !wp_verify_nonce($_POST['tagus_value_nonce_field'], 'tagus_value_admin_actions')) {
        return;
    }

    // --- Action: Save all manual edits ---
    if (isset($_POST['tagus_value_save_data'])) {
        tagus_value_handle_save_action();
    }

    // --- Action: Scrape a single value ---
    if (isset($_POST['tagus_value_scrape_single'])) {
        tagus_value_handle_scrape_action();
    }
}

/**
 * Handles the logic for saving all market data.
 */
function tagus_value_handle_save_action() {
    if (!isset($_POST['market_data']) || !is_array($_POST['market_data'])) {
        return;
    }

    $market_data = tagus_value_load_market_data();
    $submitted_data = tagus_value_sanitize_market_data($_POST['market_data']);

    // array_replace_recursive is perfect for merging the sanitized edits.
    $updated_data = array_replace_recursive($market_data, $submitted_data);

    if (tagus_value_save_market_data($updated_data)) {
        add_action('admin_notices', function() {
            echo '<div class="notice notice-success is-dismissible"><p>Market data saved successfully.</p></div>';
        });
    } else {
        add_action('admin_notices', function() {
            echo '<div class="notice notice-error is-dismissible"><p>Failed to save market data.</p></div>';
        });
    }
}

/**
 * Handles the logic for scraping a single data point.
 */
function tagus_value_handle_scrape_action() {
    if (!isset($_POST['scrape_params']) || !is_array($_POST['scrape_params'])) {
        return;
    }

    $scrape_params = $_POST['scrape_params']; // No need to sanitize, these are slugs we generated.
    $scraped_price = tagus_value_scrape_single_location($scrape_params);

    if (!is_numeric($scraped_price)) {
        // Handle scraping error
        add_action('admin_notices', function() use ($scraped_price) {
            echo '<div class="notice notice-error is-dismissible"><p>Scrape failed: ' . esc_html($scraped_price) . '</p></div>';
        });
        return;
    }

    // If scrape was successful, load data, update the value, and save.
    $market_data = tagus_value_load_market_data();

    if (isset($scrape_params['key_path']) && is_array($scrape_params['key_path'])) {
        $key_path = $scrape_params['key_path'];
        $data_pointer = &$market_data;
        $valid_path = true;

        // Traverse the array using the key path to get to the right spot.
        foreach($key_path as $key) {
            if (!isset($data_pointer[$key])) {
                $valid_path = false;
                break;
            }
            $data_pointer = &$data_pointer[$key];
        }

        if ($valid_path) {
            $data_pointer['price'] = $scraped_price;
            tagus_value_save_market_data($market_data);
            add_action('admin_notices', function() use ($scraped_price) {
                echo '<div class="notice notice-success is-dismissible"><p>Scrape successful! New price: ' . esc_html($scraped_price) . '</p></div>';
            });
        }
    }
}

/**
 * Recursively sanitizes the market data array submitted via POST.
 *
 * @param array $data The array to sanitize.
 * @return array The sanitized array.
 */
function tagus_value_sanitize_market_data($data) {
    $sanitized_data = [];
    foreach ($data as $key => $value) {
        $sanitized_key = sanitize_key($key);
        if (is_array($value)) {
            $sanitized_data[$sanitized_key] = tagus_value_sanitize_market_data($value);
        } else {
            // We only expect 'price' and 'url' here. Price can be numeric, url needs sanitizing.
            // For simplicity, we'll treat all as text fields.
            $sanitized_data[$sanitized_key] = sanitize_text_field($value);
        }
    }
    return $sanitized_data;
}
