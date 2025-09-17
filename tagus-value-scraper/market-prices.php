<?php
/**
 * Market Prices Data
 * Defines the hierarchical structure of Distritos, Concelhos, and Freguesias for the Tagus Value Price Scraper.
 */

if (!function_exists('tagus_value_get_market_data')) {
    function tagus_value_get_market_data() {
        return array(
            'faro' => array(
                'name' => 'Faro',
                'tavira' => array(
                    'name' => 'Tavira',
                    'freguesias' => array(
                        'tavira' => array('name' => 'Tavira'),
                        'conceicao-e-cabanas-de-tavira' => array('name' => 'Conceição e Cabanas de Tavira'),
                        'santa-maria-tavira' => array('name' => 'Santa Maria Tavira'),
                        'santa-luzia' => array('name' => 'Santa Luzia'),
                    ),
                ),
                'olhao' => array(
                    'name' => 'Olhão',
                    'freguesias' => array(
                        'pechao' => array('name' => 'Pechão'),
                        'olhao' => array('name' => 'Olhão'),
                        'quelfes' => array('name' => 'Quelfes'),
                        'moncarapacho-e-fuseta' => array('name' => 'Moncarapacho e Fuseta'),
                    ),
                ),
                'faro' => array(
                    'name' => 'Faro',
                    'freguesias' => array(
                        'faro-se-e-sao-pedro' => array('name' => 'Faro (Sé e São Pedro)'),
                        'montenegro' => array('name' => 'Montenegro'),
                    ),
                ),
            ),
            'lisboa' => array(
                'name' => 'Lisboa',
                'lisboa' => array(
                    'name' => 'Lisboa',
                    'freguesias' => array(
                        'alcantara' => array('name' => 'Alcântara'),
                        'belem' => array('name' => 'Belém'),
                    ),
                ),
                'cascais' => array(
                    'name' => 'Cascais',
                    'freguesias' => array(
                        'cascais-e-estoril' => array('name' => 'Cascais e Estoril'),
                        'alcabideche' => array('name' => 'Alcabideche'),
                        'carcavelos-e-parede' => array('name' => 'Carcavelos e Parede'),
                        'sao-domingos-de-rana' => array('name' => 'São Domingos de Rana'),
                    ),
                ),
            ),
            // Add more Distritos (e.g., Porto, Aveiro, etc.)
        );
    }
}
?>