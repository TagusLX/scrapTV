<?php

if (!defined('ABSPATH')) exit;

function tagus_value_generate_slug_for_data($text) {
    $text = iconv('UTF-8', 'ASCII//TRANSLIT', $text);
    $text = strtolower($text);
    $text = preg_replace('/[^a-z0-9\-]+/', '-', $text);
    $text = preg_replace('/-+/', '-', $text);
    $text = trim($text, '-');
    return empty($text) ? 'n-a' : $text;
}

function tagus_value_get_location_skeleton() {
    $data = [];
    $file_path = plugin_dir_path(__FILE__) . 'locations.tsv';
    if (!file_exists($file_path)) return [];

    $bedroom_types = ['t0', 't1', 't2', 't3', 't4-t5'];
    $property_types = ['apartamentos', 'moradias'];
    $price_template = ['average' => null, 'average_rent' => null, 'url_sale' => '', 'url_rent' => ''];

    $handle = fopen($file_path, 'r');
    if (!$handle) return [];

    fgetcsv($handle, 0, "\t"); // Skip header

    while (($row = fgetcsv($handle, 0, "\t")) !== FALSE) {
        if (count($row) < 3) continue;

        list($distrito_name, $concelho_name, $freguesia_raw_name) = array_map('trim', $row);

        $freguesia_name = str_starts_with($freguesia_raw_name, 'União das freguesias de ')
                        ? substr($freguesia_raw_name, strlen('União das freguesias de '))
                        : $freguesia_raw_name;

        $distrito_slug = tagus_value_generate_slug_for_data($distrito_name);
        $concelho_slug = tagus_value_generate_slug_for_data($concelho_name);
        $freguesia_slug = tagus_value_generate_slug_for_data($freguesia_name);

        if (!isset($data[$distrito_slug])) {
            $data[$distrito_slug] = array_merge(['name' => $distrito_name], $price_template);
            $data[$distrito_slug]['concelhos'] = [];
        }
        if (!isset($data[$distrito_slug]['concelhos'][$concelho_slug])) {
            $data[$distrito_slug]['concelhos'][$concelho_slug] = array_merge(['name' => $concelho_name], $price_template, ['freguesias' => []]);
        }
        if (!isset($data[$distrito_slug]['concelhos'][$concelho_slug]['freguesias'][$freguesia_slug])) {
            $freguesia_data = array_merge(['name' => $freguesia_name], $price_template, ['types' => []]);
            foreach ($property_types as $prop_type) {
                $freguesia_data['types'][$prop_type] = [];
                foreach ($bedroom_types as $bed_type) {
                    if ($prop_type === 'moradias' && $bed_type === 't0') continue;
                    $freguesia_data['types'][$prop_type][$bed_type] = $price_template;
                }
            }
            $data[$distrito_slug]['concelhos'][$concelho_slug]['freguesias'][$freguesia_slug] = $freguesia_data;
        }
    }
    fclose($handle);
    return $data;
}
?>
