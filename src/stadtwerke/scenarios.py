"""Explicit enterprise exposures; external drivers never scale total profits."""
import math
from datetime import date

# Each scenario requires one unambiguous original company observation.
DEFINITIONS = {
    'interest': ('Finanzierung · Zinswirkung auf betroffene Kredite', ('debt',), 'EUR',
        [('amount','Betroffene Kreditsumme (EUR)',None),('months','Dauer der Zinswirkung (Monate)',12)],
        'Die angegebene Summe betrifft neue/refinanzierte EUR-Unternehmenskredite über 1 Mio. EUR mit variabler Verzinsung oder Zinsbindung bis drei Monate. Sie ist Teil der belegten Finanzschulden. Kreditmarge und Sicherungen bleiben unverändert; die Änderung des Referenzzinses wird vollständig weitergegeben.'),
    'heat': ('Wärme · witterungsabhängiger Absatz', ('heat_sales',), 'MWh',
        [('amount','Eigener Wärmeabsatz in den historischen Vergleichsmonaten (MWh)',None),('coupling','Witterungsabhängiger Anteil (0 bis 1)',1)],
        'Die eingegebene Wärme stammt aus demselben Unternehmensumfang und exakt den unten genannten historischen Vergleichsmonaten. Der übrige Absatz bleibt konstant; Netz und Kundenbestand werden als unverändert angenommen.'),
    'water': ('Wasser · eigenes Tarifszenario', ('water_sales',), 'm³',
        [('amount','Eigene Menge in den historischen Vergleichsmonaten (m³)',None),('price','Eigener Ausgangstarif (EUR/m³)',None),('coupling','Angenommene Tarifweitergabe (0 bis 1)',1)],
        'Menge und Tarif beziehen sich auf dieselben Haushaltskunden und historischen Vergleichsmonate. Preisbestandteile, Steuern und Leistungsumfang passen zum Verbraucherpreisindex; Grundgebühren sind nicht enthalten. Die Menge bleibt konstant.'),
    'retail_households': ('Strom Haushalte · eigenes Tarifszenario', ('electricity_sales_households',), 'MWh',
        [('amount','Eigene Haushaltsmenge in den historischen Vergleichsmonaten (MWh)',None),('price','Eigener Ausgangspreis (EUR/MWh)',None),('coupling','Angenommene Preisweitergabe (0 bis 1)',1)],
        'Menge und Unternehmenspreis gelten für dieselbe Kundengruppe und historischen Vergleichsmonate. Preisbestandteile und Steuerbasis entsprechen der API-Reihe; die Menge bleibt konstant.'),
    'retail_industry': ('Strom Industrie · eigenes Tarifszenario', ('electricity_sales_industry',), 'MWh',
        [('amount','Eigene Industriemenge in den historischen Vergleichsmonaten (MWh)',None),('price','Eigener Ausgangspreis (EUR/MWh)',None),('coupling','Angenommene Preisweitergabe (0 bis 1)',1)],
        'Menge und Unternehmenspreis gelten für dieselbe Kundengruppe und historischen Vergleichsmonate. Preisbestandteile und Steuerbasis entsprechen der API-Reihe ohne Konzessionsabgabe; die Menge bleibt konstant.'),
    'spot': ('Strommarkt · offene Preisexposition', ('electricity_sales_total','electricity_generation'), 'MWh',
        [('amount','Offene, ungesicherte Menge im Vergleichszeitraum (MWh)',None)],
        'Diese Menge gehört zur belegten Unternehmensmenge und ist im angegebenen Zeitraum ungesichert dem DE-LU-Day-ahead-Preis ausgesetzt. Verkauf/Beschaffung und Zeitraum stimmen mit dem Szenario überein; keine Übertragung auf Gesamtgewinn oder Cashflow.'),
    'chargers': ('Ladepunkte · öffentlicher Unternehmensbestand', ('charge_points',), 'Anzahl',
        [('amount','Eigene öffentliche Ladepunkte zum historischen Stichtag im API-Gebiet',None)],
        'Die eingegebene Zahl enthält ausschließlich eigene öffentlich zugängliche Ladepunkte im unten genannten API-Gebiet und zum historischen API-Stichtag. Betreiberumfang und konstanter Marktanteil sind ausdrücklich angenommen.'),
    'vehicles': ('Ladestrom · jährliches BEV-Nachfrageszenario', ('charging_energy',), 'MWh',
        [('amount','Eigener jährlicher Ladestrom im API-Gebiet (MWh)',None),('coupling','An den BEV-Bestand gekoppelter Anteil (0 bis 1)',1)],
        'Die eigene Jahresmenge gehört zum unten genannten API-Gebiet und Berichtsjahr. Für den gekoppelten Anteil bleiben Ladeverhalten und Unternehmensmarktanteil konstant. Das Ergebnis ist eine annualisierte Nachfrage am neuen Fahrzeugstichtag, kein gemessener laufender Absatz.'),
}


