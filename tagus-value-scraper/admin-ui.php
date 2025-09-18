<?php

if (!defined('ABSPATH')) {
    exit; // Exit if accessed directly
}

/**
 * Renders the main admin page for the Tagus Value Scraper.
 * This version uses a collapsible accordion UI to prevent timeouts.
 */
function tagus_value_admin_page() {
    // Get the current state from URL parameters
    $open_distrito  = isset($_GET['open_distrito']) ? sanitize_key($_GET['open_distrito']) : null;
    $open_concelho  = isset($_GET['open_concelho']) ? sanitize_key($_GET['open_concelho']) : null;
    $open_freguesia = isset($_GET['open_freguesia']) ? sanitize_key($_GET['open_freguesia']) : null;

    // Load the market data
    $market_data = tagus_value_load_market_data();
    ?>
    <div class="wrap">
        <h1>Tagus Value Market Data</h1>
        <p>Browse the locations below. Click on a location to expand it. The detailed price table will only appear when you expand a Freguesia.</p>

        <style>
            .tagus-value-accordion details { border: 1px solid #ddd; margin-bottom: 5px; }
            .tagus-value-accordion summary { padding: 10px; font-weight: bold; cursor: pointer; background: #f9f9f9; }
            .tagus-value-accordion .level-2 summary { margin-left: 20px; }
            .tagus-value-accordion .level-3 summary { margin-left: 40px; }
            .tagus-value-accordion .data-table-container { padding: 10px; margin-left: 60px; }
        </style>

        <div class="tagus-value-accordion">
            <?php
            // Main form for saving any visible data
            echo '<form method="post" action="">';
            wp_nonce_field('tagus_value_admin_actions', 'tagus_value_nonce_field');

            // Loop through Distritos
            foreach ($market_data as $distrito_slug => $distrito_data) {
                $is_open = ($distrito_slug === $open_distrito);
                $distrito_link = admin_url('admin.php?page=tagus-value-scraper&open_distrito=' . $distrito_slug);

                echo '<details class="level-1" ' . ($is_open ? 'open' : '') . '>';
                echo '<summary><a href="' . esc_url($distrito_link) . '">' . esc_html($distrito_data['name']) . '</a></summary>';

                // Only render children if this distrito is open
                if ($is_open) {
                    // Loop through Concelhos
                    foreach ($distrito_data['concelhos'] as $concelho_slug => $concelho_data) {
                        $is_concelho_open = ($concelho_slug === $open_concelho);
                        $concelho_link = admin_url('admin.php?page=tagus-value-scraper&open_distrito=' . $distrito_slug . '&open_concelho=' . $concelho_slug);

                        echo '<details class="level-2" ' . ($is_concelho_open ? 'open' : '') . '>';
                        echo '<summary><a href="' . esc_url($concelho_link) . '">' . esc_html($concelho_data['name']) . '</a></summary>';

                        // Only render children if this concelho is open
                        if ($is_concelho_open) {
                            // Loop through Freguesias
                            foreach ($concelho_data['freguesias'] as $freguesia_slug => $freguesia_data) {
                                $is_freguesia_open = ($freguesia_slug === $open_freguesia);
                                $freguesia_link = admin_url('admin.php?page=tagus-value-scraper&open_distrito=' . $distrito_slug . '&open_concelho=' . $concelho_slug . '&open_freguesia=' . $freguesia_slug);

                                echo '<details class="level-3" ' . ($is_freguesia_open ? 'open' : '') . '>';
                                echo '<summary><a href="' . esc_url($freguesia_link) . '">' . esc_html($freguesia_data['name']) . '</a></summary>';

                                // Only render the data table if this freguesia is open
                                if ($is_freguesia_open) {
                                    echo '<div class="data-table-container">';
                                    $freguesia_path = [$distrito_slug, 'concelhos', $concelho_slug, 'freguesias', $freguesia_slug, 'data'];
                                    tagus_value_render_data_points_table($freguesia_data['data'], $freguesia_path, $distrito_slug, $concelho_slug, $freguesia_slug);
                                    echo '</div>';
                                }
                                echo '</details>'; // Freguesia
                            }
                        }
                        echo '</details>'; // Concelho
                    }
                }
                echo '</details>'; // Distrito
            }

            // The save button is only useful if a table is visible
            if ($open_freguesia) {
                echo '<p class="submit"><input type="submit" name="tagus_value_save_data" class="button button-primary" value="Save Changes"></p>';
            }
            echo '</form>';
            ?>
        </div>
    </div>
    <?php
}

/**
 * Renders the final data points table for a single location.
 */
function tagus_value_render_data_points_table($data_points, $base_path, $distrito_slug, $concelho_slug, $freguesia_slug) {
    ?>
    <table class="wp-list-table widefat fixed striped">
        <thead>
            <tr>
                <th style="width: 40%;">Type</th>
                <th style="width: 15%;">Price (€/m²)</th>
                <th style="width: 10%;">Scrape</th>
                <th>Idealista URL</th>
            </tr>
        </thead>
        <tbody>
            <?php
            $operations = ['venda' => 'Sale', 'arrendar' => 'Rent'];
            $property_types = ['apartamentos' => 'Apartments', 'moradias' => 'Villas'];
            $bedrooms_map = ['all' => 'All Bedrooms', 't0' => 'T0', 't1' => 'T1', 't2' => 'T2', 't3' => 'T3', 't4-t5' => 'T4/T5'];

            foreach ($operations as $op_key => $op_name) {
                foreach ($property_types as $pt_key => $pt_name) {
                    // Render the "All Bedrooms" summary row first
                    $all_bed_key = 'all';
                    if (isset($data_points[$op_key][$pt_key][$all_bed_key])) {
                        $all_bed_data = $data_points[$op_key][$pt_key][$all_bed_key];
                        $current_path = array_merge($base_path, [$op_key, $pt_key, $all_bed_key]);
                        $label = '<strong>' . $op_name . ' - ' . $pt_name . '</strong>';
                        tagus_value_render_single_row($label, $all_bed_data, $current_path, $distrito_slug, $concelho_slug, $freguesia_slug, $op_key, $pt_key, null);
                    }

                    // Render the specific bedroom types
                    foreach ($bedrooms_map as $bed_key => $bed_name) {
                        if ($bed_key === 'all') continue;

                        if (isset($data_points[$op_key][$pt_key][$bed_key])) {
                            $bedroom_data = $data_points[$op_key][$pt_key][$bed_key];
                            $current_path = array_merge($base_path, [$op_key, $pt_key, $bed_key]);
                            $label = $op_name . ' - ' . $pt_name . ' - ' . $bed_name;
                            tagus_value_render_single_row($label, $bedroom_data, $current_path, $distrito_slug, $concelho_slug, $freguesia_slug, $op_key, $pt_key, $bed_key);
                        }
                    }
                }
            }
            ?>
        </tbody>
    </table>
    <?php
}

/**
 * Renders a single row in the data table.
 */
function tagus_value_render_single_row($label, $data, $key_path, $distrito_slug, $concelho_slug, $freguesia_slug, $operation, $property_type, $bedrooms) {
    $price_input_name = 'market_data';
    foreach ($key_path as $key) {
        $price_input_name .= '[' . $key . ']';
    }
    $price_input_name .= '[price]';
    ?>
    <tr>
        <td><?php echo $label; ?></td>
        <td>
            <input type="text" name="<?php echo esc_attr($price_input_name); ?>" value="<?php echo esc_attr($data['price']); ?>" class="small-text">
        </td>
        <td>
            <form method="post" action="" class="scrape-form">
                <?php wp_nonce_field('tagus_value_admin_actions', 'tagus_value_nonce_field'); ?>
                <input type="hidden" name="scrape_params[distrito_slug]" value="<?php echo esc_attr($distrito_slug); ?>">
                <input type="hidden" name="scrape_params[concelho_slug]" value="<?php echo esc_attr($concelho_slug); ?>">
                <input type="hidden" name="scrape_params[freguesia_slug]" value="<?php echo esc_attr($freguesia_slug); ?>">
                <input type="hidden" name="scrape_params[operation]" value="<?php echo esc_attr($operation); ?>">
                <input type="hidden" name="scrape_params[property_type]" value="<?php echo esc_attr($property_type); ?>">
                <?php if ($bedrooms): ?>
                <input type="hidden" name="scrape_params[bedrooms]" value="<?php echo esc_attr($bedrooms); ?>">
                <?php endif; ?>
                <?php foreach ($key_path as $key): ?>
                <input type="hidden" name="scrape_params[key_path][]" value="<?php echo esc_attr($key); ?>">
                <?php endforeach; ?>
                <input type="submit" name="tagus_value_scrape_single" class="button button-secondary" value="Scrape">
            </form>
        </td>
        <td><a href="<?php echo esc_url($data['url']); ?>" target="_blank">View on Idealista</a></td>
    </tr>
    <?php
}
