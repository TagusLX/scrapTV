<?php

if (!defined('ABSPATH')) exit;

/**
 * Get the Idealista URL for a specific location and entity type.
 *
 * @param string $base_type 'comprar-casas' or 'arrendar-casas'.
 * @param array  $slugs Associative array of slugs ('distrito', 'concelho', 'freguesia', 'type', 'bedrooms').
 * @return string The generated URL.
 */
function tagus_value_get_idealista_url($base_type, $slugs = []) {
    $base_url = 'https://www.idealista.pt/' . $base_type;
    $path_parts = [];
    $extra_params = [];

    // Build the main path
    if (!empty($slugs['distrito'])) {
        $path_parts[] = $slugs['distrito'] . '-distrito';
    }
    if (!empty($slugs['concelho'])) {
        // As per user feedback, concelho path resets the base and doesn't include distrito.
        $path_parts = [$slugs['concelho']];
    }
    if (!empty($slugs['freguesia'])) {
        $path_parts[] = $slugs['freguesia'];
    }

    // Build the extra parameters for property types and bedrooms
    if (!empty($slugs['type'])) {
        $extra_params[] = 'com-' . $slugs['type'];
    }
    if (!empty($slugs['bedrooms'])) {
        $extra_params[] = $slugs['bedrooms'];
    }
    // Long-term rentals have a specific URL parameter that must be included
    if ($base_type === 'arrendar-casas' && (!empty($slugs['type']) || !empty($slugs['bedrooms']))) {
         $extra_params[] = 'arrendamento-longa-duracao';
    }

    $url = rtrim($base_url . '/' . implode('/', $path_parts), '/');

    if (!empty($extra_params)) {
        $url .= '/' . implode(',', $extra_params);
    }

    return $url . '/';
}
?>
