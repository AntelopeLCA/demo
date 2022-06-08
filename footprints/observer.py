from antelope_foreground.foreground_catalog import NoSuchForeground


tr = str.maketrans(' ', '_', ',[]()*&^%$#@')


def _flow_to_ref(name):
    n = name.translate(tr).lower()
    if n.startswith('flow_'):
        fl = n
        fr = n[5:]
    else:
        fr = n
        fl = 'flow_' + n
    return fl, fr


class MissingValue(Exception):
    """
    Used when a quick-link spec is missing a value and no parent is provided
    """
    pass



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



class QuickAndEasy(object):

    @classmethod
    def by_name(cls, cat, fg_name):
        try:
            fg = cat.foreground(fg_name, reset=True)
        except NoSuchForeground:
            fg = cat.create_foreground(fg_name)
        return cls(fg)

    def __init__(self, fg):
        self._fg = fg
        self._terms = {k: fg.catalog_ref(*v) for k, v in TERMS.items()}

    @property
    def fg(self):
        return self._fg

    def terms(self, term):
        return self._terms[term]

    def new_link(self, flow, ref_quantity, direction, amount=None, units=None, flow_ref=None, parent=None, name=None,
                 stage=None,
                 balance=None):
        """
        Just discovered that 'balance' is actually a direction

        am I writing fragment_from_exchanges *again*? this is the API, this function right here

        NO
        the api is fragment_from_exchange. and yes, i am writing it again.

        The policy of this impl. is to create from scratch.  no need to re-run + correct: just scratch and throw out

        :param flow:
        :param ref_quantity:
        :param direction:
        :param amount:
        :param units:
        :param flow_ref:
        :param parent:
        :param name:
        :param stage:
        :param balance: direction='balance' should be equivalent;; direction is irrelevant under balance
        :return:
        """
        external_ref = name or None
        auto_ref, frag_ref = _flow_to_ref(flow)

        if parent is None:
            external_ref = external_ref or frag_ref

        f = self.fg[flow_ref or auto_ref] or self.fg.new_flow(flow, ref_quantity, external_ref=auto_ref)

        amt = 0
        if direction == 'balance':
            balance = True
        else:
            try:
                amt = float(amount)
            except (TypeError, ValueError):
                if parent is None:
                    raise MissingValue
                balance=True

        if balance:
            frag = self.fg.new_fragment(f, direction, parent=parent, balance=True)
        else:
            frag = self.fg.new_fragment(f, direction, value=1.0, parent=parent, external_ref=external_ref)
            self.fg.observe(frag, exchange_value=amt, units=units)

        if stage:
            frag['StageName'] = stage
        return frag


class CoffeeAndShower(QuickAndEasy):

    __c = None
    def build_coffee_frags(self):
        if self.__c:
            return self.__c

        mass = self.fg.get_canonical('mass')

        ## coffee roasting
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
        self.new_link('Coffee, ground', 'mass', 'Input', 0.010, parent=brew, stage='Ground Coffee').terminate(cg, descend=False)
        filt = self.new_link('Coffee filter', 'Count', 'Input', 0.2, parent=brew)
        filt.flow.characterize(mass, 0.0017)
        self.new_link('New Coffee Filter', 'mass', 'Input', 0.0017, parent=filt, stage='Filter').terminate(self.terms('tissue_paper'))

        self.new_link('Electricity, at user', 'kWh', 'Input', 0.175, parent=brew, stage='Electricity').terminate(self.terms('elec_wecc'))
        water = self.new_link('Water, at user', 'volume', 'Input', 190, units='mL', parent=brew, stage='Tap water')
        water.flow.characterize(mass, 1000.0)
        water.terminate(self.terms('tap_water'))

        self.new_link('Spent coffee grounds', 'mass', 'Output', balance=True, parent=brew, stage='Waste to landfill').terminate(self.terms('landfill'))  # OMG 'balance' is a direction

        coffee = self.new_link('Morning coffee', 'Items', 'Output', 1.0)
        self.new_link('Coffee', 'volume', 'Input', 330, units='mL', parent=coffee).terminate(brew)
        self.new_link('Sugar', 'mass', 'Input', 0.015, parent=coffee, stage='Sugar').terminate(self.terms('sugar'))

        self.__c = roast, cg, brew, coffee
        return self.__c

    __s = None

    def build_shower(self):
        if self.__s:
            return self.__s
        heat = self.new_link('Lossy Heat', 'net calorific value', 'Output', 0.65, units='MJ')
        self.new_link('Delivered heat', 'net calorific value', 'Input', 1.0, units='MJ', parent=heat).terminate(self.terms('ng_mj'))

        hw = self.new_link('Hot water 50C', 'volume', 'Output', 1.0, units='l')
        # hot water
        self.new_link('water, at user', 'volume', 'Input', balance=True, parent=hw, stage='Tap water').terminate(self.terms('tap_water'))
        kj = self.new_link('kj per kg water degree C', 'net calorific value', 'Input', 4.184, units='KJ', parent=hw)
        kjc = self.new_link('times degrees C', 'net calorific value', 'Input', 25, parent=kj, name='_hot_water_delta_t')  # need ad hoc scenarios
        self.new_link('Lossy heat from pipe', 'net calorific value', 'Input', balance=True, parent=kjc).terminate(heat)

        shower = self.new_link('Hot Shower', 'Count', 'Output', 1.0)
        mins = self.new_link('Minutes per shower', 'Count', 'Input', 15, parent=shower)
        ls = self.new_link('liters per minute', 'volume', 'Input', 8, units='l', parent=mins)
        self.new_link('cold water fraction', 'volume', 'Input', 0.1, flow_ref='flow_water_at_user', parent=ls,
                      stage='Cold water').terminate(self.terms('tap_water'))
        self.new_link('hot water fraction', 'volume', 'Input', balance=True, parent=ls, stage='Hot water').terminate(hw, descend=False)

        self.new_link('some soap', 'mass', 'Input', 0.025, parent=shower, stage='Soap').terminate(self.terms('soap'))

        self.__s = heat, hw, shower
        return self.__s
