<?php
/**
 * Provide a admin area view for the plugin
 *
 * This file is used to markup the admin-facing aspects of the plugin.
 *
 * @link       https://example.com/
 * @since      1.0.0
 *
 * @package    Idealista_Scraper
 * @subpackage Idealista_Scraper/admin/partials
 */
?>

<div class="wrap">
    <h1><?php echo esc_html(get_admin_page_title()); ?></h1>

    <form method="post" action="options.php">
        <?php
        settings_fields('idealista_scraper_options');
        do_settings_sections('idealista-scraper-options');
        submit_button();
        ?>
    </form>

    <div id="scraper-dashboard">
        <h2>Scraper Dashboard</h2>
        <button id="start-scraping" class="button button-primary">Start New Scraping Session</button>
        <div id="scraping-status"></div>
    </div>

    <div id="captcha-solver" style="display:none;">
        <h2>CAPTCHA Required</h2>
        <p>A CAPTCHA is required to continue scraping. Please solve the CAPTCHA below.</p>
        <img id="captcha-image" src="" alt="CAPTCHA Image" />
        <input type="text" id="captcha-solution" placeholder="Enter CAPTCHA solution" />
        <button id="submit-captcha" class.php="button button-primary">Submit Solution</button>
        <input type="hidden" id="captcha-session-id" value="" />
    </div>

    <div id="scraped-data">
        <h2>Scraped Data</h2>
        <div id="scraped-data-container"></div>
    </div>
</div>
