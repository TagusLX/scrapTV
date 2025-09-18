<?php
/**
 * Plugin Name: Tagus Value Price Scraper
 * Plugin URI: https://tagusvalue.com
 * Description: WordPress plugin to scrape average prices per m² from Idealista.
 * Version: 2.0.0
 * Author: Jules
 * License: GPL v2 or later
 * Text Domain: tagus-value-scraper
 */

if (!defined('ABSPATH')) exit;

// Include core plugin files
require_once plugin_dir_path(__FILE__) . 'data-structure.php';
require_once plugin_dir_path(__FILE__) . 'url-generator.php';
require_once plugin_dir_path(__FILE__) . 'file-generator.php';
require_once plugin_dir_path(__FILE__) . 'admin-ui.php';
require_once plugin_dir_path(__FILE__) . 'actions.php';

// All functionality is loaded from included files.
?>