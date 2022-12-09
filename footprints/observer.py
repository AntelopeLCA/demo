from antelope_reports import QuickAndEasy  # , MissingValue

from pandas import DataFrame
from itertools import chain
from csv import QUOTE_ALL


from antelope_reports.model_runner.quick_model_runner import QuickModelRunner


TERMS = {
    'coffee_green': ['ecoinvent.3.8.cutoff', '40cd93ba-b97f-43e5-8bbd-f86e34cf1d4d'],
    'elec_wecc': ['ecoinvent.3.8.cutoff', '56c40e26-3740-4973-916e-3999d997ea60'],
    'ng_mj': ['ecoinvent.3.8.cutoff', '242162aa-17fb-4e5d-923a-899b5b7bb864'],
    'ng_mj_high': ['ecoinvent.3.8.cutoff', '44e62980-8489-4a80-8ecb-fca6a12e2d05'],
    'tissue_paper': ['ecoinvent.3.8.cutoff', '6f123135-58e0-4e4c-b556-19d5e71ea15e'],
    'sugar': ['ecoinvent.3.8.cutoff', 'e24d837f-eabb-41df-b282-c97af565b6ca'],
    'soap': ['ecoinvent.3.8.cutoff',  '21abc849-d8aa-4151-b063-b10df257abfc'],
    'tap_water': ['ecoinvent.3.8.cutoff', 'ac596c5b-7779-4a51-9c5f-9ec2e0025d6d'],
    'landfill': ['ecoinvent.3.8.cutoff', '37fecf1c-c830-4bff-a8fe-76aa79d7ff2d']
}


class CoffeeAndShower(QuickAndEasy):

    __c = None

    def build_coffee_frags(self):
        if self.__c:
            return self.__c

        mass = self.fg.get_canonical('mass')

        # coffee roasting
        # https://link.springer.com/article/10.1007/s11367-019-01719-2/tables/2
        roast = self.new_link('Coffee, roasted', 'mass', 'Output', 1000.0)
        self.new_link('Coffee, green', 'mass', 'Input', 1152.0, parent=roast).terminate(self.terms('coffee_green'))
        self.new_link('Electricity', 'kWh', 'Input', 275, units='MJ', parent=roast).terminate(self.terms('elec_wecc'))
        self.new_link('Heat, natural gas', 'net calorific value', 'Input', 1702, units='MJ',
                      parent=roast).terminate(self.terms('ng_mj_high'))
        self.new_link('Water', 'mass', 'Input', 384, units='kg', parent=roast).terminate(self.terms('tap_water'))

        cg = self.new_link('Coffee, ground', 'mass', 'Output', 1.0)
        self.new_link('Coffee, roasted', 'mass', 'Input', balance=True, parent=cg).terminate(roast)
        self.new_link('Electricity, grinding', 'kWh', 'Input', 0.35, parent=cg).terminate(self.terms('elec_wecc'))

        brew = self.new_link('Coffee, 1 cup', 'volume', 'Output', 180, units='mL')
        self.new_link('Coffee, ground', 'mass', 'Input', 0.010, parent=brew,
                      stage='Ground Coffee').terminate(cg, descend=False)
        filt = self.new_link('Coffee filter', 'Count', 'Input', 0.2, parent=brew)
        filt.flow.characterize(mass, 0.0017)
        self.new_link('New Coffee Filter', 'mass', 'Input', 0.0017, parent=filt,
                      stage='Filter').terminate(self.terms('tissue_paper'))

        self.new_link('Electricity, at user', 'kWh', 'Input', 0.175, parent=brew,
                      stage='Electricity').terminate(self.terms('elec_wecc'))
        water = self.new_link('Water, at user', 'volume', 'Input', 190, units='mL', parent=brew, stage='Tap water')
        water.flow.characterize(mass, 1000.0)
        water.terminate(self.terms('tap_water'))

        self.new_link('Spent coffee grounds', 'mass', 'Output', balance=True, parent=brew,
                      stage='Waste to landfill').terminate(self.terms('landfill'))  # OMG 'balance' is a direction

        coffee = self.new_link('Morning coffee', 'Items', 'Output', 1.0)
        self.new_link('Coffee', 'volume', 'Input', 330, units='mL', parent=coffee).terminate(brew)
        self.new_link('Sugar', 'mass', 'Input', 0.015, parent=coffee, stage='Sugar').terminate(self.terms('sugar'))

        self.__c = roast, cg, brew, coffee
        return self.__c

    @property
    def coff(self):
        return self.__c

    __s = None

    def build_shower(self):
        if self.__s:
            return self.__s
        heat = self.new_link('Lossy Heat', 'net calorific value', 'Output', 0.65, units='MJ')
        self.new_link('Delivered heat', 'net calorific value', 'Input', 1.0, units='MJ',
                      parent=heat).terminate(self.terms('ng_mj'))

        hw = self.new_link('Hot water 50C', 'volume', 'Output', 1.0, units='l')
        # hot water
        self.new_link('water, at user', 'volume', 'Input', balance=True, parent=hw,
                      stage='Tap water').terminate(self.terms('tap_water'))
        kj = self.new_link('kj per kg water degree C', 'net calorific value', 'Input', 4.184, units='KJ', parent=hw)
        kjc = self.new_link('times degrees C', 'net calorific value', 'Input', 25, parent=kj,
                            name='_hot_water_delta_t')  # need ad hoc scenarios
        self.new_link('Lossy heat from pipe', 'net calorific value', 'Input', balance=True, parent=kjc).terminate(heat)

        shower = self.new_link('Hot Shower', 'Count', 'Output', 1.0)
        mins = self.new_link('Minutes per shower', 'Count', 'Input', 15, parent=shower)
        ls = self.new_link('liters per minute', 'volume', 'Input', 8, units='l', parent=mins)
        self.new_link('cold water fraction', 'volume', 'Input', 0.1, flow_ref='flow_water_at_user', parent=ls,
                      stage='Cold water').terminate(self.terms('tap_water'))
        self.new_link('hot water fraction', 'volume', 'Input', balance=True, parent=ls,
                      stage='Hot water').terminate(hw, descend=False)

        self.new_link('some soap', 'mass', 'Input', 0.025, parent=shower, stage='Soap').terminate(self.terms('soap'))

        self.__s = heat, hw, shower
        return self.__s

    @property
    def shwr(self):
        return self.__s


