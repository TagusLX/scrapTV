<?php

/**
 * The admin-specific functionality of the plugin.
 *
 * @link       https://example.com/
 * @since      1.0.0
 *
 * @package    Idealista_Scraper
 * @subpackage Idealista_Scraper/admin
 */

/**
 * The admin-specific functionality of the plugin.
 *
 * Defines the plugin name, version, and two examples hooks for how to
 * enqueue the admin-specific stylesheet and JavaScript.
 *
 * @package    Idealista_Scraper
 * @subpackage Idealista_Scraper/admin
 * @author     Jules <jules@example.com>
 */
class Idealista_Scraper_Admin {

    /**
     * The ID of this plugin.
     *
     * @since    1.0.0
     * @access   private
     * @var      string    $plugin_name    The ID of this plugin.
     */
    private $plugin_name;

    /**
     * The version of this plugin.
     *
     * @since    1.0.0
     * @access   private
     * @var      string    $version    The current version of this plugin.
     */
    private $version;

    /**
     * Initialize the class and set its properties.
     *
     * @since    1.0.0
     * @param      string    $plugin_name       The name of this plugin.
     * @param      string    $version    The version of this plugin.
     */
    public function __construct( $plugin_name, $version ) {

        $this->plugin_name = $plugin_name;
        $this->version = $version;

        add_action('wp_ajax_get_selected_zones', array($this, 'get_selected_zones'));
    }

    /**
     * Register the stylesheets for the admin area.
     *
     * @since    1.0.0
     */
    public function enqueue_styles() {
        $screen = get_current_screen();
        wp_enqueue_style( $this->plugin_name, plugin_dir_url( __FILE__ ) . 'css/idealista-scraper-admin.css', array(), $this->version, 'all' );

        // Enqueue zones-specific assets only on the zones page
        if (isset($screen->id) && strpos($screen->id, 'idealista-scraper-zones') !== false) {
            wp_enqueue_style( $this->plugin_name . '-zones', plugin_dir_url( __FILE__ ) . 'css/idealista-scraper-zones-admin.css', array(), $this->version, 'all' );
        }

        // Enqueue dashboard-specific assets only on the dashboard page
        if (isset($screen->id) && strpos($screen->id, 'idealista-scraper-dashboard') !== false) {
            wp_enqueue_style( $this->plugin_name . '-dashboard', plugin_dir_url( __FILE__ ) . 'css/idealista-scraper-dashboard.css', array(), $this->version, 'all' );
        }
    }

    /**
     * Register the JavaScript for the admin area.
     *
     * @since    1.0.0
     */
    public function enqueue_scripts() {
    $screen = get_current_screen();

    // General script for all plugin pages
        wp_enqueue_script( $this->plugin_name, plugin_dir_url( __FILE__ ) . 'js/idealista-scraper-admin.js', array( 'jquery' ), $this->version, false );

    // Localize data for the general script
        wp_localize_script( $this->plugin_name, 'idealista_scraper_ajax', array(
            'ajax_url' => admin_url( 'admin-ajax.php' ),
            'api_url' => get_option('idealista_scraper_api_url'),
            'start_scraping_nonce' => wp_create_nonce('idealista_scraper_start_scraping'),
            'solve_captcha_nonce' => wp_create_nonce('idealista_scraper_solve_captcha'),
        ) );

    // Enqueue zones-specific assets only on the zones page
    if (isset($screen->id) && strpos($screen->id, 'idealista-scraper-zones') !== false) {
        wp_enqueue_script( $this->plugin_name . '-zones', plugin_dir_url( __FILE__ ) . 'js/idealista-scraper-zones-admin.js', array( 'jquery' ), $this->version, true );
    }

    // Enqueue dashboard-specific assets only on the dashboard page
    if (isset($screen->id) && strpos($screen->id, 'idealista-scraper-dashboard') !== false) {
        wp_enqueue_script( $this->plugin_name . '-dashboard', plugin_dir_url( __FILE__ ) . 'js/idealista-scraper-dashboard.js', array( 'jquery' ), $this->version, true );
    }
    }

    /**
     * Add the admin menu for the plugin.
     *
     * @since    1.0.0
     */
    public function add_plugin_admin_menu() {
        add_menu_page(
            'Idealista Scraper',
            'Idealista Scraper',
            'manage_options',
            $this->plugin_name,
            array( $this, 'display_plugin_setup_page' ),
            'dashicons-admin-generic',
            25
        );

    add_submenu_page(
        $this->plugin_name,
        'Zone Management',
        'Zone Management',
        'manage_options',
        'idealista-scraper-zones',
        array( $this, 'display_zones_page' )
    );

    add_submenu_page(
        $this->plugin_name,
        'Dashboard',
        'Dashboard',
        'manage_options',
        'idealista-scraper-dashboard',
        array( $this, 'display_dashboard_page' )
    );
    }

