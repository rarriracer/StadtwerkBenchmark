"""Deduplicate visible characters with pdfplumber's rules and linear order lookup."""
from itertools import groupby
from operator import itemgetter
from pdfplumber.page import FilteredPage
from pdfplumber.utils import cluster_objects


def clean_page(page):
    visible=page.within_bbox(page.bbox)
    # Lightweight page doubles used by tests have no PDF character objects.
    if not hasattr(visible,'chars'):return visible.dedupe_chars()
    chars=visible.chars
    order={id(char):index for index,char in enumerate(chars)}
    key=itemgetter('upright','text','fontname','size');position=itemgetter('doctop','x0')
    kept=[]
    for _,group in groupby(sorted(chars,key=key),key=key):
        for ys in cluster_objects(list(group),itemgetter('doctop'),1):
            for xs in cluster_objects(ys,itemgetter('x0'),1):kept.append(min(xs,key=position))
    filtered=FilteredPage(visible,lambda obj:True)
    filtered._objects={kind:objects for kind,objects in visible.objects.items()}
    filtered._objects['char']=sorted(kept,key=lambda char:order[id(char)])
    return filtered
