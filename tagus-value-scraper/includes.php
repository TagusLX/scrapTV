<?php

if (!defined('ABSPATH')) {
    exit; // Exit if accessed directly
}

/**
 * Generates a URL-friendly slug from a string.
 * Handles Portuguese special characters.
 *
 * @param string $string The input string.
 * @return string The sanitized slug.
 */
function tagus_value_generate_slug($string) {
    // Normalize the string to decomposed characters
    $string = normalizer_normalize($string, Normalizer::FORM_D);
    // Remove diacritical marks
    $string = preg_replace('/[\p{M}]/u', '', $string);

    $string = strtolower($string);

    // Specific replacements for characters not handled by normalization
    $string = str_replace(
        [' e ', ' de ', ' da ', ' do ', ' dos ', ' das '],
        '-',
        ' ' . $string . ' '
    );

    $string = preg_replace('/[^a-z0-9\-]+/', '-', $string);
    $string = trim($string, '-');
    return $string;
}


/**
 * Reads the location data from the TSV file and organizes it into a structured array.
 * Each level (distrito, concelho, freguesia) includes its name and slug.
 *
 * @return array The structured location data.
 */
function tagus_value_get_location_data() {
    $locations = [];
    $file_path = plugin_dir_path(__FILE__) . 'locations.tsv';

    if (!file_exists($file_path) || !is_readable($file_path)) {
        return $locations;
    }

    if (($handle = fopen($file_path, "r")) !== FALSE) {
        while (($data = fgetcsv($handle, 1000, "\t")) !== FALSE) {
            if (count($data) < 3) continue;

            list($distrito, $concelho, $freguesia) = array_map('trim', $data);

            $distrito_slug = tagus_value_generate_slug($distrito);
            $concelho_slug = tagus_value_generate_slug($concelho);
            $freguesia_slug = tagus_value_generate_slug($freguesia);

            // Create distrito if it doesn't exist
            if (!isset($locations[$distrito_slug])) {
                $locations[$distrito_slug] = [
                    'name' => $distrito,
                    'slug' => $distrito_slug,
                    'concelhos' => [],
                ];
            }

            // Create concelho if it doesn't exist
            if (!isset($locations[$distrito_slug]['concelhos'][$concelho_slug])) {
                $locations[$distrito_slug]['concelhos'][$concelho_slug] = [
                    'name' => $concelho,
                    'slug' => $concelho_slug,
                    'freguesias' => [],
                ];
            }

            // Add freguesia
            $locations[$distrito_slug]['concelhos'][$concelho_slug]['freguesias'][$freguesia_slug] = [
                'name' => $freguesia,
                'slug' => $freguesia_slug,
            ];
        }
        fclose($handle);
    }

    return $locations;
}

/**
 * Generates the correct Idealista URL based on the discovered structure.
 *
 * @param string $distrito_slug The slug for the district.
 * @param string $concelho_slug The slug for the concelho.
 * @param string|null $freguesia_slug The slug for the freguesia (optional).
 * @param string|null $property_type 'apartamentos' or 'moradias'.
 * @param string|null $bedrooms 't0', 't1', 't2', 't3', 't4-t5'.
 * @param string $operation 'venda' (sale) or 'arrendar' (rent).
 * @return string The generated Idealista URL.
 */
function tagus_value_get_idealista_url($distrito_slug, $concelho_slug, $freguesia_slug = null, $property_type = null, $bedrooms = null, $operation = 'venda') {
    // 1. Determine the base operation type. This is always 'casas' now.
    $op_string = ($operation === 'venda') ? 'comprar' : 'arrendar';
    $base_op_type = "{$op_string}-casas";

    // 2. Determine the location path.
    $location_path = '';
    if ($freguesia_slug && $concelho_slug && $distrito_slug) {
        $location_path = "{$distrito_slug}/{$concelho_slug}/{$freguesia_slug}/";
    } else if ($concelho_slug && $distrito_slug) {
        $location_path = "{$distrito_slug}/{$concelho_slug}/";
    } else if ($distrito_slug) {
        $location_path = "{$distrito_slug}-distrito/";
    }

    // 3. Build the modifier string (e.g., 'apartamentos,t1')
    $modifiers = [];
    if ($property_type === 'apartamentos' || $property_type === 'moradias') {
        $modifiers[] = $property_type;
    }
    if ($bedrooms) {
        $bedroom_map = ['t0', 't1', 't2', 't3', 't4-t5'];
        if (in_array($bedrooms, $bedroom_map)) {
            $modifiers[] = $bedrooms;
        }
    }

    // 4. Assemble the final URL
    $final_url = "https://www.idealista.pt/{$base_op_type}/{$location_path}";

    if (!empty($modifiers)) {
        $final_url .= 'com-' . implode(',', $modifiers) . '/';
    }

    return rtrim($final_url, '/');
}

/**
 * Scrapes a given Idealista URL to find the average price per square meter.
 *
 * @param string $url The URL to scrape.
 * @return int|string The found price as an integer, or an error message string.
 */
function tagus_value_scrape_url($url) {
    $args = [
        'timeout' => 20, // Set a reasonable timeout
        'headers' => [
            'User-Agent' => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
    ];
    $response = wp_remote_get($url, $args);

    if (is_wp_error($response)) {
        return 'Error fetching URL: ' . $response->get_error_message();
    }

    $body = wp_remote_retrieve_body($response);
    if (empty($body)) {
        return 'Error: Empty response body from URL: ' . esc_url($url);
    }

    // Suppress errors for malformed HTML, which is common.
    libxml_use_internal_errors(true);
    $dom = new DOMDocument();
    $dom->loadHTML($body);
    libxml_clear_errors();

    $xpath = new DOMXPath($dom);

    // The price is usually in a `<span>` or `<div>` with text "eur/m²"
    // Example: <div class="items-average-price"> Preço médio nesta zona 2.839 eur/m² </div>
    // The class name changes, so we search for the text content.
    $query = '//*[contains(text(), "eur/m²")]';
    $nodes = $xpath->query($query);

    if ($nodes->length > 0) {
        $node = $nodes->item(0);
        $text = $node->nodeValue;

        // Use regex to extract the number. It might have a dot as a thousand separator.
        // Example: "Preço médio nesta zona 2.839 eur/m²"
        if (preg_match('/(\d{1,3}(?:\.\d{3})*|\d+)/', $text, $matches)) {
            // The price is the first match. Remove dots.
            $price = str_replace('.', '', $matches[0]);
            return (int) $price;
        }
    }

    return 'Error: Price not found.';
}

/**
 * Handles the scraping for a single location, intended to be called via an admin action.
 *
 * @param array $params An array containing the location slugs.
 *                      'distrito_slug', 'concelho_slug', 'freguesia_slug' (optional),
 *                      'property_type' (optional), 'bedrooms' (optional),
 *                      'operation' ('venda' or 'arrendar').
 * @return string The scraped price or an error message.
 */
function tagus_value_scrape_single_location($params) {
    // Basic validation
    if (empty($params['distrito_slug']) || empty($params['concelho_slug']) || empty($params['operation'])) {
        return 'Error: Missing required location parameters.';
    }

    $url = tagus_value_get_idealista_url(
        $params['distrito_slug'],
        $params['concelho_slug'],
        $params['freguesia_slug'] ?? null,
        $params['property_type'] ?? null,
        $params['bedrooms'] ?? null,
        $params['operation']
    );

    $price = tagus_value_scrape_url($url);

    // We can expand this to return more structured data if needed
    return $price;
}
