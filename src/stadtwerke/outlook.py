"""Keep enterprise results separate from external environment-only comparisons."""

def company_result(result):
    topics=[_without_day_ahead(item) for item in result.get('topics',[]) if item['reference'].get('kind','stock') in ('stock','flow','report')]
    return dict(result,reference_period_display='aligned-v1',topics=topics,reviews=[row for row in result.get('reviews',[]) if _eligible(row['metric'])])


def _eligible(metric):
    from .config import REFERENCE_TOPICS
    if metric.startswith('scenario_'):return False
    return metric not in REFERENCE_TOPICS or REFERENCE_TOPICS[metric][3]!='context'


def _without_day_ahead(item):
    ref=item['reference']
    secondary=ref.get('secondary')
    if not secondary:return item
    kept=[row for row in secondary if row.get('series')!='day_ahead_price' and row.get('label')!='Day-ahead-Marktpreis']
    if len(kept)==len(secondary):return item
    return dict(item,reference=dict(ref,secondary=kept))
