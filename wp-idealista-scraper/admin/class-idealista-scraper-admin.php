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

    }

    /**
     * Register the stylesheets for the admin area.
     *
     * @since    1.0.0
     */
    public function enqueue_styles() {

        wp_enqueue_style( $this->plugin_name, plugin_dir_url( __FILE__ ) . 'css/idealista-scraper-admin.css', array(), $this->version, 'all' );

    }

    /**
     * Register the JavaScript for the admin area.
     *
     * @since    1.0.0
     */
    public function enqueue_scripts() {

        wp_enqueue_script( $this->plugin_name, plugin_dir_url( __FILE__ ) . 'js/idealista-scraper-admin.js', array( 'jquery' ), $this->version, false );

        // Pass ajax url and nonces to the script
        wp_localize_script( $this->plugin_name, 'idealista_scraper_ajax', array(
            'ajax_url' => admin_url( 'admin-ajax.php' ),
            'api_url' => get_option('idealista_scraper_api_url'),
            'start_scraping_nonce' => wp_create_nonce('idealista_scraper_start_scraping'),
            'solve_captcha_nonce' => wp_create_nonce('idealista_scraper_solve_captcha'),
        ) );
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
    }

    /**
     * Display the admin page.
     *
     * @since    1.0.0
     */
    public function display_plugin_setup_page() {
        require_once 'partials/idealista-scraper-admin-display.php';
    }

    /**
     * Register the settings for the plugin.
     *
     * @since    1.0.0
     */
    public function register_settings() {
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
    }

    /**
     * Callback for the API settings section.
     *
     * @since    1.0.0
     */
    public function api_settings_section_callback() {
        echo '<p>Enter the URL of the Idealista Scraper API.</p>';
    }

    /**
     * Callback for the API URL field.
     *
     * @since    1.0.0
     */
    public function api_url_field_callback() {
        $api_url = get_option('idealista_scraper_api_url');
        echo '<input type="text" id="idealista_scraper_api_url" name="idealista_scraper_api_url" value="' . esc_attr($api_url) . '" class="regular-text" />';
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
}
