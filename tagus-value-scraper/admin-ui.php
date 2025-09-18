<?php

if (!defined('ABSPATH')) exit;

/**
 * Recursively renders the rows of the market data table.
 *
 * @param array $data The data to render.
 * @param array $path_prefix The current path in the data hierarchy.
 */
function tagus_value_render_data_table_rows($data, $path_prefix = []) {
    $level = count($path_prefix);
    $indent = str_repeat('&nbsp;', $level * 6);
    $item_slugs = array_keys($data);

    // Prioritize specific keys to render them in a consistent order
    $key_order = ['name', 'average', 'average_rent', 'url_sale', 'url_rent', 'concelhos', 'freguesias', 'types', 'apartamentos', 'moradias'];

    // This is complex, a simple loop is better for this structure.
    foreach ($data as $slug => $item) {
        if (!is_array($item)) continue;

        $current_path = array_merge($path_prefix, [$slug]);
        $name_path = 'prices[' . implode('][', $current_path) . ']';
        $name = $item['name'] ?? ucfirst(str_replace(['-', '_'], ' ', $slug));

        echo '<tr class="level-' . esc_attr($level) . '">';
        echo '<td>' . $indent . esc_html($name) . '</td>';

        // Check if this level is a scrapable entity (i.e., it has the price template)
        if (array_key_exists('average', $item)) {
            $url = $item['url_sale'] ?: '#';
            echo '<td><input type="text" size="8" name="' . $name_path . '[average]" value="' . esc_attr($item['average'] ?? '') . '"/></td>';
            echo '<td><input type="text" size="8" name="' . $name_path . '[average_rent]" value="' . esc_attr($item['average_rent'] ?? '') . '"/></td>';
            echo '<td><a href="' . esc_url($url) . '" target="_blank">Voir</a></td>';
            echo '<td>' . get_submit_button('Scraper', 'secondary', 'scrape_path[' . implode('][', $current_path) . ']', false, ['style' => 'padding: 1px 5px; height: auto;']) . '</td>';
        } else {
            echo '<td colspan="4"></td>';
        }
        echo '</tr>';

        // Recurse into nested data levels
        if (!empty($item['concelhos'])) {
            tagus_value_render_data_table_rows($item['concelhos'], $current_path);
        }
        if (!empty($item['freguesias'])) {
            tagus_value_render_data_table_rows($item['freguesias'], array_merge($current_path, ['freguesias']));
        }
        if (!empty($item['types'])) {
            tagus_value_render_data_table_rows($item['types'], array_merge($current_path, ['types']));
        }
    }
}

add_action('admin_menu', 'tagus_value_scraper_menu');
function tagus_value_scraper_menu() {
    add_menu_page('Tagus Value Price Scraper', 'Price Scraper', 'manage_options', 'tagus-value-scraper', 'tagus_value_scraper_admin_page', 'dashicons-chart-line', 30);
}

function tagus_value_scraper_admin_page() {
    if (!current_user_can('manage_options')) {
        wp_die('Unauthorized access');
    }

    // This logic merges the full skeleton with any saved data
    $location_skeleton = tagus_value_get_location_skeleton();
    $market_data = function_exists('tagus_value_get_market_data') ? tagus_value_get_market_data() : [];
    $display_data = array_replace_recursive($location_skeleton, $market_data);
    ?>
    <div class="wrap">
        <h1>Tagus Value Price Scraper</h1>
        <p>Cliquez sur un bouton "Scraper" pour récupérer les données pour une ligne spécifique. Sauvegardez toutes les modifications manuelles avec le bouton "Enregistrer".</p>

        <form method="post">
            <input type="hidden" name="tagus_value_action" value="scrape_or_save">
            <?php wp_nonce_field('tagus_value_action_nonce', 'tagus_value_nonce'); ?>

            <style>
                .market-data-table td { vertical-align: middle; }
                .level-0 { font-weight: bold; background-color: #f0f6fc; }
                .level-1 td:first-child { padding-left: 25px; }
                .level-2 { background-color: #f8f9fa; }
                .level-2 td:first-child { padding-left: 50px; }
                .level-3 td:first-child { padding-left: 75px; font-style: italic; }
                .level-4 td:first-child { padding-left: 100px; }
                .market-data-table input[type="text"] { width: 90px; }
            </style>

            <?php submit_button('Enregistrer toutes les modifications'); ?>

            <table class="wp-list-table widefat fixed striped">
                <thead>
                    <tr>
                        <th style="width: 45%;">Localisation</th>
                        <th>Prix Vente (€/m²)</th>
                        <th>Prix Location (€/m²)</th>
                        <th>URL</th>
                        <th style="width: 10%;">Action</th>
                    </tr>
                </thead>
                <tbody>
                    <?php tagus_value_render_data_table_rows($display_data); ?>
                </tbody>
            </table>

            <?php submit_button('Enregistrer toutes les modifications'); ?>
        </form>
    </div>
    <?php
}
?>
