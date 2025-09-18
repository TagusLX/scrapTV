<?php

if (!defined('ABSPATH')) {
    exit; // Exit if accessed directly
}

/**
 * Renders the main admin page for the Tagus Value Scraper.
 */
function tagus_value_admin_page() {
    // Load the market data. This will initialize from skeleton if it doesn't exist.
    $market_data = tagus_value_load_market_data();
    ?>
    <div class="wrap">
        <h1>Tagus Value Market Data</h1>
        <p>Manually edit prices below or click "Scrape" to fetch the latest average price for a specific entry. Click "Save All Changes" to save all manual edits.</p>

        <form method="post" action="">
            <?php wp_nonce_field('tagus_value_admin_actions', 'tagus_value_nonce_field'); ?>

            <p class="submit">
                <input type="submit" name="tagus_value_save_data" class="button button-primary" value="Save All Changes">
            </p>

            <style>
                .tagus-value-table { table-layout: fixed; }
                .tagus-value-table .scrape-form { margin: 0; }
            </style>
            <table class="wp-list-table widefat fixed striped tagus-value-table">
                <thead>
                    <tr>
                        <th style="width: 40%;">Location / Type</th>
                        <th style="width: 15%;">Price (€/m²)</th>
                        <th style="width: 10%;">Scrape</th>
                        <th>Idealista URL</th>
                    </tr>
                </thead>
                <tbody>
                    <?php
                    // Start the recursive rendering
                    tagus_value_render_distritos($market_data);
                    ?>
                </tbody>
            </table>

            <p class="submit">
                <input type="submit" name="tagus_value_save_data" class="button button-primary" value="Save All Changes">
            </p>
        </form>
    </div>
    <?php
}

/**
 * Renders the distrito level of the data table.
 */
function tagus_value_render_distritos($data) {
    foreach ($data as $distrito_slug => $distrito_data) {
        echo '<tr class="table-section-header"><td colspan="4"><strong>Distrito: ' . esc_html($distrito_data['name']) . '</strong></td></tr>';

        $distrito_path = [$distrito_slug, 'data'];
        tagus_value_render_data_points($distrito_data['data'], $distrito_path, $distrito_slug, null, null, 1);

        foreach ($distrito_data['concelhos'] as $concelho_slug => $concelho_data) {
            echo '<tr><td colspan="4" style="padding-left: 20px;"><strong>Concelho: ' . esc_html($concelho_data['name']) . '</strong></td></tr>';

            $concelho_path = [$distrito_slug, 'concelhos', $concelho_slug, 'data'];
            tagus_value_render_data_points($concelho_data['data'], $concelho_path, $distrito_slug, $concelho_slug, null, 2);

            foreach ($concelho_data['freguesias'] as $freguesia_slug => $freguesia_data) {
                echo '<tr><td colspan="4" style="padding-left: 40px;"><strong>Freguesia: ' . esc_html($freguesia_data['name']) . '</strong></td></tr>';

                $freguesia_path = [$distrito_slug, 'concelhos', $concelho_slug, 'freguesias', $freguesia_slug, 'data'];
                tagus_value_render_data_points($freguesia_data['data'], $freguesia_path, $distrito_slug, $concelho_slug, $freguesia_slug, 3);
            }
        }
    }
}

/**
 * Recursive function to render the data points for a given location level.
 */
function tagus_value_render_data_points($data_points, $base_path, $distrito_slug, $concelho_slug, $freguesia_slug, $level) {
    $indent = str_repeat('&mdash;', $level * 2) . ' ';
    $padding = $level * 20;

    $operations = ['venda' => 'Sale', 'arrendar' => 'Rent'];
    $property_types = ['apartamentos' => 'Apartments', 'moradias' => 'Villas'];
    $bedrooms_map = ['all' => 'All Bedrooms', 't0' => 'T0', 't1' => 'T1', 't2' => 'T2', 't3' => 'T3', 't4-t5' => 'T4/T5'];

    foreach ($operations as $op_key => $op_name) {
        foreach ($property_types as $pt_key => $pt_name) {
            // Render the "All Bedrooms" summary row first
            $all_bed_key = 'all';
            $all_bed_data = $data_points[$op_key][$pt_key][$all_bed_key];
            $current_path = array_merge($base_path, [$op_key, $pt_key, $all_bed_key]);
            $label = $indent . '<strong>' . $op_name . ' - ' . $pt_name . '</strong>';
            tagus_value_render_single_row($label, $all_bed_data, $current_path, $distrito_slug, $concelho_slug, $freguesia_slug, $op_key, $pt_key, null, $padding);

            // Render the specific bedroom types
            foreach ($bedrooms_map as $bed_key => $bed_name) {
                if ($bed_key === 'all') continue; // Skip the one we just did

                $bedroom_data = $data_points[$op_key][$pt_key][$bed_key];
                $current_path = array_merge($base_path, [$op_key, $pt_key, $bed_key]);
                $label = $indent . $op_name . ' - ' . $pt_name . ' - ' . $bed_name;
                tagus_value_render_single_row($label, $bedroom_data, $current_path, $distrito_slug, $concelho_slug, $freguesia_slug, $op_key, $pt_key, $bed_key, $padding);
            }
        }
    }
}

/**
 * Renders a single row in the data table.
 *
 * @param string      $label          The display label for the row.
 * @param array       $data           The data for this row ('price' and 'url').
 * @param array       $key_path       The array keys to reach this data point from the root.
 * @param string      $distrito_slug  The slug of the district.
 * @param string|null $concelho_slug  The slug of the concelho.
 * @param string|null $freguesia_slug The slug of the freguesia.
 * @param string      $operation      'venda' or 'arrendar'.
 * @param string      $property_type  'apartamentos' or 'moradias'.
 * @param string|null $bedrooms       The bedroom key ('t0', 't1', etc.), or null for the "all bedrooms" category.
 * @param int         $padding        The left padding in pixels for indentation.
 */
function tagus_value_render_single_row($label, $data, $key_path, $distrito_slug, $concelho_slug, $freguesia_slug, $operation, $property_type, $bedrooms, $padding) {
    $price_input_name = 'market_data';
    foreach ($key_path as $key) {
        $price_input_name .= '[' . $key . ']';
    }
    $price_input_name .= '[price]';
    ?>
    <tr>
        <td style="padding-left: <?php echo $padding + 20; ?>px;"><?php echo $label; ?></td>
        <td>
            <input type="text" name="<?php echo esc_attr($price_input_name); ?>" value="<?php echo esc_attr($data['price']); ?>" class="small-text">
        </td>
        <td>
            <form method="post" action="" style="margin: 0;">
                <?php wp_nonce_field('tagus_value_admin_actions', 'tagus_value_nonce_field'); ?>
                <input type="hidden" name="scrape_params[distrito_slug]" value="<?php echo esc_attr($distrito_slug); ?>">
                <?php if ($concelho_slug): ?>
                <input type="hidden" name="scrape_params[concelho_slug]" value="<?php echo esc_attr($concelho_slug); ?>">
                <?php endif; ?>
                <?php if ($freguesia_slug): ?>
                <input type="hidden" name="scrape_params[freguesia_slug]" value="<?php echo esc_attr($freguesia_slug); ?>">
                <?php endif; ?>
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
