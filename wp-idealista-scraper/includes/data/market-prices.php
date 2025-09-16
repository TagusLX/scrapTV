
<?php
/**
 * Market prices data for Portugal
 * Last update 16-09-2025 (16:30)
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

/**
 * Get market data for Portuguese real estate
 *
 * @return array Market data by region
 */
function tagus_value_get_market_data() {
    return [
        'Faro' => [
            'name' => 'Faro',
            'average' => 0,
            'average_rent' => 0,
            'freguesias' => [
                'Tavira' => [
                    'name' => 'Tavira',
                    'average' => 0,
                    'average_rent' => 0,
                    'freguesias' => [
                        'Conceição e Cabanas de Tavira' => [
                            'name' => 'Conceição e Cabanas de Tavira',
                            'average' => 0,
                            'average_rent' => 0,
                        ],
                    ],
                ],
            ],
        ],
    ];
}
