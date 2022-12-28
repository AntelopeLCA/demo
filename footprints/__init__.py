import os
from antelope_foreground import ForegroundCatalog
from .observer import QuickAndEasy, qae_init


CAT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'catalog'))
BLACKBOOK_URL = 'http://localhost:80'


def lca_init(xdb=False):
    if xdb:
        cat = ForegroundCatalog.make_tester(strict_clookup=False, quell_biogenic_co2=True)
        cat.blackbook_authenticate(BLACKBOOK_URL)
        cat.get_blackbook_resources('demo.ecoinvent')
    else:
        cat = ForegroundCatalog(CAT_ROOT, strict_clookup=False, quell_biogenic_co2=True)
    cat.lcia_engine.add_synonym('number of items', 'Items')
    cat.lcia_engine.add_synonym('number of items', 'Count')
    cat.lcia_engine.get_canonical('volume')['UnitConversion']['mL'] = 1e6
    return cat
