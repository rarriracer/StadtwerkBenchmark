"""Validate saved research responses and write the candidate topic catalog."""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / 'data' / 'research'
checks = json.loads((RESEARCH / 'api_checks.json').read_text())
sources = {r['source']: r for r in checks}

# Revalidate CSV from the saved original response; no network operation.
rows = list(csv.reader((RESEARCH / 'smard_prices.csv').open(), delimiter=';'))
ids = ['s-mdl_stpr-1-1', 's-mdl_stpr-1-2', 's-ind_stpr-1-1',
       'g-mdl_gspr-1-1', 'g-mdl_gspr-1-2', 's-mdl_dyn_stpr-1-1']
sources['smard_prices']['selected_series'] = {
    series: {'year_counts': {str(y): sum(r[0] == series and r[1].startswith(str(y)) and bool(r[-1])
                                       for r in rows if len(r) > 2)
                            for y in (2024, 2025, 2026)},
             'latest': max(r[1] for r in rows if len(r) > 2 and r[0] == series)}
    for series in ids
}
sources['smard_prices'].pop('error', None)
assert all(r.get('status') == 200 and not r.get('error') for r in checks)
for name in ['energy_capacity', 'energy_price', 'ecb_credit', 'bundesbank_credit',
             'gas_rlm', 'gas_slp', 'kba_nrw', 'kba_bonn_share']:
    assert all(sources[name]['year_counts'][str(y)] > 0 for y in (2024, 2025, 2026)), name
for series, coverage in sources['smard_prices']['selected_series'].items():
    assert all(coverage['year_counts'][str(y)] > 0 for y in (2024, 2025, 2026)), series
for y in (2024, 2025, 2026):
    assert all(v > 0 for v in sources['weather_archive']['non_null_by_year'][str(y)].values())
capacity = json.loads((RESEARCH / 'energy_capacity.json').read_text())
for series in ['solar_dc', 'solar_ac', 'wind_onshore', 'wind_offshore',
               'battery_storage_power', 'battery_storage_capacity']:
    assert all(any(r['timestamp'].startswith(str(y)) and r['values'].get(series) is not None
                   for r in capacity['data']) for y in (2024, 2025, 2026)), series
assert not sources['kba_nrw']['exceeded_transfer_limit']
assert not sources['kba_bonn_share']['exceeded_transfer_limit']

topic_specs = [
 ('pv_capacity', 'Photovoltaik: Ausbau eigener Anlagen', ['energy_capacity'],
  ['PV-Leistung MW/MWp', 'Stichtag', 'Eigentums-/Beteiligungsumfang'],
  'constant_national_capacity_share', ['solar_dc', 'solar_ac'], 'DE', 'MW_DC_or_MW_AC'),
 ('pv_yield', 'Photovoltaik: Stromertrag', ['weather_archive', 'weather_forecast'],
  ['PV-Erzeugung MWh', 'Standort oder expliziter Standort-Proxy'],
  'radiation_sensitivity_with_capacity_assumption', ['shortwave_radiation_sum'], 'plant_coordinates', 'MWh'),
 ('wind_capacity', 'Windenergie: Ausbau eigener Anlagen', ['energy_capacity'],
  ['Windleistung MW', 'onshore/offshore', 'Stichtag', 'Beteiligungsumfang'],
  'constant_national_capacity_share', ['wind_onshore', 'wind_offshore'], 'DE', 'MW'),
 ('battery_capacity', 'Batteriespeicher: Ausbau', ['energy_capacity'],
  ['Speicherleistung MW und/oder Energieinhalt MWh', 'Stichtag'],
  'constant_national_capacity_share', ['battery_storage_power', 'battery_storage_capacity'], 'DE', 'MW_and_MWh_separate'),
 ('electricity_household_prices', 'Stromvertrieb Haushalte: Preis-/Erlösszenario', ['smard_prices'],
  ['Haushaltsabsatz', 'zugehöriger Umsatz oder Preis', 'Abgaben-/Nettobasis'],
  'price_spread_or_ratio_with_separate_volume', ['s-mdl_stpr-1-1', 's-mdl_stpr-1-2'], 'DE', 'ct/kWh'),
 ('electricity_industry_prices', 'Stromvertrieb Industrie: Preis-/Erlösszenario', ['smard_prices'],
  ['Industrieabsatz', 'zugehöriger Umsatz oder Preis', 'Vergünstigungsprofil'],
  'price_spread_or_ratio_with_separate_volume', ['s-ind_stpr-1-1'], 'DE', 'ct/kWh'),
 ('gas_household_prices', 'Gasvertrieb Haushalte: Preis-/Erlösszenario', ['smard_prices'],
  ['Haushaltsgasabsatz', 'zugehöriger Umsatz oder Preis', 'Abgaben-/Nettobasis'],
  'price_spread_or_ratio_with_separate_volume', ['g-mdl_gspr-1-1', 'g-mdl_gspr-1-2'], 'DE', 'ct/kWh'),
 ('gas_slp_volume', 'Gasabsatz Haushalte und kleines Gewerbe', ['gas_slp'],
  ['SLP-Gasabsatz MWh/GWh', 'Geschäftsjahr', 'Gebiet'],
  'constant_national_segment_share', ['2024', '2025', '2026'], 'DE', 'GWh/day_weekly_mean'),
 ('gas_rlm_volume', 'Gasabsatz Industrie und größere Verbraucher', ['gas_rlm'],
  ['RLM-Gasabsatz MWh/GWh', 'Geschäftsjahr', 'Branchenmix'],
  'constant_national_segment_share', ['2024', '2025', '2026'], 'DE', 'GWh/day_weekly_mean'),
 ('heat_weather', 'Fernwärme: wetterabhängiger Absatz', ['weather_archive', 'weather_forecast'],
  ['Wärmeabsatz MWh', 'Gebiet'],
  'heating_degree_day_proxy_with_base_load', ['temperature_2m_mean'], 'service_area_coordinates', 'MWh'),
 ('electricity_spot_exposure', 'Strombeschaffung: Marktpreisexposition', ['energy_price'],
  ['Beschaffungs-/Erzeugungsmenge', 'offener Anteil als belegter Wert oder explizite Annahme'],
  'unhedged_volume_price_sensitivity', ['day_ahead_price'], 'DE-LU', 'EUR/MWh'),
 ('financing', 'Finanzierung: Zinsbelastung', ['bundesbank_credit', 'ecb_credit'],
  ['Finanzschulden', 'Zinsaufwand', 'variable/refinanzierte Schulden als Wert oder Annahme'],
  'repriced_debt_interest_sensitivity', ['M.DE.B.A2A.D.R.1.2240.EUR.N'], 'DE', 'percent_per_annum'),
 ('ev_market', 'E-Mobilität: regionales Marktpotenzial', ['kba_nrw', 'kba_bonn_share'],
  ['Ladegeschäft im Bericht', 'Gebiet'],
  'market_context_then_explicit_utilisation_assumptions', ['Pkw_BEV', 'Pkw_Elektro_Anteil'],
  'NRW_counts_Bonn_share_verified', 'count_and_percent_separate'),
]
fields = ['id', 'label', 'sources', 'required_report_fields', 'scenario_method',
          'reference_series', 'verified_geography', 'metric_unit']
