<?php
/**
 * Plugin Name: Tagus Value Price Scraper
 * Plugin URI: https://tagusvalue.com
 * Description: WordPress plugin to scrape average prices per m² from Idealista at Distrito, Concelho, and Freguesia levels for apartments, houses (sale/rent), and terrains. Displays results in a table in backoffice.
 * Version: 1.7.0
 * Author: xAI Assistant
 * License: GPL v2 or later
 * Text Domain: tagus-value-scraper
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

// Include the market data structure if it exists
if (file_exists(plugin_dir_path(__FILE__) . 'market-data.php')) {
    require_once plugin_dir_path(__FILE__) . 'market-data.php';
}

/**
 * Generate a URL-friendly slug from a string.
 *
 * @param string $text The input string.
 * @return string The sanitized slug.
 */
function tagus_value_generate_slug($text) {
    // Transliterate special characters to ASCII
    $text = iconv('UTF-8', 'ASCII//TRANSLIT', $text);
    // Convert to lowercase
    $text = strtolower($text);
    // Replace characters that are not letters, numbers, or hyphens with a hyphen
    $text = preg_replace('/[^a-z0-9\-]+/', '-', $text);
    // Replace multiple hyphens with a single one
    $text = preg_replace('/-+/', '-', $text);
    // Trim hyphens from the beginning and end
    $text = trim($text, '-');

    if (empty($text)) {
        return 'n-a';
    }

    return $text;
}

/**
 * Process the locations.tsv file and build a hierarchical data array.
 *
 * @return array The market data structure skeleton.
 */
function tagus_value_process_locations_file() {
    $data = [];
    $file_path = plugin_dir_path(__FILE__) . 'locations.tsv';

    if (!file_exists($file_path)) {
        error_log('Tagus Value Scraper: locations.tsv file not found.');
        return $data;
    }

    if (($handle = fopen($file_path, 'r')) !== FALSE) {
        fgetcsv($handle, 0, "\t"); // Skip header row

        while (($row = fgetcsv($handle, 0, "\t")) !== FALSE) {
            if (count($row) < 3) {
                continue;
            }

            $distrito_name = trim($row[0]);
            $concelho_name = trim($row[1]);
            $freguesia_raw_name = trim($row[2]);

            // Clean freguesia name as per user request
            $freguesia_name = $freguesia_raw_name;
            $prefix_to_remove = 'União das freguesias de ';
            if (strpos($freguesia_raw_name, $prefix_to_remove) === 0) {
                $freguesia_name = substr($freguesia_raw_name, strlen($prefix_to_remove));
            }

            // Generate slugs for array keys
            $distrito_slug = tagus_value_generate_slug($distrito_name);
            $concelho_slug = tagus_value_generate_slug($concelho_name);
            $freguesia_slug = tagus_value_generate_slug($freguesia_name);

            // Build the hierarchical array structure
            if (!isset($data[$distrito_slug])) {
                $data[$distrito_slug] = ['name' => $distrito_name];
            }
            if (!isset($data[$distrito_slug][$concelho_slug])) {
                $data[$distrito_slug][$concelho_slug] = ['name' => $concelho_name, 'freguesias' => []];
            }
            $data[$distrito_slug][$concelho_slug]['freguesias'][$freguesia_slug] = ['name' => $freguesia_name];
        }
        fclose($handle);
    }

    return $data;
}


/**
 * Sanitizes the submitted array of prices.
 *
 * @param array $array The input array.
 * @return array The sanitized array.
 */
