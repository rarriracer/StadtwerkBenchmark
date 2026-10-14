"""Source-bound personnel comparison, with no external workforce projection."""
import math
import re


def personnel_option(report):
    def unique(metric):
        rows=[r for r in report['observations'] if r['metric']==metric and r['status'] in ('validated','manual_checked')
              and r['year']==report['metadata']['year'] and r.get('unit')=='Anzahl' and r.get('value') is not None
              and r.get('portfolio')=='total' and r.get('scope') in ('own','group')]
        keys={(r['value'],r.get('page'),r.get('entity','')) for r in rows}
        return rows[0] if len(keys)==1 else None
    employees=unique('employees');apprentices=unique('apprentices')
    main=employees or apprentices
    if not main:return None
    return {'label':'Beschäftigte & Ausbildung','observation':main,'reference_kind':'report',
            'personnel':{'employees':employees,'apprentices':apprentices}}


def personnel_analysis(option,report):
    rows=option['personnel'];employee=rows['employees'];apprentice=rows['apprentices']
    quote=None;reason='Für die Quote fehlen eindeutig abgegrenzte Mitarbeiter- und Ausbildungszahlen.'
    if employee and apprentice:
        a=employee.get('table_reference',{});b=apprentice.get('table_reference',{})
        comparable=(employee['page']==apprentice['page'] and a.get('header') and a['header']==b.get('header')
                    and employee['year']==apprentice['year'] and employee.get('scope')==apprentice.get('scope')
                    and employee.get('reporting_scope')==apprentice.get('reporting_scope'))
        excludes=re.search(r'ohne\s+Auszubildende',employee['evidence'],re.I)
        if comparable and excludes:
            total=employee['value']+apprentice['value']
            if total>0 and all(math.isfinite(r['value']) and r['value']>=0 for r in (employee,apprentice)):
                quote=apprentice['value']/total*100
                reason='Auszubildende / (Mitarbeiter ohne Auszubildende + Auszubildende) × 100; gleiche Tabelle und Berichtsperiode.'
        else:reason='Die gemeinsame Zeitbasis oder die Abgrenzung ohne Auszubildende ist nicht eindeutig belegt.'
    basis='Jahresdurchschnitt' if re.search(r'Jahresdurchschnitt|Jahresmittel|Durchschnittliche Anzahl',option['observation'].get('table_reference',{}).get('header',''),re.I) else 'Berichtsangabe'
    reference={'period_label':basis+' '+str(report['metadata']['year']),'kind':'report','provider':'Geschäftsbericht','target_date':str(report['metadata']['year']),
               'unit':'Anzahl','baseline':None,'target':None,'baseline_date':str(report['metadata']['year']),
               'assumption':reason,'personnel':rows,'url':report['metadata'].get('path',''),'sha256':report['id']}
    calc={'kind':'report','expected':None,'company_change':None,'apprentice_share_percent':quote,
          'formula':'apprentices / (employees_excluding_apprentices + apprentices) * 100' if quote is not None else None}
    return reference,calc
