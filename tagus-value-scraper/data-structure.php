<?php

if (!defined('ABSPATH')) {
    exit; // Exit if accessed directly
}

/**
 * Builds the full, nested data structure for all locations.
 * This structure serves as the initial template for the market data.
 *
 * @return array The complete data skeleton.
 */
function tagus_value_get_location_skeleton() {
    $locations = tagus_value_get_location_data();
    $skeleton = [];

    $operations = ['venda', 'arrendar'];
    $property_types = ['apartamentos', 'moradias'];
    $bedrooms = ['t0', 't1', 't2', 't3', 't4-t5'];

    foreach ($locations as $distrito_slug => $distrito_data) {
        $skeleton[$distrito_slug] = [
            'name' => $distrito_data['name'],
            'slug' => $distrito_slug,
            'data' => [],
            'concelhos' => [],
        ];

        // Generate data structure for the distrito itself
        $skeleton[$distrito_slug]['data'] = tagus_value_get_data_points_for_location($distrito_slug, null, null);

        foreach ($distrito_data['concelhos'] as $concelho_slug => $concelho_data) {
            $skeleton[$distrito_slug]['concelhos'][$concelho_slug] = [
                'name' => $concelho_data['name'],
                'slug' => $concelho_slug,
                'data' => [],
                'freguesias' => [],
            ];

            // Generate data structure for the concelho
            $skeleton[$distrito_slug]['concelhos'][$concelho_slug]['data'] = tagus_value_get_data_points_for_location($distrito_slug, $concelho_slug, null);

            foreach ($concelho_data['freguesias'] as $freguesia_slug => $freguesia_data) {
                 $skeleton[$distrito_slug]['concelhos'][$concelho_slug]['freguesias'][$freguesia_slug] = [
                    'name' => $freguesia_data['name'],
                    'slug' => $freguesia_slug,
                    'data' => [],
                ];

                // Generate data structure for the freguesia
                $skeleton[$distrito_slug]['concelhos'][$concelho_slug]['freguesias'][$freguesia_slug]['data'] = tagus_value_get_data_points_for_location($distrito_slug, $concelho_slug, $freguesia_slug);
            }
        }
    }

    return $skeleton;
}

/**
 * Helper function to generate the nested data points for a single location.
 * (distrito, concelho, or freguesia)
 *
 * @param string $distrito_slug
 * @param string|null $concelho_slug
 * @param string|null $freguesia_slug
 * @return array The generated data points.
 */
function tagus_value_get_data_points_for_location($distrito_slug, $concelho_slug, $freguesia_slug) {
    $data_points = [];
    $operations = ['venda', 'arrendar'];
    $property_types = ['apartamentos', 'moradias'];
    // The 'all' key represents the category total (e.g., all apartments, regardless of bedroom count)
    $bedrooms = ['all', 't0', 't1', 't2', 't3', 't4-t5'];

    foreach ($operations as $operation) {
        $data_points[$operation] = [];
        foreach ($property_types as $property_type) {
            $data_points[$operation][$property_type] = [];

            foreach ($bedrooms as $bedroom_key) {
                // For the 'all' category, the bedroom parameter should be null.
                $bedroom_param_for_url = ($bedroom_key === 'all') ? null : $bedroom_key;

                $data_points[$operation][$property_type][$bedroom_key] = [
                    'price' => '',
                    'url' => tagus_value_get_idealista_url($distrito_slug, $concelho_slug, $freguesia_slug, $property_type, $bedroom_param_for_url, $operation)
                ];
            }
        }
    }
    return $data_points;
}
