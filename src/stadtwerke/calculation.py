import math

def baseline_scenarios(company, reference_base, reference_target, spread=0.1):
    if not all(math.isfinite(v) for v in (company,reference_base,reference_target,spread)):
        raise ValueError('Nicht endliche Zahlen.')
    if reference_base <= 0 or company < 0 or reference_target < 0 or not 0 <= spread <= .5:
        raise ValueError('Unzulässige Ausgangswerte oder Szenarioabstände.')
    ratio = company/reference_base
    expected = ratio*reference_target
    return {'ratio':ratio,'ratio_percent':ratio*100,'expected':expected,
            'lower':expected*(1-spread),'upper':expected*(1+spread),'spread':spread,
            'reference_change_percent':(reference_target/reference_base-1)*100,
            'company_change':expected-company,
            'formula':'U_basis * R_target / R_basis'}

def available_metrics(report):
    from .config import CAPACITY_TOPICS, REFERENCE_TOPICS
    available = {}
    for metric,(label,_,unit) in CAPACITY_TOPICS.items():
        rows = [r for r in report['observations'] if r['metric']==metric and
                r['status'] in ('validated','manual_checked') and r['year']==report['metadata']['year']
                and r.get('basis')=='stock' and r.get('unit')==unit
                and r.get('geography')=='DE'
                and ((r['scope'] in ('own','group') and r.get('portfolio')=='total') or
                     (r['scope']=='reported_portfolio' and r.get('portfolio')=='defined_subset' and r.get('entity')))]
        # A confirmed total and a bounded subset describe different cohorts.
        # Prefer the total; never treat their different sizes as a contradiction.
        totals = [r for r in rows if r.get('portfolio')=='total']
        if totals:
            rows = totals
        elif len({r.get('entity','') for r in rows}) > 1:
            rows = []
        # Unresolved disagreement is not silently reduced to the first candidate.
        if rows and len({r['value'] for r in rows}) == 1:
            entity = rows[0].get('entity', '')
            available[metric] = {'label':label + (' · ' + entity if entity else ''),'observation':rows[0]}
    for metric,(label,basis,unit,kind) in REFERENCE_TOPICS.items():
        if kind=='context':continue
        rows=[r for r in report['observations'] if r['metric']==metric
              and r['status'] in ('validated','manual_checked') and r['year']==report['metadata']['year']
              and r.get('basis')==basis and r.get('unit')==unit
              and r.get('scope') in ('own','group','reported_portfolio','network_area','customers')
              and r.get('portfolio')!='project']
        if metric=='debt' and any(r.get('scope')=='group' and r.get('table_reference') for r in rows):
            rows=[r for r in rows if r.get('scope')=='group' and r.get('table_reference')]
        # Explicitly labelled consolidated totals are the report's primary
        # cohort. Wider group totals remain visible, never added to them.
        consolidated=[r for r in rows if r.get('reporting_scope')=='consolidated']
        if consolidated:
            rows=consolidated
        if metric=='revenue' and any(r.get('portfolio')=='total' for r in rows):
            rows=[r for r in rows if r.get('portfolio')=='total']
        if metric=='heat_sales' and not report['metadata'].get('location',{}).get('city'):
            continue
        if rows and len({(r['value'],r.get('entity','')) for r in rows})==1:
            available[metric]={'label':label,'observation':rows[0],'reference_kind':kind}
    from .personnel import personnel_option
    staff=personnel_option(report)
    if staff:available[staff['observation']['metric']]=staff
    return available


def calculate_reference(obs,ref,spread=0):
    kind=ref.get('kind','stock')
    if kind in ('stock','flow'):
        if obs['unit']!=ref['unit']:
            raise ValueError('Bericht und Mengenreferenz haben unterschiedliche Einheiten.')
        calc=baseline_scenarios(obs['value'],ref['baseline'],ref['target'],spread)
        if kind=='flow':
            aligned=ref['aligned_baseline']
            if aligned<=0: raise ValueError('Historische Vergleichsperiode hat keine positive Referenzmenge.')
            calc['historical_company_aligned']=obs['value']*aligned/ref['baseline']
            calc['company_change']=calc['expected']-calc['historical_company_aligned']
            calc['reference_change_percent']=(ref['target']/aligned-1)*100
            calc['formula']='U_annual * R_current_YTD / R_baseline_annual; growth = R_current_YTD / R_baseline_same_months - 1'
        return dict(calc,kind=kind,company_outlook_series=company_outlook_series(obs,ref))
    b,t=ref['baseline'],ref['target']
    if not all(math.isfinite(v) for v in (b,t)): raise ValueError('Nicht endliche Referenzwerte.')
    return {'kind':'context','expected':None,'ratio':None,'ratio_percent':None,'company_change':None,
        'reference_change':t-b,'reference_change_percent':(t/b-1)*100 if b>0 else None,
        'formula':'R_current - R_baseline; no company projection without exposure assumptions'}


def company_outlook_series(obs,ref):
    """Generate conditional company values; never label them observations."""
    kind=ref.get('kind','stock')
    if kind=='context':return []
    baseline=ref['baseline']
    if baseline<=0:raise ValueError('Eine positive Referenzbasis ist erforderlich.')
    ratio=obs['value']/baseline
    output=[];current=historical=0
    for point in ref.get('history',[]):
        value=point['value']
        if not math.isfinite(value) or value<0:raise ValueError('Unzulässige Mengenreferenz in der Verlaufskurve.')
        if kind=='flow':
            historic=point.get('baseline_value')
            if historic is None or not math.isfinite(historic) or historic<0:
                raise ValueError('Historischer Vergleichsmonat für die Verlaufskurve fehlt.')
            current+=value;historical+=historic
            output.append({'date':point['date'],'value':ratio*current,'historical_proxy':ratio*historical,
                'value_kind':'conditional_company_projection','historical_kind':'reference_derived_distribution'})
        else:
            output.append({'date':point['date'],'value':ratio*value,'value_kind':'conditional_company_projection'})
    return output


def reference_comparison(ref):
    """Display flow references for matching months, keeping annual bases separate."""
    if ref.get('kind')!='flow':
        return {'baseline':ref['baseline'],'baseline_period':ref['baseline_date'],
                'target':ref['target'],'target_period':ref['target_date']}
    months=ref['months']
    historic_dates=ref.get('baseline_comparison_dates') or [f"{ref['baseline_date'][:4]}-{m:02}" for m in range(1,months+1)]
    current_dates=[f"{ref['target_date'][:4]}-{m:02}" for m in range(1,months+1)]
    return {'baseline':ref['aligned_baseline'],'baseline_period':_month_period(historic_dates),
            'target':ref['target'],'target_period':_month_period(current_dates)}


def _month_period(dates):
    names=['','Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember']
    years={}
    for value in sorted(set(d[:7] for d in dates)):
        years.setdefault(value[:4],[]).append(int(value[5:7]))
    labels=[]
    for year,months in years.items():
        if months==list(range(months[0],months[-1]+1)):
            label=names[months[0]] if len(months)==1 else names[months[0]]+'–'+names[months[-1]]
        else:label=', '.join(names[m] for m in months)
        labels.append(label+' '+year)
    return '; '.join(labels)
