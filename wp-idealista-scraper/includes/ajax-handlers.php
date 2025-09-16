<?php

if (!defined('ABSPATH')) {
    exit; // Exit if accessed directly
}

add_action('wp_ajax_save_selected_zones', 'is_save_selected_zones_callback');

function is_save_selected_zones_callback() {
    check_ajax_referer('idealista_scraper_nonce', 'nonce');

    $selected_zones = isset($_POST['selected_zones']) ? json_decode(stripslashes($_POST['selected_zones']), true) : [];

    if (empty($selected_zones)) {
        wp_send_json_error('No zones selected.');
    }

    update_option('idealista_scraper_selected_zones', $selected_zones);

    wp_send_json_success('Selected zones saved successfully.');
}