DEFINITIONS['wastewater']=('Abwasser · eigenes Tarifszenario',('wastewater_volume',),'m³',DEFINITIONS['water'][3],
    DEFINITIONS['water'][4].replace('Haushaltskunden','Haushaltskunden der Abwasserentsorgung'))

def available_scenarios(report):
    from .config import REFERENCE_TOPICS
    result={}
    for key,(label,metrics,unit,fields,confirmation) in DEFINITIONS.items():
        for metric in metrics:
            basis=REFERENCE_TOPICS[metric][1]
            rows=[r for r in report.get('observations',[]) if r['metric']==metric
                  and r.get('status') in ('validated','manual_checked')
                  and r['year']==report['metadata']['year'] and r.get('unit')==unit
                  and r.get('basis')==basis and r.get('scope') in ('own','group','reported_portfolio','customers')
                  and r.get('portfolio')!='project' and r['value']>0]
            consolidated=[r for r in rows if r.get('reporting_scope')=='consolidated']
            if consolidated:rows=consolidated
            # Different entities or scopes are not interchangeable exposures.
            signatures={(r['value'],r.get('entity',''),r.get('scope'),r.get('reporting_scope')) for r in rows}
            if rows and len(signatures)==1:
                if key=='heat' and not report['metadata'].get('location',{}).get('city'):continue
                result['scenario_'+key]={'label':label+' · Angaben erforderlich','observation':rows[0],
                    'source_metric':metric,'scenario':key,'reference_kind':'scenario',
                    'fields':fields,'confirmation':confirmation}
                break
    return result


def analysis_options(report):
    from .calculation import available_metrics
    return available_metrics(report)


def scenario_reference(item,report,target_year,today=None):
    from .references import reference_pair, spot_reference, public_charger_reference, vehicle_reference
    today=today or date.today()
    year=item['observation']['year'];key=item['scenario']
    location=report['metadata'].get('location',{})
    if key=='spot':return spot_reference(year,target_year,today,report['metadata'].get('reporting_period'))
    if key=='chargers':return public_charger_reference(year,target_year,today,location)
    if key=='vehicles':return vehicle_reference(year,target_year,today,location)
    return reference_pair(item['source_metric'],year,target_year,today=today,report=report)