    /**
 * Display the main admin page.
     *
     * @since    1.0.0
     */
    public function display_plugin_setup_page() {
        require_once 'partials/idealista-scraper-admin-display.php';
    }

/**
 * Display the zones management page.
 *
 * @since    1.1.0
 */
public function display_zones_page() {
    require_once 'partials/idealista-scraper-admin-zones-display.php';
}

/**
 * Display the dashboard page.
 *
 * @since    1.1.0
 */
public function display_dashboard_page() {
    require_once 'partials/idealista-scraper-admin-dashboard-display.php';
}

    /**
     * Register the settings for the plugin.
     *
     * @since    1.0.0
     */
    public function register_settings() {
        // API URL Setting
        register_setting(
            'idealista_scraper_options',
            'idealista_scraper_api_url',
            array(
                'type' => 'string',
                'sanitize_callback' => 'esc_url_raw',
            )
        );

        add_settings_section(
            'idealista_scraper_api_settings_section',
            'API Settings',
            array( $this, 'api_settings_section_callback' ),
            'idealista-scraper-options'
        );

        add_settings_field(
            'idealista_scraper_api_url_field',
            'API URL',
            array( $this, 'api_url_field_callback' ),
            'idealista-scraper-options',
            'idealista_scraper_api_settings_section'
        );

        // Scraper Speed Settings
        add_settings_section(
            'idealista_scraper_speed_settings_section',
            'Scraper Speed Settings',
            array( $this, 'speed_settings_section_callback' ),
            'idealista-scraper-speed'
        );

        register_setting(
            'idealista_scraper_speed',
            'idealista_scraper_scraping_intensity',
            array(
                'type' => 'string',
                'sanitize_callback' => array($this, 'sanitize_scraping_intensity'),
            )
        );

        add_settings_field(
            'idealista_scraper_scraping_intensity_field',
            'Scraping Intensity',
            array( $this, 'scraping_intensity_field_callback' ),
            'idealista-scraper-speed',
            'idealista_scraper_speed_settings_section'
        );

        // Advanced Settings
        add_settings_section(
            'idealista_scraper_advanced_settings_section',
            'Advanced Settings',
            array( $this, 'advanced_settings_section_callback' ),
            'idealista-scraper-advanced'
        );

        register_setting(
            'idealista_scraper_advanced',
            'idealista_scraper_proxy_list',
            array(
                'type' => 'string',
                'sanitize_callback' => array($this, 'sanitize_textarea'),
            )
        );

        add_settings_field(
            'idealista_scraper_proxy_list_field',
            'Proxy List',
            array( $this, 'proxy_list_field_callback' ),
            'idealista-scraper-advanced',
            'idealista_scraper_advanced_settings_section'
        );

        register_setting(
            'idealista_scraper_advanced',
            'idealista_scraper_user_agent_list',
            array(
                'type' => 'string',
                'sanitize_callback' => array($this, 'sanitize_textarea'),
            )
        );

        add_settings_field(
            'idealista_scraper_user_agent_list_field',
            'User-Agent List',
            array( $this, 'user_agent_list_field_callback' ),
            'idealista-scraper-advanced',
            'idealista_scraper_advanced_settings_section'
        );
    }

    /**
     * Sanitize scraping intensity dropdown.
     */
    public function sanitize_scraping_intensity($input) {
        $allowed_values = array('slow', 'moderate', 'fast');
        if (in_array($input, $allowed_values, true)) {
            return $input;
        }
        return 'moderate'; // Default value
    }

    /**
     * Sanitize textarea fields, one line at a time.
     */
    public function sanitize_textarea($input) {
        $lines = explode("\n", $input);
        $sanitized_lines = array_map('sanitize_text_field', $lines);
        return implode("\n", $sanitized_lines);
    }


    /**
     * Callback for the API settings section.
     */
    public function api_settings_section_callback() {
        echo '<p>Enter the URL of the Idealista Scraper API.</p>';
    }

    /**
     * Callback for the API URL field.
     */
    public function api_url_field_callback() {
        $api_url = get_option('idealista_scraper_api_url');
        echo '<input type="text" id="idealista_scraper_api_url" name="idealista_scraper_api_url" value="' . esc_attr($api_url) . '" class="regular-text" />';
    }

    /**
     * Callback for the speed settings section.
     */
    public function speed_settings_section_callback() {
        echo '<p>Control the speed and intensity of the scraper. "Slow and Safe" is recommended to avoid getting blocked.</p>';
    }