function tagus_value_sanitize_prices_array($array) {
    foreach ($array as $key => &$value) {
        if (is_array($value)) {
            $value = tagus_value_sanitize_prices_array($value);
        } else {
            if ($value === '') {
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

// Handle admin form submissions
add_action('admin_init', 'tagus_value_handle_admin_actions');
function tagus_value_handle_admin_actions() {
    // Handle starting a new scrape
    if (isset($_POST['start_scrape_submit'])) {
        check_admin_referer('tagus_value_start_scrape_action', 'tagus_value_nonce');

        if (get_option('tagus_value_scrape_status') === 'running') {
            return;
        }

        update_option('tagus_value_scrape_status', 'running');

        // Create a flat list of all concelhos to process
        $all_locations = tagus_value_process_locations_file();
        $concelhos_to_scrape = [];
        $initial_data = [];

        $base_url_sale = 'https://www.idealista.pt/comprar-casas';
        $base_url_rent = 'https://www.idealista.pt/arrendar-casas';

        foreach ($all_locations as $distrito_slug => $distrito_data) {
            // Scrape top-level distrito prices immediately
            $distrito_data['average'] = tagus_value_scrape_url("$base_url_sale/$distrito_slug-distrito/")['price'];
            $distrito_data['average_rent'] = tagus_value_scrape_url("$base_url_rent/$distrito_slug-distrito/")['price'];
            $initial_data[$distrito_slug] = $distrito_data;

            foreach ($distrito_data as $concelho_slug => $concelho_data) {
                if (is_array($concelho_data) && isset($concelho_data['freguesias'])) {
                    $concelhos_to_scrape[] = [
                        'distrito_slug' => $distrito_slug,
                        'concelho_slug' => $concelho_slug
                    ];
                }
            }
        }

        // Save the initial data with distrito prices
        $market_data_path = plugin_dir_path(__FILE__) . 'market-data.json';
        file_put_contents($market_data_path, json_encode($initial_data, JSON_PRETTY_PRINT));

        // Schedule the first concelho batch
        wp_clear_scheduled_hook('tagus_value_scrape_concelho_hook');
        wp_schedule_single_event(time() + 5, 'tagus_value_scrape_concelho_hook', array('concelhos' => $concelhos_to_scrape));

        add_action('admin_notices', function() {
            echo '<div class="notice notice-success is-dismissible"><p>Le processus de scraping complet a été lancé. Cela peut prendre plusieurs heures.</p></div>';
        });
    }

    // Handle saving manual prices
    if (isset($_POST['tagus_value_action']) && $_POST['tagus_value_action'] === 'save_manual_prices') {
        check_admin_referer('tagus_value_save_prices_action', 'tagus_value_prices_nonce');

        $submitted_prices = isset($_POST['prices']) ? $_POST['prices'] : [];
        $sanitized_prices = tagus_value_sanitize_prices_array($submitted_prices);

        $market_data_path = plugin_dir_path(__FILE__) . 'market-data.json';
        $existing_data = file_exists($market_data_path) ? json_decode(file_get_contents($market_data_path), true) : [];
        $existing_data = is_array($existing_data) ? $existing_data : [];

        // Merge the sanitized data into the existing data
        $updated_data = array_replace_recursive($existing_data, $sanitized_prices);

        // Save the data back to JSON and regenerate the PHP file
        file_put_contents($market_data_path, json_encode($updated_data, JSON_PRETTY_PRINT));
        tagus_value_generate_php_data_file();

        add_action('admin_notices', function() {
            echo '<div class="notice notice-success is-dismissible"><p>Les prix manuels ont été enregistrés avec succès.</p></div>';
        });
    }
}

add_action('tagus_value_scrape_concelho_hook', 'tagus_value_scrape_concelho_hook_func', 10, 1);
/**
 * The main worker function for the WP-Cron batch scraping process.
 * Processes one concelho at a time.
 */
function tagus_value_scrape_concelho_hook_func($args) {
    $concelhos = isset($args['concelhos']) ? $args['concelhos'] : [];

    if (empty($concelhos)) {
        update_option('tagus_value_scrape_status', 'idle');
        tagus_value_generate_php_data_file();
        error_log('Tagus Value Scraper: Full scrape completed and market-data.php generated.');
        return;
    }

    $concelho_to_process = array_shift($concelhos);
    $distrito_slug = $concelho_to_process['distrito_slug'];
    $concelho_slug = $concelho_to_process['concelho_slug'];

    // Load all data
    $market_data_path = plugin_dir_path(__FILE__) . 'market-data.json';
    $market_data = file_exists($market_data_path) ? json_decode(file_get_contents($market_data_path), true) : [];
    $market_data = is_array($market_data) ? $market_data : [];

    // Scrape the data for this concelho
    if (isset($market_data[$distrito_slug][$concelho_slug])) {
        $concelho_data = $market_data[$distrito_slug][$concelho_slug];
        $scraped_data = tagus_value_scrape_single_concelho($distrito_slug, $concelho_slug, $concelho_data);
        $market_data[$distrito_slug][$concelho_slug] = $scraped_data;

        file_put_contents($market_data_path, json_encode($market_data, JSON_PRETTY_PRINT));
        error_log("Tagus Value Scraper: Finished scraping and saved data for concelho: $concelho_slug.");
    }

    // If there are more concelhos, reschedule the hook for the next batch
    if (!empty($concelhos)) {
        wp_schedule_single_event(time() + 5, 'tagus_value_scrape_concelho_hook', array('concelhos' => $concelhos));
    } else {
        update_option('tagus_value_scrape_status', 'idle');
        tagus_value_generate_php_data_file();
        error_log('Tagus Value Scraper: Full scrape process finished and market-data.php generated.');
    }
}

/**
 * Scrapes all data for a single concelho and its freguesias.
 */
function tagus_value_scrape_single_concelho($distrito_slug, $concelho_slug, $concelho_data) {
    $base_url_sale = 'https://www.idealista.pt/comprar-casas';
    $base_url_rent = 'https://www.idealista.pt/arrendar-casas';

    // Scrape Concelho level
    $concelho_url_sale = "$base_url_sale/$concelho_slug-concelho/";
    $concelho_url_rent = "$base_url_rent/$concelho_slug-concelho/";
    $concelho_data['average'] = tagus_value_scrape_url($concelho_url_sale)['price'];
    $concelho_data['average_rent'] = tagus_value_scrape_url($concelho_url_rent)['price'];
    sleep(1);

    // Scrape Freguesias
    if (isset($concelho_data['freguesias']) && is_array($concelho_data['freguesias'])) {
        foreach ($concelho_data['freguesias'] as $freguesia_slug => &$freguesia_data) {
            $freguesia_url_sale = "$base_url_sale/$concelho_slug-concelho/$freguesia_slug/";
            $freguesia_url_rent = "$base_url_rent/$concelho_slug-concelho/$freguesia_slug/";
            $freguesia_data['average'] = tagus_value_scrape_url($freguesia_url_sale)['price'];
            $freguesia_data['average_rent'] = tagus_value_scrape_url($freguesia_url_rent)['price'];
            sleep(1);
        }
        unset($freguesia_data);
    }

    return $concelho_data;
}

/**
 * Generates the final market-data.php file from the JSON data store.
 */
function tagus_value_generate_php_data_file() {
    $json_path = plugin_dir_path(__FILE__) . 'market-data.json';
    if (!file_exists($json_path)) {
        error_log('Tagus Value Scraper: Cannot generate PHP data file, market-data.json not found.');
        return;
    }

    $data = json_decode(file_get_contents($json_path), true);
    if (json_last_error() !== JSON_ERROR_NONE) {
        error_log('Tagus Value Scraper: Error decoding market-data.json: ' . json_last_error_msg());
        return;
    }

    $array_export = var_export($data, true);
    $timestamp = current_time('d-m-Y (H:i)');

    $file_content = <<<EOD
<?php
/**
 * Market prices data for Portugal
 * Last update {$timestamp}
 * @link       https://tagusvalue.com
 * @since      1.0.0
 *
 * @package    Tagus_Value
 * @subpackage Tagus_Value/data
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

if (!function_exists('tagus_value_get_market_data')) {
    /**
     * Get market data for Portuguese real estate
     *
     * @return array Market data by region
     */
    function tagus_value_get_market_data() {
        return {$array_export};
    }
}
EOD;

    $php_file_path = plugin_dir_path(__FILE__) . 'market-data.php';
    file_put_contents($php_file_path, $file_content);
}

// Admin menu
add_action('admin_menu', 'tagus_value_scraper_menu');
function tagus_value_scraper_menu() {
    add_menu_page(
        'Tagus Value Price Scraper',
        'Price Scraper',
        'manage_options',
        'tagus-value-scraper',
        'tagus_value_scraper_admin_page',
        'dashicons-chart-line',
        30
    );
}

// Admin page
function tagus_value_scraper_admin_page() {
    if (!current_user_can('manage_options')) {
        wp_die('Unauthorized access');
    }

    // Get current scraping status
    $scrape_status = get_option('tagus_value_scrape_status', 'idle');

    // Use the new function to get the full list of locations
    $data = tagus_value_process_locations_file();
    ?>
    <div class="wrap">
        <h1>Tagus Value Price Scraper</h1>

        <div style="border: 1px solid #ccc; padding: 10px; margin-bottom: 20px; background: #fff;">
            <h2>Contrôle du Scraping</h2>
            <p><strong>Statut actuel:</strong> <?php echo esc_html(ucfirst($scrape_status)); ?></p>
            <form method="post">
                <?php wp_nonce_field('tagus_value_start_scrape_action', 'tagus_value_nonce'); ?>
                <input type="hidden" name="tagus_value_action" value="start_full_scrape">
                <?php
                $disabled_attr = ($scrape_status === 'running') ? 'disabled="disabled"' : '';
                submit_button('Lancer le Scraping Complet', 'primary', 'start_scrape_submit', true, $disabled_attr);
                ?>
            </form>
            <?php if ($scrape_status === 'running'): ?>
                <p><i>Le scraping est en cours. Cela peut prendre plusieurs heures. Les données seront mises à jour progressivement.</i></p>
            <?php endif; ?>
        </div>
        
        <hr>

        <h2>Sélecteur de Localisation (Données Complètes)</h2>
        <table class="form-table">
            <tr>
                <th scope="row">Distrito</th>
                <td>
                    <select name="distrito" id="distrito" required>
                        <option value="">Choisir un Distrito</option>
                        <?php foreach ($data as $distrito_slug => $distrito_info): ?>
                            <option value="<?php echo esc_attr($distrito_slug); ?>"><?php echo esc_html($distrito_info['name']); ?></option>
                        <?php endforeach; ?>
                    </select>
                </td>
            </tr>
            <tr>
                <th scope="row">Concelho</th>
                <td>
                    <select name="concelho" id="concelho" disabled>
                        <option value="">Sélectionnez d'abord un Distrito</option>
                    </select>
                </td>
            </tr>
            <tr>
                <th scope="row">Freguesia</th>
                <td>
                    <select name="freguesia" id="freguesia" disabled>
                        <option value="">Sélectionnez d'abord un Concelho</option>
                    </select>
                </td>
            </tr>
        </table>

        <hr>
        <h2>Données du Marché Actuel</h2>
        <?php
        $market_data = function_exists('tagus_value_get_market_data') ? tagus_value_get_market_data() : [];
        if (empty($market_data)):
        ?>
            <p>Aucune donnée de marché n'a encore été générée. Lancez le scraping pour commencer.</p>
        <?php else: ?>
            <form method="post">
                <input type="hidden" name="tagus_value_action" value="save_manual_prices">
                <?php wp_nonce_field('tagus_value_save_prices_action', 'tagus_value_prices_nonce'); ?>

                <style>
                    .market-data-table .concelho-row td:first-child { padding-left: 30px; }
                    .market-data-table .freguesia-row td:first-child { padding-left: 60px; }
                    .market-data-table .distrito-row { background-color: #f0f6fc; }
                    .market-data-table input[type="text"] { width: 100px; }
                </style>
                <table class="wp-list-table widefat fixed striped market-data-table">
                    <thead>
                        <tr>
                            <th>Localisation</th>
                            <th>Prix Moyen Vente (€/m²)</th>
                            <th>Prix Moyen Location (€/m²)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($market_data as $distrito_slug => $distrito_data): ?>
                            <tr class="distrito-row">
                                <td><strong><?php echo esc_html($distrito_data['name'] ?? $distrito_slug); ?></strong></td>
                                <td><input type="text" size="8" name="prices[<?php echo esc_attr($distrito_slug); ?>][average]" value="<?php echo esc_attr($distrito_data['average'] ?? ''); ?>" placeholder="N/A" /></td>
                                <td><input type="text" size="8" name="prices[<?php echo esc_attr($distrito_slug); ?>][average_rent]" value="<?php echo esc_attr($distrito_data['average_rent'] ?? ''); ?>" placeholder="N/A" /></td>
                            </tr>
                            <?php foreach ($distrito_data as $concelho_slug => $concelho_data): ?>
                                <?php if (!is_array($concelho_data) || !isset($concelho_data['freguesias'])) continue; ?>
                                <tr class="concelho-row">
                                    <td><?php echo esc_html($concelho_data['name']); ?></td>
                                    <td><input type="text" size="8" name="prices[<?php echo esc_attr($distrito_slug); ?>][<?php echo esc_attr($concelho_slug); ?>][average]" value="<?php echo esc_attr($concelho_data['average'] ?? ''); ?>" placeholder="N/A" /></td>
                                    <td><input type="text" size="8" name="prices[<?php echo esc_attr($distrito_slug); ?>][<?php echo esc_attr($concelho_slug); ?>][average_rent]" value="<?php echo esc_attr($concelho_data['average_rent'] ?? ''); ?>" placeholder="N/A" /></td>
                                </tr>
                                <?php foreach ($concelho_data['freguesias'] as $freguesia_slug => $freguesia_data): ?>
                                    <tr class="freguesia-row">
                                        <td><?php echo esc_html($freguesia_data['name']); ?></td>
                                        <td><input type="text" size="8" name="prices[<?php echo esc_attr($distrito_slug); ?>][<?php echo esc_attr($concelho_slug); ?>][freguesias][<?php echo esc_attr($freguesia_slug); ?>][average]" value="<?php echo esc_attr($freguesia_data['average'] ?? ''); ?>" placeholder="N/A" /></td>
                                        <td><input type="text" size="8" name="prices[<?php echo esc_attr($distrito_slug); ?>][<?php echo esc_attr($concelho_slug); ?>][freguesias][<?php echo esc_attr($freguesia_slug); ?>][average_rent]" value="<?php echo esc_attr($freguesia_data['average_rent'] ?? ''); ?>" placeholder="N/A" /></td>
                                    </tr>
                                <?php endforeach; ?>
                            <?php endforeach; ?>
                        <?php endforeach; ?>
                    </tbody>
                </table>
                <?php submit_button('Enregistrer les modifications manuelles'); ?>
            </form>
        <?php endif; ?>

    </div>

    <script>
    jQuery(document).ready(function($) {
        var data = <?php echo json_encode($data); ?>;
        
        // Populate Concelho dropdown when Distrito changes
        $('#distrito').change(function() {
            var distrito = $(this).val();
            var concelhoSelect = $('#concelho');
            var freguesiaSelect = $('#freguesia');

            concelhoSelect.html('<option value="">Choisir un Concelho</option>').prop('disabled', true);
            freguesiaSelect.html('<option value="">Choisir une Freguesia</option>').prop('disabled', true);
            
            if (distrito && data[distrito]) {
                var concelhos = Object.keys(data[distrito]).filter(key => key !== 'name' && key !== 'average' && key !== 'average_rent');
                concelhos.forEach(function(concelhoKey) {
                    var option = '<option value="' + concelhoKey + '">' + data[distrito][concelhoKey].name + '</option>';
                    concelhoSelect.append(option);
                });
                concelhoSelect.prop('disabled', false);
            }
        });
        
        // Populate Freguesia dropdown when Concelho changes
        $('#concelho').change(function() {
            var distrito = $('#distrito').val();
            var concelho = $(this).val();
            var freguesiaSelect = $('#freguesia');

            freguesiaSelect.html('<option value="">Choisir une Freguesia</option>').prop('disabled', true);
            
            if (distrito && concelho && data[distrito][concelho] && data[distrito][concelho].freguesias) {
                var freguesias = data[distrito][concelho].freguesias;
                Object.keys(freguesias).forEach(function(freguesiaKey) {
                    var option = '<option value="' + freguesiaKey + '">' + freguesias[freguesiaKey].name + '</option>';
                    freguesiaSelect.append(option);
                });
                freguesiaSelect.prop('disabled', false);
            }
        });
    });
    </script>
    <?php
}

// Helper function to get property type label
function get_property_type_label($property_type) {
    $labels = array(
        'comprar-casas/com-apartamentos' => 'Vente (Appartements)',
        'comprar-casas/com-moradias' => 'Vente (Maisons)',
        'arrendar-casas/com-apartamentos' => 'Location (Appartements)',
        'arrendar-casas/com-moradias' => 'Location (Maisons)',
        'comprar-terrenos/com-terreno-urbano' => 'Terrain Constructible',
        'comprar-terrenos/com-terreno-nao-urbanizavel' => 'Terrain Non-Constructible'
    );
    return isset($labels[$property_type]) ? $labels[$property_type] : $property_type;
}

// Obsolete AJAX handlers removed.

/**
 * Scrapes a single Idealista URL for its average price.
 *
 * @param string $url The URL to scrape.
 * @return array A result array with 'price', 'error', and 'url'.
 */
function tagus_value_scrape_url($url) {
    $response = wp_remote_get($url, array(
        'timeout' => 30,
        'user-agent' => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    ));

    if (is_wp_error($response)) {
        return array('price' => false, 'error' => 'Erreur HTTP: ' . $response->get_error_message(), 'url' => $url);
    }

    $body = wp_remote_retrieve_body($response);
    if (empty($body)) {
        return array('price' => false, 'error' => 'Réponse vide.', 'url' => $url);
    }

    $dom = new DOMDocument();
    @$dom->loadHTML('<?xml encoding="UTF-8">' . $body);
    $xpath = new DOMXPath($dom);

    // Try primary selector first, then fallbacks
    $selectors = array(
        '//p[@class="items-average-price"]',
        '//*[contains(text(), "eur/m²")]'
    );
    
    foreach ($selectors as $selector) {
        $price_nodes = $xpath->query($selector);
        if ($price_nodes->length > 0) {
            $price_text = $price_nodes->item(0)->textContent;
            if (preg_match('/([\d,.]+)/', $price_text, $matches)) {
                $price_string = $matches[1];
                // Handle Portuguese number format (e.g., "1.234,56")
                $price_string_no_thousands = str_replace('.', '', $price_string);
                $price_string_for_float = str_replace(',', '.', $price_string_no_thousands);
                $price = floatval($price_string_for_float);
                return array('price' => $price, 'error' => '', 'url' => $url);
            }
        }
    }

    return array('price' => false, 'error' => 'Aucun prix moyen trouvé.', 'url' => $url);
}

/**
 * Runs the full scraping process for all locations.
 * This function is intended to be called by a background process.
 *
 * @return array The fully populated market data array.
 */
function tagus_value_run_full_scrape() {
    $market_data = tagus_value_process_locations_file();
    $base_url_sale = 'https://www.idealista.pt/comprar-casas';
    $base_url_rent = 'https://www.idealista.pt/arrendar-casas';

    foreach ($market_data as $distrito_slug => &$distrito_data) {
        $distrito_url_sale = "$base_url_sale/$distrito_slug-distrito/";
        $distrito_url_rent = "$base_url_rent/$distrito_slug-distrito/";

        $distrito_data['average'] = tagus_value_scrape_url($distrito_url_sale)['price'];
        $distrito_data['average_rent'] = tagus_value_scrape_url($distrito_url_rent)['price'];
        sleep(1);

        foreach ($distrito_data as $concelho_slug => &$concelho_data) {
            if (!is_array($concelho_data) || !isset($concelho_data['freguesias'])) {
                continue;
            }

            $concelho_url_sale = "$base_url_sale/$concelho_slug-concelho/";
            $concelho_url_rent = "$base_url_rent/$concelho_slug-concelho/";

            $concelho_data['average'] = tagus_value_scrape_url($concelho_url_sale)['price'];
            $concelho_data['average_rent'] = tagus_value_scrape_url($concelho_url_rent)['price'];
            sleep(1);

            foreach ($concelho_data['freguesias'] as $freguesia_slug => &$freguesia_data) {
                $freguesia_url_sale = "$base_url_sale/$concelho_slug/$freguesia_slug/";
                $freguesia_url_rent = "$base_url_rent/$concelho_slug/$freguesia_slug/";

                $freguesia_data['average'] = tagus_value_scrape_url($freguesia_url_sale)['price'];
                $freguesia_data['average_rent'] = tagus_value_scrape_url($freguesia_url_rent)['price'];
                sleep(1);
            }
            unset($freguesia_data);
        }
        unset($concelho_data);
    }
    unset($distrito_data);

    // In a later phase, this will write to a file. For now, it returns the data.
    return $market_data;
}

// Enqueue jQuery for AJAX
add_action('admin_enqueue_scripts', 'tagus_value_scraper_scripts');
function tagus_value_scraper_scripts($hook) {
    if ($hook !== 'toplevel_page_tagus-value-scraper') {
        return;
    }
    wp_enqueue_script('jquery');
}
?>