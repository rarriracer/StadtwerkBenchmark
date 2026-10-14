from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / 'data' / 'runtime'
OUTPUTS = ROOT / 'outputs'
MODEL = os.environ.get('STADTWERKE_MODEL', 'qwen2.5:3b')
OLLAMA_URL = os.environ.get('STADTWERKE_OLLAMA_URL', 'http://127.0.0.1:11434')
for directory in (RUNTIME, OUTPUTS, ROOT / 'data' / 'raw'):
    directory.mkdir(parents=True, exist_ok=True)

# Only same-dimension, tested capacity references are enabled initially.
CAPACITY_TOPICS = {
    'pv_capacity_dc': ('Photovoltaik-Ausbau', 'solar_dc', 'MWp'),
    'pv_capacity_ac': ('Photovoltaik-Ausbau (AC)', 'solar_ac', 'MW'),
    'wind_onshore': ('Windenergie-Ausbau an Land', 'wind_onshore', 'MW'),
    'wind_offshore': ('Windenergie-Ausbau auf See', 'wind_offshore', 'MW'),
    'battery_power': ('Batteriespeicher-Leistung', 'battery_storage_power', 'MW'),
    'battery_energy': ('Batteriespeicher-Energieinhalt', 'battery_storage_capacity', 'MWh'),
}

METRIC_LABELS = {key: value[0] for key, value in CAPACITY_TOPICS.items()} | {
    'pv_generation': 'Photovoltaik-Stromertrag', 'electricity_sales_total': 'Stromabsatz gesamt',
    'electricity_sales_households': 'Stromabsatz an Haushalte',
    'electricity_sales_industry': 'Stromabsatz an Industrie', 'gas_sales_total': 'Gasabsatz gesamt',
    'gas_sales_slp': 'Gasabsatz mit Standardlastprofil', 'gas_sales_rlm': 'Gasabsatz mit Leistungsmessung',
    'heat_sales': 'Wärmeabsatz', 'charge_points': 'Ladepunkte', 'charging_energy': 'Ladestrom',
    'debt': 'Finanzschulden', 'interest_expense': 'Zinsaufwand', 'revenue': 'Umsatz',
    'electricity_market_share': 'Marktanteil Strom', 'gas_market_share': 'Marktanteil Gas',
    'electricity_customers': 'Kundenanzahl Strom', 'gas_customers': 'Kundenanzahl Gas',
    'water_customers': 'Kundenanzahl Wasser', 'heat_customers': 'Kundenanzahl Wärme',
    'water_sales': 'Wasserabsatz', 'electricity_operating_volume': 'Betriebsmenge Strom',
    'gas_operating_volume': 'Betriebsmenge Gas', 'water_operating_volume': 'Betriebsmenge Wasser',
    'heat_operating_volume': 'Betriebsmenge Wärme',
    'electricity_network_input': 'Netzeinspeisung Strom',
    'electricity_network_renewable_input': 'Netzeinspeisung erneuerbarer Strom',
    'gas_network_input': 'Netzeinspeisung Gas',
    'heat_network_input': 'Netzeinspeisung Wärme',
    'water_network_input': 'Netzeinspeisung Wasser',
    'electricity_network_output': 'Netzausspeisung Strom',
    'gas_network_output': 'Netzausspeisung Gas',
    'electricity_peak_load': 'Höchstlast Strom',
    'heat_peak_load': 'Höchstlast Wärme',
    'gas_network_max_power': 'Maximale Einspeiseleistung Gas',
    'heat_cold_sales': 'Wärme-/Kälteabsatz',
    'heat_contracting_sales': 'Wärmecontracting-Absatz',
    'ebit': 'EBIT',
    'ebitda': 'EBITDA',
    'ebt': 'Ergebnis vor Steuern',
    'equity': 'Eigenkapital',
    'balance_total': 'Bilanzsumme',
    'operating_cashflow': 'Operativer Cashflow',
    'investments': 'Investitionen',
    'employees': 'Mitarbeiteranzahl',
    'apprentices': 'Auszubildende',
    'personnel_expense': 'Personalaufwand',
    'funds_from_operations': 'Funds from Operations (FFO)',
    'dynamic_debt_ratio': 'Dynamischer Verschuldungsgrad',
    'net_debt_multiple': 'Nettoverschuldungsgrad',
    'gearing_ratio': 'Gearing Ratio',
    'wastewater_volume': 'Verwertete Abwassermenge',
    'sewage_sludge_volume': 'Verwertete Klärschlammmenge',
    'electricity_network_connections': 'Netzanschlüsse Strom',
    'electricity_network_meters': 'Zähler im Netz Strom',
    'electricity_network_length': 'Netzlänge Strom',
    'gas_network_connections': 'Netzanschlüsse Gas',
    'gas_network_meters': 'Zähler im Netz Gas',
    'electricity_generation': 'Stromerzeugung gesamt',
    'heat_generation': 'Wärmeerzeugung gesamt',
    'net_income': 'Jahresüberschuss',
    'employees_fte': 'Beschäftigte in Vollzeitäquivalenten',
    'gas_network_length': 'Netzlänge Gas',
    'heat_network_connections': 'Netzanschlüsse Wärme',
    'heat_network_meters': 'Zähler im Netz Wärme',
    'heat_network_length': 'Netzlänge Wärme',
    'water_network_connections': 'Netzanschlüsse Wasser',
    'water_network_meters': 'Zähler im Netz Wasser',
    'water_network_length': 'Netzlänge Wasser',
}