topics = [dict(zip(fields, row), status='sources_verified_report_gate_required') for row in topic_specs]
# The selected MVP requires a compatible baseline ratio, not just an available API.
for topic in topics:
    topic['required_reference_gate'] = 'compatible_definition_unit_scope_and_period'
    topic['primary_mvp_formula'] = 'U_basis * R_target / R_basis'
    if topic['id'] in ('pv_yield', 'heat_weather', 'ev_market'):
        topic['direct_ratio_contract_status'] = 'pending_matching_reference_metric'
        topic['menu_enabled_by_source_check_alone'] = False
    elif topic['id'] in ('electricity_household_prices', 'electricity_industry_prices',
                         'gas_household_prices', 'electricity_spot_exposure', 'financing'):
        topic['direct_ratio_contract_status'] = 'conditional_comparable_price_or_rate'
        topic['menu_enabled_by_source_check_alone'] = False
    else:
        topic['direct_ratio_contract_status'] = 'candidate_matching_capacity_or_volume'
        topic['menu_enabled_by_source_check_alone'] = False
keep = ['url', 'status', 'retrieved_at', 'sha256', 'year_counts', 'non_null_by_year',
        'available_until', 'selected_series', 'last_available_week']
catalog = {
 'schema_version': 1, 'research_date': '2026-10-06', 'implementation_status': 'research_only',
 'documentation': 'docs/API_QUELLEN.md',
 'eligibility_rules': [
  'Require valid reference observations in 2024, 2025 and 2026, not HTTP success alone.',
  'Evaluate nulls, provisional observations and provider status flags.',
  'Show only topics with compatible evidenced report KPIs, periods, units and entity scope.',
  'Check regional availability at runtime; NRW/Bonn are examples, not guarantees for every municipality.',
  'Separate observed references, estimated company numbers and assumed remaining-year development.',
  'One annual observation cannot establish a trained forecast or statistically calibrated interval.'
 ],
 'sources': {name: {k: r[k] for k in keep if k in r} for name, r in sources.items()
             if name not in ('energy_schema', 'kba_regions')},
 'topics': topics,
 'blocked_topics': [
  {'id': 'regional_pv_registry', 'reason': 'MaStR access and historical completeness/ownership not verified.'},
  {'id': 'public_chargepoint_history', 'reason': 'Exact public endpoint and compatible 2024/2025 snapshots not tested.'},
  {'id': 'local_network_tariffs', 'reason': 'No universal tested supplier-specific interface with all three years.'},
  {'id': 'customer_pv_installation_count', 'reason': 'Registry plant stock differs from supplier installation sales.'},
  {'id': 'live_supplier_profit_or_customer_count', 'reason': 'No universal public historic/current company API verified.'},
  {'id': 'water_waste_transport', 'reason': 'No cross-provider historic/current interface verified in this research.'}
 ]
}
(RESEARCH / 'api_checks.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2) + '\n')
(ROOT / 'data' / 'reference_catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
print('Validated 13 public responses; wrote 13 topic candidates with report gates.')