def qae_init(cat, fg_name='coffee'):
    qae = CoffeeAndShower.by_name(cat, fg_name, terms=TERMS)
    qae.build_coffee_frags()
    qae.build_shower()
    return qae


def _frag_name(frag):
    if frag is None:
        return '(reference)'
    if frag.external_ref == frag.uuid:
        return frag.uuid[:5]
    return frag.external_ref


def _term(ff):
    if ff.term.is_context:
        return ff.term.term_node.name
    elif ff.term.is_null:
        return ff.fragment.direction
    elif ff.term.is_process:
        return ff.term.term_node.name
    elif ff.term.is_fg:
        return '(foreground)'
    else:
        return _frag_name(ff.term.term_node)


def act_table(ff, *res):
    d = {
        'parent': _frag_name(ff.fragment.parent),
        'direction': ff.fragment.direction,
        'node': _frag_name(ff.fragment),
        'flow': ff.fragment.flow.name,
        'magnitude': ff.magnitude,
        'units': ff.fragment.flow.unit,
        'term': _term(ff),
    }
    for r in res:
        try:
            s = r[ff].cumulative_result
        except KeyError:
            if ff.fragment.is_reference:
                s = ff.fragment.fragment_lcia(r.quantity, r.scenario).total()
            else:
                s = None
        d[r.quantity['Indicator']] = s
    return d


refs = ('coffee_1_cup', 'coffee_ground', 'coffee_roasted', 'morning_coffee', 'hot_shower', 'hot_water_50c', 'lossy_heat')


def write_fragment_flows(qae, q, fragment_flows_file='coffee_and_shower.csv'):
    frags = [qae.fg[k] for k in refs]
    res = {f: f.fragment_lcia(q) for f in frags}
    df = DataFrame(chain(*((act_table(ff, res[ff.fragment.top()]) for ff in
                            _f.activity(True)) for _f in frags)))

    df.to_csv(fragment_flows_file, index=False, quoting=QUOTE_ALL)


def write_lcia(qae, q, lcia_file='coffee_shower_lcia.csv'):
    frags = [qae.fg[k] for k in refs]
    qr = QuickModelRunner(qae.fg, frags)
    qr.run_lcia(q)
    qr.results_to_csv(lcia_file)
