"""
This script file generates a set of API outputs as JSON files

Routes to generate:

    ORYX_ROOT/[foreground]/fragments     [list of FragmentRef]
    ORYX_ROOT/[foreground]/fragments/<fragment id>    FragmentEntity
    ORYX_ROOT/[foreground]/fragments/[fragment id]/tree                [list of FragmentBranch]
    ORYX_ROOT/[foreground]/fragments/[fragment id]/scenarios           [list of str]
    ORYX_ROOT/[foreground]/fragments/[fragment id]/child_flows         [list of FragmentRef]
    ORYX_ROOT/[foreground]/fragments/[fragment id]/traverse            [list of FragmentFlow]

let's do this after dinner

OK, so we'll make an output directory with one file-- the list of fragments-- and a subdirectory for each fragment
containing 5 files- the fragment entity itself, plus the tree traversal, the list of scenarios, the list of child
flows, and the traversal.  and maybe we'll throw in LCIA.

But hold on- first we have to write the tree routine.

"""
import os
import json

from footprints import lca_init

from antelope_foreground import models
from antelope_core.models import DetailedLciaResult, Entity

API_ROOT = 'ORYX_ROOT'


def _write_api_response(path, *query, response=None, noisy=False, **kwargs):
    """
    :param path:
    :param query: a tuple
    :param response:
    :param noisy:
    :return:
    """
    if response is None:
        response = dict()

    route = '/'.join([API_ROOT, *query])

    j = {'route': route,
         'response': response,
         'params': kwargs}

    wp = os.path.join(path, *query)

    os.makedirs(os.path.dirname(wp), exist_ok=True)
    if noisy:
        print('generating json output to %s' % wp)
    with open(wp, 'w') as fp:
        json.dump(j, fp, indent=2)


def demo_output(fg, path, *qs, **kwargs):
    """

    :param fg: the foreground
    :param path: output
    :return:
    """
    foreground = fg.origin

    frags = list(fg.fragments(**kwargs))

    _write_api_response(path, 'foregrounds', response=['coffee'])

    _write_api_response(path, 'lcia_methods', response=[Entity.from_entity(q).dict() for q in qs])

    # ORYX_ROOT/[foreground]/fragments
    fragments = [models.FragmentRef.from_fragment(f).dict() for f in frags]
    _write_api_response(path, foreground, 'fragments', response=fragments)

    for frag in frags:
        ent = models.FragmentEntity.from_entity(frag).dict()
        subpath = (path, foreground, frag.external_ref)
        _write_api_response(*subpath, frag.external_ref, response=ent)

        tree = [models.FragmentBranch.from_fragment(f, observed=True).dict() for f in frag.tree()]
        _write_api_response(*subpath, 'tree_observed', response=tree, scenario='observed')  # '1' also works (and 1 too I think)

        tree = [models.FragmentBranch.from_fragment(f).dict() for f in frag.tree()]
        _write_api_response(*subpath, 'tree', response=tree, scenario='cached')

        scens = list(frag.scenarios())
        _write_api_response(*subpath, 'scenarios', response=scens)

        cfs = [models.FragmentRef.from_fragment(c).dict() for c in frag.child_flows]
        _write_api_response(*subpath, 'child_flows', response=cfs)

        _write_api_response(*subpath, 'anchor', response=frag.term.to_anchor().dict())

        ffs = [models.FragmentFlow.from_fragment_flow(ff).dict() for ff in frag.traverse(observed=True)]
        _write_api_response(*subpath, 'traverse', response=ffs)

        for scen in scens:
            _fs = [models.FragmentFlow.from_fragment_flow(ff).dict() for ff in frag.traverse(scenario=scen)]
            _write_api_response(*subpath, 'traverse_%s' % scen, response=_fs, scenario=scen)

        for q in qs:
            res = frag.fragment_lcia(q)

            lcia = DetailedLciaResult.from_lcia_result(frag, res).dict()
            _write_api_response(*subpath, 'contrib_lcia', q.external_ref, response=lcia)

            lcia_f = DetailedLciaResult.from_lcia_result(frag, res.flatten()).dict()
            _write_api_response(*subpath, 'lcia', q.external_ref, response=lcia_f)

            lcia_s = DetailedLciaResult.from_lcia_result(frag, res.aggregate()).dict()
            _write_api_response(*subpath, 'stage_lcia', q.external_ref, response=lcia_s)

            lcia_a = DetailedLciaResult.from_lcia_result(frag, res.terminal_nodes()).dict()
            _write_api_response(*subpath, 'anchor_lcia', q.external_ref, response=lcia_a)


if __name__ == '__main__':
    cat = lca_init()

    PATH = '/data/GitHub/Antelope/demo/oryx_demo/ORYX_ROOT'
    qs = list(cat.query('local.lcia.traci.2.1').lcia_methods())

    demo_output(cat.foreground('coffee'), PATH, qs[4], qs[8])