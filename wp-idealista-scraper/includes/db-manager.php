<?php

if (!defined('ABSPATH')) {
    exit; // Exit if accessed directly
}

class Idealista_Scraper_DB_Manager {
    public static function create_table() {
        global $wpdb;
        $table_name = $wpdb->prefix . 'idealista_prices';
        $charset_collate = $wpdb->get_charset_collate();

        // Need to require this file as it's not always available
        require_once(ABSPATH . 'wp-admin/includes/upgrade.php');

        $sql = "CREATE TABLE $table_name (
            id mediumint(9) NOT NULL AUTO_INCREMENT,
            property_url varchar(255) DEFAULT '' NOT NULL,
            price float DEFAULT 0 NOT NULL,
            property_type varchar(50) DEFAULT '' NOT NULL,
            transaction_type varchar(50) DEFAULT '' NOT NULL,
            scraped_at datetime DEFAULT '0000-00-00 00:00:00' NOT NULL,
            PRIMARY KEY  (id)
        ) $charset_collate;";

        dbDelta($sql);
    }
}
