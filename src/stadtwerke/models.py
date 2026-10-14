from typing import Literal
from pydantic import BaseModel, Field

Metric = Literal['pv_capacity_dc','pv_capacity_ac','pv_generation','wind_onshore',
                 'wind_offshore','battery_power','battery_energy','electricity_sales_total',
                 'electricity_sales_households','electricity_sales_industry','gas_sales_total',
                 'gas_sales_slp','gas_sales_rlm','heat_sales','charge_points','charging_energy',
                 'debt','interest_expense','revenue','electricity_market_share','gas_market_share','electricity_customers','gas_customers','water_customers',
                 'heat_customers','water_sales','electricity_operating_volume','gas_operating_volume',
                 'water_operating_volume','heat_operating_volume','electricity_network_input','electricity_network_renewable_input','gas_network_input','heat_network_input','water_network_input','electricity_network_output','gas_network_output','electricity_peak_load','heat_peak_load','gas_network_max_power','heat_cold_sales','heat_contracting_sales','ebit','ebitda','ebt','equity','balance_total','operating_cashflow','investments','employees','employees_fte','apprentices','personnel_expense','funds_from_operations','dynamic_debt_ratio','net_debt_multiple','gearing_ratio','wastewater_volume','sewage_sludge_volume','electricity_generation','heat_generation','net_income','electricity_network_connections','electricity_network_meters','electricity_network_length','gas_network_connections','gas_network_meters','gas_network_length','heat_network_connections','heat_network_meters','heat_network_length','water_network_connections','water_network_meters','water_network_length']

class Candidate(BaseModel):
    metric: Metric
    raw_value: str = Field(description='Zahl exakt wie im PDF, ohne Einheit')
    raw_unit: str = Field(description='Originaleinheit inklusive k/M/G oder Mio.')
    year: int
    evidence: str = Field(max_length=500, description='Kurzer zusammenhängender Originalausschnitt mit Zahl und Kontext, höchstens 500 Zeichen')
    scope: Literal['own','group','reported_portfolio','network_area','customers','unknown']
    basis: Literal['stock','annual_generation','annual_sales','annual_revenue','annual_expense','annual_volume','planned','additions','unknown']
    portfolio: Literal['total','defined_subset','project','unknown'] = 'unknown'
    entity: str = Field(default='', description='Unternehmen oder Tochter, deren Wert dies ist')
    geography: Literal['DE','other','mixed','unknown'] = 'unknown'
    notes: str = Field(default='', max_length=200)

class PageExtraction(BaseModel):
    company: str = ''
    report_year: int | None = None
    observations: list[Candidate] = Field(default_factory=list)

class Selection(BaseModel):
    metrics: list[str] = Field(min_length=1)
    target_year: int = Field(ge=2024, le=2100)
    spread: float = Field(default=0, ge=0, le=0.5)
    assumptions: dict[str, dict] = Field(default_factory=dict)


class FactClassification(BaseModel):
    id: int = Field(ge=0)
    metric: Metric | None = None
    scope: Literal['own','group','reported_portfolio','network_area','customers','unknown'] = 'unknown'
    basis: Literal['stock','annual_generation','annual_sales','annual_revenue','annual_expense','annual_volume','planned','additions','unknown'] = 'unknown'
    portfolio: Literal['total','defined_subset','project','unknown'] = 'unknown'
    geography: Literal['DE','other','mixed','unknown'] = 'unknown'
    entity: str = Field(default='',max_length=100)

class FactClassifications(BaseModel):
    classifications: list[FactClassification] = Field(default_factory=list,max_length=4)