    /**
     * Callback for the scraping intensity field.
     */
    public function scraping_intensity_field_callback() {
        $intensity = get_option('idealista_scraper_scraping_intensity', 'moderate');
        ?>
        <select name="idealista_scraper_scraping_intensity" id="idealista_scraper_scraping_intensity">
            <option value="slow" <?php selected($intensity, 'slow'); ?>>Slow and Safe</option>
            <option value="moderate" <?php selected($intensity, 'moderate'); ?>>Moderate</option>
            <option value="fast" <?php selected($intensity, 'fast'); ?>>Fast (Not Recommended)</option>
        </select>
        <?php
    }

    /**
     * Callback for the advanced settings section.
     */
    public function advanced_settings_section_callback() {
        echo '<p>Configure advanced options like proxies and user agents.</p>';
    }

    /**
     * Callback for the proxy list field.
     */
    public function proxy_list_field_callback() {
        $proxy_list = get_option('idealista_scraper_proxy_list', '');
        echo '<textarea id="idealista_scraper_proxy_list" name="idealista_scraper_proxy_list" rows="5" class="large-text">' . esc_textarea($proxy_list) . '</textarea>';
        echo '<p class="description">Enter one proxy per line, e.g., <code>123.45.67.89:8080</code>.</p>';
    }

    /**
     * Callback for the user-agent list field.
     */
    public function user_agent_list_field_callback() {
        $user_agent_list = get_option('idealista_scraper_user_agent_list', '');
        echo '<textarea id="idealista_scraper_user_agent_list" name="idealista_scraper_user_agent_list" rows="5" class="large-text">' . esc_textarea($user_agent_list) . '</textarea>';
        echo '<p class="description">Enter one user-agent string per line. These will be rotated during scraping.</p>';
    }

    /**
     * Start the scraping process.
     *
     * @since    1.0.0
     */
    public function start_scraping() {
        // Security check
        check_ajax_referer('idealista_scraper_start_scraping', 'security');

        $api_url = get_option('idealista_scraper_api_url');
        if (empty($api_url)) {
            wp_send_json_error('API URL is not configured.');
        }

        $response = wp_remote_post($api_url . '/api/scrape/start', array(
            'method'    => 'POST',
            'timeout'   => 45,
            'blocking'  => true,
        ));

        if (is_wp_error($response)) {
            wp_send_json_error($response->get_error_message());
        }

        $body = wp_remote_retrieve_body($response);
        $data = json_decode($body, true);

        wp_send_json_success($data);
    }

    /**
     * Get the scraped data.
     *
     * @since    1.0.0
     */
    public function get_scraped_data() {
        $api_url = get_option('idealista_scraper_api_url');
        if (empty($api_url)) {
            wp_send_json_error('API URL is not configured.');
        }

        $response = wp_remote_get($api_url . '/api/properties');

        if (is_wp_error($response)) {
            wp_send_json_error($response->get_error_message());
        }

        $body = wp_remote_retrieve_body($response);
        $data = json_decode($body, true);

        wp_send_json_success($data);
    }

    /**
     * Get the scraping status.
     *
     * @since    1.0.0
     */
    public function get_scraping_status() {
        $api_url = get_option('idealista_scraper_api_url');
        if (empty($api_url)) {
            wp_send_json_error('API URL is not configured.');
        }

        $response = wp_remote_get($api_url . '/api/scraping-sessions');

        if (is_wp_error($response)) {
            wp_send_json_error($response->get_error_message());
        }

        $body = wp_remote_retrieve_body($response);
        $data = json_decode($body, true);

        wp_send_json_success($data);
    }

    /**
     * Solve the captcha.
     *
     * @since    1.0.0
     */
    public function solve_captcha() {
        // Security check
        check_ajax_referer('idealista_scraper_solve_captcha', 'security');

        $api_url = get_option('idealista_scraper_api_url');
        if (empty($api_url)) {
            wp_send_json_error('API URL is not configured.');
        }

        $session_id = sanitize_text_field($_POST['session_id']);
        $solution = sanitize_text_field($_POST['solution']);

        $response = wp_remote_post($api_url . '/api/captcha/' . $session_id . '/solve', array(
            'method'    => 'POST',
            'timeout'   => 45,
            'blocking'  => true,
            'body'      => json_encode(array('solution' => $solution)),
            'headers'   => array('Content-Type' => 'application/json')
        ));

        if (is_wp_error($response)) {
            wp_send_json_error($response->get_error_message());
        }

        $body = wp_remote_retrieve_body($response);
        $data = json_decode($body, true);

        wp_send_json_success($data);
    }

    /**
     * Get the selected zones for scraping.
     *
     * @since    1.1.0
     */
    public function get_selected_zones() {
        if ( ! current_user_can( 'manage_options' ) ) {
            wp_send_json_error( 'You do not have permission to perform this action.' );
        }

        $selected_zones = get_option('idealista_scraper_selected_zones', array());
        wp_send_json_success($selected_zones);
    }
}
