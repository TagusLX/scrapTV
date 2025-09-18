<?php

if (!defined('ABSPATH')) exit;

// #####################################################################
// # ACTION HANDLING AND SCRAPING LOGIC
// #####################################################################

add_action('admin_init', 'tagus_value_handle_admin_actions');
function tagus_value_handle_admin_actions() {
    if (!isset($_POST['tagus_value_action']) || $_POST['tagus_value_action'] !== 'scrape_or_save' || !isset($_POST['_wpnonce'])) {
        return;
    }
    check_admin_referer('tagus_value_action_nonce');

    $market_data_path = plugin_dir_path(__FILE__) . 'market-data.json';
    $market_data = file_exists($market_data_path) ? json_decode(file_get_contents($market_data_path), true) : [];
    $market_data = is_array($market_data) ? $market_data : [];

    if (isset($_POST['scrape_path'])) {
        $scrape_path = [];
        $temp = $_POST['scrape_path'];
        while (is_array($temp)) {
            $key = key($temp);
            $scrape_path[] = $key;
            $temp = $temp[$key];
        }

        $scraped_values = tagus_value_scrape_entity($scrape_path);
        tagus_value_update_data_at_path($market_data, $scrape_path, $scraped_values);
        add_action('admin_notices', function() { echo '<div class="notice notice-success is-dismissible"><p>Scraping terminé !</p></div>'; });

    } else { // General save
        $submitted_prices = isset($_POST['prices']) ? $_POST['prices'] : [];
        $sanitized_prices = tagus_value_sanitize_prices_array($submitted_prices);
        // Use the skeleton to ensure no data is lost if the form is partial
        $skeleton = tagus_value_get_location_skeleton();
        $merged_data = array_replace_recursive($skeleton, $market_data, $sanitized_prices);
        $market_data = $merged_data;

        add_action('admin_notices', function() { echo '<div class="notice notice-success is-dismissible"><p>Données enregistrées !</p></div>'; });
    }

    file_put_contents($market_data_path, json_encode($market_data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));
    tagus_value_generate_php_data_file();
}

function tagus_value_scrape_entity($path) {
    $slugs = [];
    $slugs['distrito'] = $path[0] ?? null;
    $slugs['concelho'] = $path[1] ?? null;
    if (isset($path[2]) && $path[2] === 'freguesias') {
        $slugs['freguesia'] = $path[3] ?? null;
        if (isset($path[4]) && $path[4] === 'types') {
            $slugs['type'] = $path[5] ?? null;
            $slugs['bedrooms'] = $path[6] ?? null;
        }
    }
    $slugs = array_filter($slugs);

    $url_sale = tagus_value_get_idealista_url('comprar-casas', $slugs);
    $url_rent = tagus_value_get_idealista_url('arrendar-casas', $slugs);

    return [
        'average'      => tagus_value_scrape_url($url_sale)['price'],
        'average_rent' => tagus_value_scrape_url($url_rent)['price'],
        'url_sale'     => $url_sale,
        'url_rent'     => $url_rent
    ];
}

function tagus_value_update_data_at_path(&$data, $path, $values_to_set) {
    $temp = &$data;
    foreach ($path as $key) {
        if (!isset($temp[$key])) $temp[$key] = [];
        $temp = &$temp[$key];
    }
    $temp = array_merge($temp, $values_to_set);
}

function tagus_value_get_data_at_path($data, $path) {
    $temp = $data;
    foreach ($path as $key) {
        if (!isset($temp[$key])) return null;
        $temp = $temp[$key];
    }
    return $temp;
}

function tagus_value_sanitize_prices_array($array) {
    foreach ($array as $key => &$value) {
        if (is_array($value)) {
            $value = tagus_value_sanitize_prices_array($value);
        } else {
            if ($value === '' || $value === null) {
                $value = null;
            } else {
                $sanitized_value = preg_replace('/[^0-9,.]/', '', $value);
                $sanitized_value = str_replace(',', '.', $sanitized_value);
                $value = is_numeric($sanitized_value) ? floatval($sanitized_value) : null;
            }
        }
    }
    return $array;
}

function tagus_value_scrape_url($url) {
    if (empty($url)) return ['price' => null];

    $response = wp_remote_get($url, ['timeout' => 30, 'user-agent' => 'Mozilla/5.0']);
    if (is_wp_error($response)) return ['price' => false];

    $body = wp_remote_retrieve_body($response);
    if (empty($body)) return ['price' => false];

    $dom = new DOMDocument();
    @$dom->loadHTML('<?xml encoding="UTF-8">' . $body);
    $xpath = new DOMXPath($dom);

    $selectors = ['//p[@class="items-average-price"]', '//*[contains(text(), "eur/m²")]'];
    foreach ($selectors as $selector) {
        $nodes = $xpath->query($selector);
        if ($nodes->length > 0) {
            if (preg_match('/([\d,.]+)/', $nodes->item(0)->textContent, $matches)) {
                $price_str = str_replace('.', '', $matches[1]);
                $price_str = str_replace(',', '.', $price_str);
                return ['price' => floatval($price_str)];
            }
        }
    }
    return ['price' => false];
}
?>
