import os
from antelope_foreground import ForegroundCatalog

CAT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'catalog'))


def lca_init():
    cat = ForegroundCatalog(CAT_ROOT, strict_clookup=False, quell_biogenic_co2=True)
    cat.lcia_engine.add_synonym('number of items', 'Items')
    cat.lcia_engine.add_synonym('number of items', 'Count')
    cat.lcia_engine.get_canonical('volume')['UnitConversion']['mL'] = 1e6
    return cat