def validate_inputs(item,inputs):
    if inputs.get('confirmed') is not True:raise ValueError('Unternehmensumfang, Zeitraum und Modellannahmen müssen bestätigt werden.')
    for name,label,maximum in item['fields']:
        value=inputs.get(name)
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
            raise ValueError('Angabe fehlt oder ist ungültig: '+label)
        if value<0 or (name in ('price','months') and value<=0) or (maximum is not None and value>maximum):
            raise ValueError('Angabe außerhalb des zulässigen Bereichs: '+label)
    amount=inputs['amount']
    if amount<=0 or amount>item['observation']['value']:raise ValueError('Die betroffene Unternehmensmenge muss positiv sein und darf den belegten Berichtswert nicht überschreiten.')
    if item['scenario']=='interest' and amount<=1_000_000:raise ValueError('Diese Zinsreihe gilt für Kredite über 1 Mio. EUR; eine kleinere Exposition passt nicht zur Reihe.')
    if item['scenario']=='chargers' and amount!=int(amount):raise ValueError('Ladepunkte müssen als ganze Anzahl angegeben werden.')
    if item['scenario']=='spot' and inputs.get('direction') not in ('Verkauf','Beschaffung'):raise ValueError('Verkauf oder Beschaffung auswählen.')
    for field in ('baseline_date','target_date','geography'):
        if field not in inputs:raise ValueError('Der angezeigte API-Zeitraum und das Gebiet müssen mit bestätigt werden.')


def scenario_calculation(item,ref,inputs):
    validate_inputs(item,inputs)
    for field in ('baseline_date','target_date','geography'):
        if inputs[field]!=ref.get(field,'Deutschland' if field=='geography' else ''):
            raise ValueError('API-Zeitraum oder Gebiet hat sich geändert. Bitte die Angaben mit der aktualisierten Referenz erneut bestätigen.')
    key=item['scenario']
    b,t=ref['baseline'],ref['target']
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in (b,t)) or (key!='spot' and (b<=0 or t<0)):
        raise ValueError('Eine positive historische und nicht negative aktuelle Referenz ist erforderlich.')
    amount=inputs['amount'];coupling=inputs.get('coupling',1)
    if key=='interest':
        base=amount*b/100*inputs['months']/12;expected=amount*t/100*inputs['months']/12
        formula='Kreditsumme × Referenzzins / 100 × Monate / 12'
        title='Modellierter Zinsaufwand auf die betroffene Finanzierung';unit='EUR';period=f"{inputs['months']:g} Monate Zinswirkung"
    elif key=='spot':
        base=amount*b;expected=amount*t;unit='EUR';formula='Offene Menge × Day-ahead-Preis'
        title='Bedingter Verkaufserlös' if inputs['direction']=='Verkauf' else 'Bedingte Beschaffungskosten'
        period='Preisvergleich für die angegebenen API-Monate'
    elif key.startswith('retail_') or key in ('water','wastewater'):
        base=amount*inputs['price'];expected=base*(1+coupling*(t/b-1));unit='EUR'
        formula='Eigene Menge × eigener Preis × [1 + Weitergabe × (API-Preisverhältnis − 1)]'
        title='Bedingter mengenbezogener Erlös';period='Gleiche Vergleichsmonate · Menge unverändert'
    else:
        base=amount;expected=amount*(1+coupling*(t/b-1));unit=item['observation']['unit']
        formula='Eigene Basis × [(1 − gekoppelter Anteil) + gekoppelter Anteil × API-Verhältnis]'
        title={'heat':'Bedingter Wärmeabsatz','chargers':'Bedingter öffentlicher Ladepunktbestand','vehicles':'Bedingter annualisierter Ladestrom'}[key]
        period={'heat':'Gleiche Vergleichsmonate','chargers':'Bestand zum Vergleichsstichtag','vehicles':'Jahresmenge bei aktuellem BEV-Bestand'}[key]
    if not all(math.isfinite(v) for v in (base,expected)):raise ValueError('Szenariowerte sind nicht endlich.')
    calc={'kind':'scenario','baseline_company':base,'expected':expected,'company_change':expected-base,
        'output_unit':unit,'title':title,'period_label':period,'formula':formula,
        'assumptions':dict(inputs),'input_origin':'user_assumption','reference_change_percent':(t/b-1)*100 if b>0 else None,
        'confirmation_text':item['confirmation']}
    return dict(ref,kind='scenario',assumption=item['confirmation']),calc
