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

// Include the market data structure
require_once plugin_dir_path(__FILE__) . 'market-prices.php';

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

    $data = tagus_value_get_market_data();
    $distritos = array_keys($data);
    
    // Handle form submission
    $results = [];
    if (isset($_POST['scrape_distrito']) && check_admin_referer('scrape_distrito_nonce', 'scrape_nonce')) {
        $distrito = sanitize_text_field($_POST['distrito']);
        $property_type = sanitize_text_field($_POST['property_type']);
        $result = scrape_idealista_price($distrito, '', '', $property_type);
        $result['level'] = 'Distrito';
        $result['location'] = ucfirst(str_replace('_', ' ', $distrito));
        $result['property_type'] = get_property_type_label($property_type);
        $results[] = $result;
    } elseif (isset($_POST['scrape_concelho']) && check_admin_referer('scrape_concelho_nonce', 'scrape_nonce')) {
        $distrito = sanitize_text_field($_POST['distrito']);
        $concelho = sanitize_text_field($_POST['concelho']);
        $property_type = sanitize_text_field($_POST['property_type']);
        $result = scrape_idealista_price($distrito, $concelho, '', $property_type);
        $result['level'] = 'Concelho';
        $result['location'] = $data[$distrito][$concelho]['name'];
        $result['property_type'] = get_property_type_label($property_type);
        $results[] = $result;
    } elseif (isset($_POST['scrape_price']) && check_admin_referer('scrape_price_nonce', 'scrape_nonce')) {
        $distrito = sanitize_text_field($_POST['distrito']);
        $concelho = sanitize_text_field($_POST['concelho']);
        $freguesia = sanitize_text_field($_POST['freguesia']);
        $property_type = sanitize_text_field($_POST['property_type']);
        $result = scrape_idealista_price($distrito, $concelho, $freguesia, $property_type);
        $result['level'] = 'Freguesia';
        $result['location'] = $data[$distrito][$concelho]['name'] . ', ' . $data[$distrito][$concelho]['freguesias'][$freguesia]['name'];
        $result['property_type'] = get_property_type_label($property_type);
        $results[] = $result;
    }

    ?>
    <div class="wrap">
        <h1>Tagus Value Price Scraper</h1>
        <p>Sélectionnez le Distrito, Concelho, Freguesia et type de bien pour scraper le prix moyen au m² depuis Idealista. Les résultats s'affichent dans le tableau ci-dessous.</p>
        
        <form method="post" id="scraper-form">
            <table class="form-table">
                <tr>
                    <th scope="row">Type de Bien</th>
                    <td>
                        <select name="property_type" id="property_type" required>
                            <option value="comprar-casas/com-apartamentos">Vente (Appartements)</option>
                            <option value="comprar-casas/com-moradias">Vente (Maisons)</option>
                            <option value="arrendar-casas/com-apartamentos">Location (Appartements)</option>
                            <option value="arrendar-casas/com-moradias">Location (Maisons)</option>
                            <option value="comprar-terrenos/com-terreno-urbano">Terrain Constructible</option>
                            <option value="comprar-terrenos/com-terreno-nao-urbanizavel">Terrain Non-Constructible</option>
                        </select>
                    </td>
                </tr>
                <tr>
                    <th scope="row">Distrito</th>
                    <td>
                        <select name="distrito" id="distrito" required>
                            <option value="">Choisir un Distrito</option>
                            <?php foreach ($distritos as $distrito_key): ?>
                                <option value="<?php echo esc_attr($distrito_key); ?>"><?php echo esc_html(ucfirst(str_replace('_', ' ', $distrito_key))); ?></option>
                            <?php endforeach; ?>
                        </select>
                        <?php wp_nonce_field('scrape_distrito_nonce', 'scrape_nonce'); ?>
                        <?php submit_button('Scraper au niveau Distrito', 'secondary', 'scrape_distrito'); ?>
                    </td>
                </tr>
                <tr>
                    <th scope="row">Concelho</th>
                    <td>
                        <select name="concelho" id="concelho" disabled>
                            <option value="">Sélectionnez d'abord un Distrito</option>
                        </select>
                        <?php wp_nonce_field('scrape_concelho_nonce', 'scrape_nonce'); ?>
                        <?php submit_button('Scraper au niveau Concelho', 'secondary', 'scrape_concelho', false); ?>
                    </td>
                </tr>
                <tr>
                    <th scope="row">Freguesia</th>
                    <td>
                        <select name="freguesia" id="freguesia" disabled>
                            <option value="">Sélectionnez d'abord un Concelho</option>
                        </select>
                        <?php wp_nonce_field('scrape_price_nonce', 'scrape_nonce'); ?>
                        <?php submit_button('Scraper au niveau Freguesia', 'primary', 'scrape_price', false); ?>
                    </td>
                </tr>
            </table>
        </form>
        
        <?php if (!empty($results)): ?>
            <h2>Résultats du Scraping</h2>
            <table class="wp-list-table widefat fixed striped">
                <thead>
                    <tr>
                        <th>Niveau</th>
                        <th>Type de Bien</th>
                        <th>Lieu</th>
                        <th>Prix Moyen</th>
                        <th>URL</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($results as $result): ?>
                        <tr>
                            <td><?php echo esc_html($result['level']); ?></td>
                            <td><?php echo esc_html($result['property_type']); ?></td>
                            <td><?php echo esc_html($result['location']); ?></td>
                            <td>
                                <?php if ($result['price'] !== false): ?>
                                    <?php echo esc_html($result['price']); ?> €/m²
                                <?php else: ?>
                                    <span style="color: red;"><?php echo esc_html($result['error']); ?></span>
                                <?php endif; ?>
                            </td>
                            <td><a href="<?php echo esc_url($result['url']); ?>" target="_blank"><?php echo esc_html($result['url']); ?></a></td>
                        </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        <?php endif; ?>
    </div>

    <script>
    jQuery(document).ready(function($) {
        var data = <?php echo json_encode($data); ?>;
        
        // Populate Concelho dropdown when Distrito changes
        $('#distrito').change(function() {
            var distrito = $(this).val();
            $('#concelho').html('<option value="">Choisir un Concelho</option>').prop('disabled', true);
            $('#freguesia').html('<option value="">Choisir une Freguesia</option>').prop('disabled', true);
            $('#scrape_concelho').prop('disabled', true);
            $('#scrape_price').prop('disabled', true);
            
            if (distrito && data[distrito]) {
                var concelhos = Object.keys(data[distrito]).filter(key => key !== 'average' && key !== 'average_rent');
                concelhos.forEach(function(concelhoKey) {
                    var option = '<option value="' + concelhoKey + '">' + data[distrito][concelhoKey].name + '</option>';
                    $('#concelho').append(option);
                });
                $('#concelho').prop('disabled', false);
                $('#scrape_concelho').prop('disabled', false);
            }
        });
        
        // Populate Freguesia dropdown when Concelho changes
        $('#concelho').change(function() {
            var distrito = $('#distrito').val();
            var concelho = $(this).val();
            $('#freguesia').html('<option value="">Choisir une Freguesia</option>').prop('disabled', true);
            $('#scrape_price').prop('disabled', true);
            
            if (distrito && concelho && data[distrito][concelho]) {
                var freguesias = data[distrito][concelho].freguesias;
                Object.keys(freguesias).forEach(function(freguesiaKey) {
                    var option = '<option value="' + freguesiaKey + '">' + freguesias[freguesiaKey].name + '</option>';
                    $('#freguesia').append(option);
                });
                $('#freguesia').prop('disabled', false);
                $('#scrape_price').prop('disabled', false);
            }
        });
        
        // AJAX form submission
        $('#scraper-form').submit(function(e) {
            e.preventDefault();
            var formData = $(this).serialize();
            var action = '';
            var level = '';
            if ($(e.originalEvent.submitter).attr('name') === 'scrape_distrito') {
                action = 'scrape_distrito_ajax';
                level = 'Distrito';
            } else if ($(e.originalEvent.submitter).attr('name') === 'scrape_concelho') {
                action = 'scrape_concelho_ajax';
                level = 'Concelho';
            } else {
                action = 'scrape_price_ajax';
                level = 'Freguesia';
            }
            $.post(ajaxurl, formData + '&action=' + action + '&scrape_nonce=<?php echo wp_create_nonce('scrape_price_ajax'); ?>', function(response) {
                var resultsTable = $('#results-table tbody');
                if (!resultsTable.length) {
                    $('.wp-list-table').remove();
                    $('.wrap').append('<h2>Résultats du Scraping</h2><table class="wp-list-table widefat fixed striped" id="results-table"><thead><tr><th>Niveau</th><th>Type de Bien</th><th>Lieu</th><th>Prix Moyen</th><th>URL</th></tr></thead><tbody></tbody></table>');
                    resultsTable = $('#results-table tbody');
                }
                var row = '';
                if (response.success) {
                    row = '<tr><td>' + level + '</td><td>' + response.data.property_type + '</td><td>' + response.data.location + '</td><td>' + response.data.price + ' €/m²</td><td><a href="' + response.data.url + '" target="_blank">' + response.data.url + '</a></td></tr>';
                } else {
                    row = '<tr><td>' + level + '</td><td>' + response.data.property_type + '</td><td>' + response.data.location + '</td><td><span style="color: red;">' + response.data.error + '</span></td><td><a href="' + response.data.url + '" target="_blank">' + response.data.url + '</a></td></tr>';
                }
                resultsTable.append(row);
            });
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

// AJAX handlers
add_action('wp_ajax_scrape_distrito_ajax', 'handle_scrape_distrito_ajax');
function handle_scrape_distrito_ajax() {
    check_ajax_referer('scrape_price_ajax', 'scrape_nonce');
    
    $distrito = sanitize_text_field($_POST['distrito']);
    $property_type = sanitize_text_field($_POST['property_type']);
    $data = tagus_value_get_market_data();
    
    $result = scrape_idealista_price($distrito, '', '', $property_type);
    $result['level'] = 'Distrito';
    $result['location'] = ucfirst(str_replace('_', ' ', $distrito));
    $result['property_type'] = get_property_type_label($property_type);
    
    if ($result['price'] !== false) {
        wp_send_json_success($result);
    } else {
        wp_send_json_error($result);
    }
}

add_action('wp_ajax_scrape_concelho_ajax', 'handle_scrape_concelho_ajax');
function handle_scrape_concelho_ajax() {
    check_ajax_referer('scrape_price_ajax', 'scrape_nonce');
    
    $distrito = sanitize_text_field($_POST['distrito']);
    $concelho = sanitize_text_field($_POST['concelho']);
    $property_type = sanitize_text_field($_POST['property_type']);
    $data = tagus_value_get_market_data();
    
    $result = scrape_idealista_price($distrito, $concelho, '', $property_type);
    $result['level'] = 'Concelho';
    $result['location'] = $data[$distrito][$concelho]['name'];
    $result['property_type'] = get_property_type_label($property_type);
    
    if ($result['price'] !== false) {
        wp_send_json_success($result);
    } else {
        wp_send_json_error($result);
    }
}

add_action('wp_ajax_scrape_price_ajax', 'handle_scrape_price_ajax');
function handle_scrape_price_ajax() {
    check_ajax_referer('scrape_price_ajax', 'scrape_nonce');
    
    $distrito = sanitize_text_field($_POST['distrito']);
    $concelho = sanitize_text_field($_POST['concelho']);
    $freguesia = sanitize_text_field($_POST['freguesia']);
    $property_type = sanitize_text_field($_POST['property_type']);
    $data = tagus_value_get_market_data();
    
    $result = scrape_idealista_price($distrito, $concelho, $freguesia, $property_type);
    $result['level'] = 'Freguesia';
    $result['location'] = $data[$distrito][$concelho]['name'] . ', ' . $data[$distrito][$concelho]['freguesias'][$freguesia]['name'];
    $result['property_type'] = get_property_type_label($property_type);
    
    if ($result['price'] !== false) {
        wp_send_json_success($result);
    } else {
        wp_send_json_error($result);
    }
}

// Function to scrape the average price
function scrape_idealista_price($distrito, $concelho = '', $freguesia = '', $property_type = 'comprar-casas/com-apartamentos') {
    // Split property_type into base and subtype
    $parts = explode('/', $property_type);
    $base_type = $parts[0];
    $subtype = isset($parts[1]) ? '/' . $parts[1] : '';
    
    // Construct URL based on level
    if ($freguesia) {
        $url = 'https://www.idealista.pt/' . $base_type . '/' . $concelho . '/' . $freguesia . $subtype . '/';
    } elseif ($concelho) {
        $url = 'https://www.idealista.pt/' . $base_type . '/' . $concelho . $subtype . '/';
    } else {
        $url = 'https://www.idealista.pt/' . $base_type . '/' . $distrito . $subtype . '/';
    }
    
    // Fetch the page using wp_remote_get
    $response = wp_remote_get($url, array(
        'timeout' => 30,
        'user-agent' => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    ));
    
    if (is_wp_error($response)) {
        $error_message = 'Erreur HTTP : ' . $response->get_error_message();
        error_log('Tagus Value Scraper: ' . $error_message . ' for URL - ' . $url);
        return array('price' => false, 'error' => $error_message, 'url' => $url);
    }
    
    $body = wp_remote_retrieve_body($response);
    if (empty($body)) {
        $error_message = 'Réponse vide : la page n\'a pas pu être chargée.';
        error_log('Tagus Value Scraper: ' . $error_message . ' for URL - ' . $url);
        return array('price' => false, 'error' => $error_message, 'url' => $url);
    }
    
    // Parse HTML using DOMDocument
    $dom = new DOMDocument();
    @$dom->loadHTML('<?xml encoding="UTF-8">' . $body); // Handle encoding
    $xpath = new DOMXPath($dom);
    
    // Find <p class="items-average-price">
    $price_nodes = $xpath->query('//p[@class="items-average-price"]');
    if ($price_nodes->length > 0) {
        $price_text = $price_nodes->item(0)->textContent;
        // Extract numeric value (e.g., "3.349 eur/m²" -> 3.349)
        if (preg_match('/([\d,.]+)/', $price_text, $matches)) {
            $price = floatval(str_replace(',', '.', $matches[1]));
            error_log('Tagus Value Scraper: Successfully scraped price ' . $price . ' for URL - ' . $url);
            return array('price' => $price, 'error' => '', 'url' => $url);
        }
    }
    
    $error_message = 'Aucun prix moyen trouvé. La page peut ne pas contenir de données ou l\'élément items-average-price est absent. Essayez un autre niveau ou type de bien, ou utilisez l\'API Idealista.';
    error_log('Tagus Value Scraper: ' . $error_message . ' for URL - ' . $url);
    return array('price' => false, 'error' => $error_message, 'url' => $url);
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