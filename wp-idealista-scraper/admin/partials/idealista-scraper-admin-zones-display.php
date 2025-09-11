<?php
/**
 * Provide a admin area view for the plugin
 *
 * This file is used to markup the admin-facing aspects of the plugin.
 *
 * @link       https://www.linkedin.com/in/soufiane-sadaoui/
 * @since      1.0.0
 *
 * @package    Idealista_Scraper
 * @subpackage Idealista_Scraper/admin/partials
 */

// Handle form submission
if (isset($_POST['save_zone_selections'])) {
    // Nonce verification for security
    if (!isset($_POST['idealista_scraper_zones_nonce']) || !wp_verify_nonce($_POST['idealista_scraper_zones_nonce'], 'idealista_scraper_save_zones')) {
        die('Security check failed');
    }

    // Get selected freguesias
    $selected_freguesias = isset($_POST['selected_freguesias']) ? array_map('sanitize_text_field', $_POST['selected_freguesias']) : [];

    // Save the selection to WordPress options
    update_option('idealista_scraper_selected_zones', $selected_freguesias);

    // Display a confirmation message
    echo '<div class="notice notice-success is-dismissible"><p>Your zone selections have been saved!</p></div>';
}

// Get saved selections
$saved_selections = get_option('idealista_scraper_selected_zones', []);

// Load the administrative structure from the JSON file
$json_path = plugin_dir_path(__FILE__) . '../../portugal_administrative_structure.json';
$administrative_structure = [];
if (file_exists($json_path)) {
    $json_content = file_get_contents($json_path);
    $data = json_decode($json_content, true);
    if (isset($data['php_array'])) {
        $administrative_structure = $data['php_array'];
    }
}

// Fetch stats from the backend API
$api_url = get_option('idealista_scraper_api_url');
$stats = [];
if ($api_url) {
    $response = wp_remote_get($api_url . '/api/stats/detailed');
    if (!is_wp_error($response) && wp_remote_retrieve_response_code($response) === 200) {
        $body = wp_remote_retrieve_body($response);
        $stats_data = json_decode($body, true);

        // Re-key stats for easy lookup
        foreach ($stats_data as $stat) {
            $key = $stat['region'] . '|' . $stat['location'];
            $stats[$key] = $stat['detailed_stats'];
        }
    }
}

function get_stats_for_freguesia($distrito_code, $concelho_code, $freguesia_code, $stats) {
    $location_key = "{$distrito_code}_{$freguesia_code}";
    $key = "{$distrito_code}|{$location_key}";
    return isset($stats[$key]) ? $stats[$key] : [];
}

?>

<div class="wrap">
    <h1>Idealista Scraper - Zone Management</h1>
    <p>Select the administrative zones you want to scrape. The scraper will iterate through each selected 'freguesia'.</p>

    <form method="POST" action="">
        <?php wp_nonce_field('idealista_scraper_save_zones', 'idealista_scraper_zones_nonce'); ?>

        <div id="zone-selection-tree">
            <?php foreach ($administrative_structure as $distrito_name => $distrito_data) :
                $distrito_code = $distrito_data['code'];
            ?>
                <div class.php="distrito-group">
                    <h2 class="distrito-title">
                        <input type="checkbox" class="distrito-checkbox" data-distrito="<?php echo esc_attr($distrito_code); ?>">
                        <?php echo esc_html($distrito_name); ?>
                    </h2>
                    <div class="concelhos-container">
                        <?php foreach ($distrito_data['freguesias'] as $concelho_name => $concelho_data) :
                            $concelho_code = $concelho_data['code'];
                        ?>
                            <div class="concelho-group">
                                <h3 class="concelho-title">
                                    <input type="checkbox" class="concelho-checkbox" data-concelho="<?php echo esc_attr($concelho_code); ?>" data-distrito="<?php echo esc_attr($distrito_code); ?>">
                                    <?php echo esc_html($concelho_name); ?>
                                </h3>
                                <ul class="freguesias-list">
                                    <?php foreach ($concelho_data['freguesias'] as $freguesia_name => $freguesia_data) :
                                        $freguesia_code = $freguesia_data['code'];
                                        $full_code = "{$distrito_code}|{$concelho_code}|{$freguesia_code}";
                                        $is_checked = in_array($full_code, $saved_selections);
                                        $freguesia_stats = get_stats_for_freguesia($distrito_code, $concelho_code, $freguesia_code, $stats);
                                    ?>
                                        <li>
                                            <label>
                                                <input type="checkbox" name="selected_freguesias[]" value="<?php echo esc_attr($full_code); ?>" <?php checked($is_checked); ?> class="freguesia-checkbox" data-distrito="<?php echo esc_attr($distrito_code); ?>" data-concelho="<?php echo esc_attr($concelho_code); ?>">
                                                <?php echo esc_html($freguesia_name); ?>
                                            </label>
                                            <span class="stats-info">
                                                <?php if (!empty($freguesia_stats)): ?>
                                                    <?php foreach($freguesia_stats as $stat): ?>
                                                        <span class="stat-item <?php echo esc_attr($stat['operation_type']); ?>">
                                                            <?php echo esc_html(ucfirst($stat['property_type'])); ?> (<?php echo esc_html($stat['operation_type']); ?>):
                                                            <strong><?php echo number_format($stat['avg_price_per_sqm'], 2); ?> €/m²</strong>
                                                        </span>
                                                    <?php endforeach; ?>
                                                <?php else: ?>
                                                    <span class="no-data">(No data)</span>
                                                <?php endif; ?>
                                            </span>
                                        </li>
                                    <?php endforeach; ?>
                                </ul>
                            </div>
                        <?php endforeach; ?>
                    </div>
                </div>
            <?php endforeach; ?>
        </div>

        <?php submit_button('Save Selections', 'primary', 'save_zone_selections'); ?>
    </form>
</div>