# A connected reference may be a volume benchmark or contextual driver.
# Context references never produce an automatic company forecast.
REFERENCE_TOPICS = {
    'electricity_sales_total': ('Stromabsatz / Verbrauchsreferenz', 'annual_sales', 'MWh', 'flow'),
    'electricity_sales_households': ('Stromvertrieb Haushalte / Preisreferenz', 'annual_sales', 'MWh', 'context'),
    'electricity_sales_industry': ('Stromvertrieb Industrie / Preisreferenz', 'annual_sales', 'MWh', 'context'),
    'gas_sales_total': ('Gasabsatz / Verbrauchsreferenz', 'annual_sales', 'MWh', 'flow'),
    'gas_sales_slp': ('Gasabsatz SLP / Verbrauchsreferenz', 'annual_sales', 'MWh', 'flow'),
    'gas_sales_rlm': ('Gasabsatz RLM / Verbrauchsreferenz', 'annual_sales', 'MWh', 'flow'),
    'heat_sales': ('Fernwärmeabsatz / Witterungsreferenz', 'annual_sales', 'MWh', 'context'),
    'pv_generation': ('Photovoltaik-Stromertrag / Erzeugungsreferenz', 'annual_generation', 'MWh', 'flow'),
    'charge_points': ('Ladeinfrastruktur / Fahrzeugmarkt', 'stock', 'Anzahl', 'context'),
    'charging_energy': ('Ladestrom / Fahrzeugmarkt', 'annual_sales', 'MWh', 'context'),
    'debt': ('Finanzierung / Kreditzinsreferenz', 'stock', 'EUR', 'context'),
    'interest_expense': ('Zinsaufwand / Kreditzinsreferenz', 'annual_expense', 'EUR', 'context'),
}

# Added reference families: retain company figures, compare external drivers.
WATER_PRICE_METRICS={'water_sales','water_operating_volume','water_network_input','wastewater_volume'}
ENERGY_MARKET_METRICS={'electricity_generation','revenue','ebit','ebitda','ebt','net_income','funds_from_operations','operating_cashflow'}
FINANCIAL_RATE_METRICS={'investments','equity','balance_total','dynamic_debt_ratio','net_debt_multiple','gearing_ratio'}
for metric in sorted(WATER_PRICE_METRICS):
    REFERENCE_TOPICS[metric]=(METRIC_LABELS[metric]+' / '+('Abwasserpreisreferenz' if metric=='wastewater_volume' else 'Wasserpreisreferenz'),
        'annual_sales' if metric=='water_sales' else 'annual_volume','m³','context')
for metric in sorted(ENERGY_MARKET_METRICS):
    REFERENCE_TOPICS[metric]=(METRIC_LABELS[metric]+' / Strommarktpreisreferenz',
        'annual_generation' if metric=='electricity_generation' else 'annual_revenue','MWh' if metric=='electricity_generation' else 'EUR','context')
for metric in sorted(FINANCIAL_RATE_METRICS):
    unit='%' if metric in ('dynamic_debt_ratio','gearing_ratio') else 'Faktor' if metric=='net_debt_multiple' else 'EUR'
    REFERENCE_TOPICS[metric]=(METRIC_LABELS[metric]+' / Finanzierungsumfeld',
        'annual_revenue' if metric=='investments' else 'stock',unit,'context')
