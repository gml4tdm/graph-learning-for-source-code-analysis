#! ../venv/bin/python
import argparse
####################################################################################################
####################################################################################################
# Imports, Constants, Config
####################################################################################################

import collections
import contextlib
import os
import warnings

import alive_progress
import matplotlib.pyplot as pyplot
import upsetplot

import data_loading
import utils
import plot_utils

import seaborn


@contextlib.contextmanager
def adjusted_font_scale(scale):
    _set_seaborn_theme(scale)
    yield
    _set_seaborn_theme(FONT_SCALE)


def _set_seaborn_theme(font_scale):
    seaborn.set_theme(
        context='paper',
        rc={
            'patch.force_edgecolor': False  # No edge color to keep stack chart readable
        },
        font_scale=font_scale
    )


FONT_SCALE = 1.5
_set_seaborn_theme(FONT_SCALE)
pyplot.rcParams["font.family"] = "Hack"

os.makedirs('temp', exist_ok=True)


####################################################################################################
####################################################################################################
# Domains
####################################################################################################


@utils.easy_log('Plotting Domain Charts')
def plot_domains(args, data: list[data_loading.DataLoader]):
    plot_domains_as_pie(args, data)
    plot_domains_as_stack_chart(args, data)
    plot_domains_joint(args, data)


@utils.easy_log('Plotting Domain Pie Chart')
def plot_domains_as_pie(args, data: list[data_loading.DataLoader], ax=None):
    """Plot the domains as a pie chart."""
    hist = collections.defaultdict(int)
    for x in data:
        for domain in x.domains:
            hist[domain] += 1
    labels = sorted(hist, key=lambda x: hist[x], reverse=True)
    values = [hist[label] for label in labels]
    total = sum(values)
    if ax is None:
        with plot_utils.figure('domains/domains-as-pie.png') as (fig, ax):
            return ax.pie(values,
                          labels=labels,
                          autopct=lambda p: '{:.0f}'.format(p * total / 100),
                          pctdistance=1.15)
    else:
        return ax.pie(values,
                      autopct=lambda p: '{:.0f}'.format(p * total / 100),
                      pctdistance=1.15)


@utils.easy_log('Plotting Domain Stack Chart')
def plot_domains_as_stack_chart(args, data: list[data_loading.DataLoader], ax=None):
    """Plot the domains as a stack plot"""
    # Compute count per domain per year
    count_per_domain_per_year = collections.defaultdict(lambda: collections.defaultdict(int))
    for z in data:
        for domain in z.domains:
            count_per_domain_per_year[domain][z.year] += 1
    if ax is None:
        with plot_utils.figure('domains/domains-as-stack.png', tight=False) as (fig, ax):
            return plot_utils.stack_chart_from_dict(count_per_domain_per_year, ax)
    else:
        return plot_utils.stack_chart_from_dict(count_per_domain_per_year, ax, draw_labels=False)


@utils.easy_log('Plotting Domains Joint')
def plot_domains_joint(args, data: list[data_loading.DataLoader]):
    with adjusted_font_scale(1):
        variant = 'single columnx'
        if variant == 'single column':
            with plot_utils.figure('domains/domains-joint.png',
                                   nrows=2,
                                   ncols=2,
                                   tight=True,
                                   a4=True,
                                   height_factor=0.5,
                                   grid_spec=True) as (fig, spec):
                ax1 = fig.add_subplot(spec[0, 0])
                ax2 = fig.add_subplot(spec[0, 1])
                ax3 = fig.add_subplot(spec[1, :])
                plot_domains_as_pie(args, data, ax=ax2)
                handles = plot_domains_as_stack_chart(args, data, ax=ax3)
                ax3.set_frame_on(False)
                ax3.tick_params(labelright=True, right=False, left=False)
                ax3.grid(visible=True,
                         axis='y',
                         which='both',
                         color='black',
                         linestyle='-',
                         linewidth=0.5)
                ax3.grid(visible=False, axis='x')
                ax3.set_axisbelow('line')
                ax1.set_axis_off()
                ax1.legend(handles=handles, loc='center')
        else:
            with plot_utils.figure('domains/domains-joint.png',
                                   nrows=1,
                                   ncols=3,
                                   tight=True,
                                   a4=True,
                                   height_factor=0.35,
                                   grid_spec=True) as (fig, spec):
                ax1 = fig.add_subplot(spec[0, 2])
                ax2 = fig.add_subplot(spec[0, 0:2])
                plot_domains_as_pie(args, data, ax=ax1)
                handles = plot_domains_as_stack_chart(args, data, ax=ax2)
                ax2.set_frame_on(False)
                ax2.tick_params(labelright=True, right=False, left=False)
                ax2.grid(visible=True,
                         axis='y',
                         which='both',
                         color='black',
                         linestyle='-',
                         linewidth=0.5)
                ax2.grid(visible=False, axis='x')
                ax2.set_axisbelow('line')
                ax2.legend(loc='upper left')

####################################################################################################
####################################################################################################
# Artefacts
####################################################################################################


@utils.easy_log('Plotting Artefacts')
def plot_artefacts(args, data: list[data_loading.DataLoader]):
    plot_artefacts_as_upset_chart(args, data)
    plot_artefacts_as_upset_chart_by_domain(args, data)


@utils.easy_log('Plotting Artefacts as Upset Chart')
#@crossref_data.cached
def plot_artefacts_as_upset_chart(args, data: list[data_loading.DataLoader]):
    order = [
        # pure source code
        'source code (commit/diff/changeset)',
        'source code pair (different languages)',
        'source code (file)',
        'source code (function/snippet)',
        'source code (multiple files/project)',
        # heterogeneous -- source code + something else
        'design pattern specifications',
        'repository',
        # non-source code
        'tags/topics',
        'user data (e.g. github)',
        # machine generated
        'compiler error information',
        # natural language
        'bug reports/issues/work items',
        'comment',
        'commit message',
        'markdown text (Jupyter Notebook)',
        'questions/answers',
        'source code summary'
    ]
    translate = {
        'bug reports/issuses/work items': 'bug reports/issues/work items'
    }
    artefact_items = []
    for study in data:
        art = study.artefacts
        if 'self-generated ast' in art:
            art.remove('self-generated ast')
        if not art:
            continue
        artefact_items.append(
            #sorted([translate.get(x, x) for x in art], key=order.index)
            [translate.get(x, x) for x in art]
        )
    #artefact_items.sort(key=lambda row: min(order.index(y) for y in row))
    #df = upsetplot.from_memberships(artefact_items)
    #print(df.head())
    df = plot_utils.from_memberships(artefact_items, categories=order)
    with plot_utils.figure('artefacts/artefacts-as-upset.png',
                           nrows=2,
                           ncols=2,
                           tight=3) as (fig, axes):
        plot_utils.upset_plot(df, fig, axes, use_native_order=True)


@utils.easy_log('Plotting Artefacts as Upset Chart By Domain')
def plot_artefacts_as_upset_chart_by_domain(args, data: list[data_loading.DataLoader]):
    studies_by_domain = collections.defaultdict(list)
    for study in data:
        for domain in study.domains:
            studies_by_domain[domain].append(study)
    for domain, studies in studies_by_domain.items():
        df = upsetplot.from_memberships([study.artefacts for study in studies])
        with plot_utils.figure(f'artefacts/artefacts-as-upset-by-domain-{domain}.png',
                               nrows=2,
                               ncols=2,
                               tight=3) as (fig, axes):
            plot_utils.upset_plot(df, fig, axes)


####################################################################################################
####################################################################################################
# Features
####################################################################################################


def plot_features(args, data: list[data_loading.DataLoader]):
    plot_global_node_feature_types_as_barh(args, data)
    plot_global_edge_features_as_barh(args, data)
    plot_global_other_features_as_barh(args, data)
    plot_global_node_feature_types_as_upset(args, data)
    plot_global_edge_features_as_upset(args, data)
    plot_global_other_features_as_upset(args, data)
    plot_node_feature_encoding_strategies(args, data)
    plot_edge_feature_encoding_strategies(args, data)
    plot_other_feature_encoding_strategies(args, data)
    plot_features_joint(args, data)


@utils.easy_log('Plotting Features Joint')
def plot_features_joint(args, data: list[data_loading.DataLoader]):
    keys = [
        [
            'node feature (internal)',
            'node feature (terminal)',
            'node feature (root/terminal)',
            'node feature',
        ],
        [
            'edge feature',
        ],
        [
            'other',
        ]
    ]
    plot_data = [
        ('Node Features', 'b'),
        ('Edge Features', 'r'),
        ('Other Features', 'g')
    ]
    histograms = []
    for key_set in keys:
        total = collections.Counter()
        for study in data:
            attrs = _deduplicate_keys(study.features, *key_set)
            attrs = map(_remove_brackets, attrs)
            total += collections.Counter(attrs)
        total = {k: v for k, v in total.items() if v >= args.min_feature_count}
        histograms.append(total)
    with plot_utils.figure('features/features-joint.png',
                           height_size_hint=0.75,
                           a4=True,
                           nrows=1,
                           share_y=False) as (fig, axes):
        ax = axes
        offset = 0
        labels = []
        for (title, color), histogram in zip(plot_data, histograms):
            y_values = [y + offset for y in range(len(histogram))]
            categories = list(histogram)
            handles = ax.barh(y_values,
                              [histogram[c] for c in categories],
                              color=color,
                              label=title)
            ax.bar_label(handles, padding=3)
            offset += len(histogram)
            labels.extend(categories)
        ax.set_yticks(list(range(offset)), labels)
        ax.legend(bbox_to_anchor=(0, 1.02, 1, 0.2),
                  loc="lower left",
                  mode="expand",
                  borderaxespad=0,
                  ncol=1)


@utils.easy_log('Plotting Global Node Feature Types as Bar Chart')
def plot_global_node_feature_types_as_barh(args, data: list[data_loading.DataLoader]):
    features = [
        'node feature (internal)',
        'node feature (terminal)',
        'node feature (root/terminal)',
        'node feature',
    ]
    plot_global_feature_types_as_barh(args, data, features, 'features/global-node-feature-types-as-barh.png')


@utils.easy_log('Plotting Global Edge Feature Types as Bar Chart')
def plot_global_edge_features_as_barh(args, data: list[data_loading.DataLoader]):
    features = [
        'edge feature',
    ]
    plot_global_feature_types_as_barh(args, data, features, 'features/global-edge-feature-types-as-barh.png')


@utils.easy_log('Plotting Global Other Feature Types as Bar Chart')
def plot_global_other_features_as_barh(args, data: list[data_loading.DataLoader]):
    features = [
        'other',
    ]
    plot_global_feature_types_as_barh(args, data, features, 'features/global-other-feature-types-as-barh.png')


@utils.easy_log('Plot global feature types as barh')
def plot_global_feature_types_as_barh(args, data: list[data_loading.DataLoader], keys, filename):
    total = collections.Counter()
    for study in data:
        # for feature in study.features:  # Features by graph!
        #     for feat in keys:
        #         attrs = feature.get_next_attribute_level(feat)
        #         attrs = map(_remove_brackets, attrs)
        #         total += collections.Counter(attrs)
        attrs = _deduplicate_keys(study.features, *keys)
        attrs = map(_remove_brackets, attrs)
        total += collections.Counter(attrs)
    total = {k: v for k, v in total.items() if v >= args.min_feature_count}
    with plot_utils.figure(filename, height_size_hint=0.5, a4=True) as (fig, ax):
        plot_utils.barh_chart_from_dict(total, ax)


@utils.easy_log('Plotting Global Node Features as Upset Chart')
def plot_global_node_feature_types_as_upset(args, data: list[data_loading.DataLoader]):
    features = [
        'node feature (internal)',
        'node feature (terminal)',
        'node feature (root/terminal)',
        'node feature',
    ]
    plot_global_feature_types_as_upset(
        args, data, features, 'features/global-node-feature-types-as-upset.png'
    )


@utils.easy_log('Plotting Global Edge Features as Upset Chart')
def plot_global_edge_features_as_upset(args, data: list[data_loading.DataLoader]):
    features = [
        'edge feature',
    ]
    plot_global_feature_types_as_upset(
        args, data, features, 'features/global-edge-feature-types-as-upset.png'
    )


@utils.easy_log('Plotting Global Other Features as Upset Chart')
def plot_global_other_features_as_upset(args, data: list[data_loading.DataLoader]):
    features = [
        'other',
    ]
    plot_global_feature_types_as_upset(
        args, data, features, 'features/global-other-feature-types-as-upset.png'
    )


@utils.easy_log('Plot global feature types as upset')
def plot_global_feature_types_as_upset(args, data: list[data_loading.DataLoader], keys, filename):
    df = upsetplot.from_memberships(
        [
            [
                _remove_brackets(item)
                for feature in study.features
                for feat in keys
                for item in feature.get_next_attribute_level(feat)
            ]
            for study in data
         ]
    )
    with plot_utils.figure(filename,
                           nrows=2,
                           ncols=2,
                           tight=3) as (fig, axes):
        plot_utils.upset_plot(df, fig, axes, min_size=args.min_feature_upset)


@utils.easy_log('Plotting Node Feature Encoding Strategies')
def plot_node_feature_encoding_strategies(args, data: list[data_loading.DataLoader]):
    plot_feature_encoding_strategies(
        args,
        data,
        keys=[
            'node feature (internal)',
            'node feature (terminal)',
            'node feature (root/terminal)',
            'node feature',
        ],
        filename='features/node-feature-encoding-strategies.png',
        overwrite_encoding={
            'time dependent': None,
            'real number (ordinal)': 'ordinal',
            'or token(s) for identifier nodes) (embedding layer': 'embedding layer',
            'embedding model': 'custom embedding model',
            'modified node2vec': 'node2vec',
            'terminal, nonterminal, value) (not specified': 'n/a',
            'jointly embedded using document embedding': None,
            'label encoding': 'ordinal encoding',
            'ordinal': 'ordinal encoding'
        }
    )


@utils.easy_log('Plotting Edge Feature Encoding Strategies')
def plot_edge_feature_encoding_strategies(args, data: list[data_loading.DataLoader]):
    plot_feature_encoding_strategies(
        args,
        data,
        keys=['edge feature'],
        filename='features/edge-feature-encoding-strategies.png',
        overwrite_encoding={}
    )


@utils.easy_log('Plotting Other Feature Encoding Strategies')
def plot_other_feature_encoding_strategies(args, data: list[data_loading.DataLoader]):
    plot_feature_encoding_strategies(
        args,
        data,
        keys=['other'],
        filename='features/other-feature-encoding-strategies.png',
        overwrite_encoding={}
    )


@utils.easy_log('Plotting Feature Encoding Strategies')
def plot_feature_encoding_strategies(args,
                                     data: list[data_loading.DataLoader],
                                     keys,
                                     filename,
                                     overwrite_encoding):
    strategies = collections.defaultdict(lambda: collections.defaultdict(int))
    for study in data:
        for feature in study.features:
            for feat in keys:
                attrs = feature.get_next_attribute_level(feat)
                for name, encoding in zip(map(_remove_brackets, attrs), map(_get_bracket_part, attrs)):
                    encoding = overwrite_encoding.get(encoding, encoding)
                    if encoding is None:
                        continue
                    strategies[name][encoding] += 1
    for key in list(strategies):
        if len(strategies[key]) == 1 and 'n/a' in strategies[key]:
            # print('Dropping key:', key)
            del strategies[key]
    transposed = {}
    for key_1, inner in strategies.items():
        for key_2, value in inner.items():
            transposed.setdefault(key_2, {})[key_1] = value
    lonely = set()
    for key_1, inner in strategies.items():
        if len(inner) > 1:
            continue
        for key_2, c in inner.items():
            if len(transposed[key_2]) > 1 and c == 1:
                continue
            lonely.add(key_1)
    for k in lonely:
        # print('Dropping key [L]: ', k)
        del strategies[k]
    converted = {(k1, k2): v for k1, inner in strategies.items() for k2, v in inner.items()}
    with plot_utils.figure(filename) as (fig, ax):
        plot_utils.categorical_bubble_plot(converted, ax, r_max=2)


def _remove_brackets(item: str) -> str:
    try:
        index = item.index('(')
    except ValueError:
        return item
    else:
        return item[:index].strip()


def _get_bracket_part(item: str) -> str:
    try:
        index = item.index('(')
    except ValueError:
        return 'n/a'
    else:
        return item[index+1:].strip().removesuffix(')')


####################################################################################################
####################################################################################################
# Models
####################################################################################################


@utils.easy_log('Plotting Models')
def plot_models(args, data: list[data_loading.DataLoader]):
    plot_models_by_type(args, data)
    plot_models_by_domain(args, data)
    plot_models_by_year(args, data)
    plot_models_by_type_as_upset(args, data)
    plot_graph_pooling_as_barh(args, data)
    plot_node_transforms_as_barh(args, data)
    plot_gnn_message_passing_models(args, data)
    plot_the_remaining_stuff(args, data)
    plot_tree_stuff(args, data)
    plot_classic_models(args, data)
    plot_pooling_as_starburst(args, data)


@utils.easy_log('Plotting Models by Type')
def plot_models_by_type(args, data: list[data_loading.DataLoader]):
    models_by_type = collections.defaultdict(int)
    for study in data:
        for model in study.models:
            model_type = '/'.join(
                sorted(
                    model.get_attributes('base-type')
                )
            )
            models_by_type[model_type] += 1
    with plot_utils.figure('models/models-by-type.png') as (fig, ax):
        plot_utils.barh_chart_from_dict(models_by_type, ax)


@utils.easy_log('Plotting models by type as upset plot')
def plot_models_by_type_as_upset(args, data: list[data_loading.DataLoader]):
    models = [m.get_attributes('base-type') for study in data for m in study.models]
    df = upsetplot.from_memberships(models)
    with plot_utils.figure('models/models-by-type-as-upset.png',
                           nrows=2,
                           ncols=2,
                           tight=3) as (fig, axes):
        plot_utils.upset_plot(df, fig, axes)


@utils.easy_log('Plotting Models by Domain')
def plot_models_by_domain(args, data: list[data_loading.DataLoader]):
    models_by_domain = collections.defaultdict(lambda: collections.defaultdict(int))
    for study in data:
        for model in study.models:
            for domain in set(study.domains):
                model_type = '/'.join(
                    sorted(
                        model.get_attributes('base-type')
                    )
                )
                for model_type in model.get_attributes('base-type'):
                    models_by_domain[domain][model_type] += 1
    with plot_utils.figure('models/models-by-domain.png') as (fig, ax):
        plot_utils.bar_chart_from_nested_dict(models_by_domain, ax)


@utils.easy_log('Plotting Models by Year')
def plot_models_by_year(args, data: list[data_loading.DataLoader]):
    models_by_year = collections.defaultdict(lambda: collections.defaultdict(int))
    for study in data:
        for model in study.models:
            # model_type = '/'.join(
            #     sorted(
            #         model.get_attributes('base-type')
            #     )
            # )
            for model_type in model.get_attributes('base-type'):
                models_by_year[model_type][study.year] += 1
    with plot_utils.figure('models/models-by-year.png') as (fig, ax):
        plot_utils.stack_chart_from_dict(models_by_year, ax)


@utils.easy_log('Plotting Graph Pooling')
def plot_graph_pooling_as_barh(args, data: list[data_loading.DataLoader]):
    pooling_methods = collections.defaultdict(int)
    for study in data:
        # for model in study.models:
        #     for attr in model.get_attributes('gnn-functionality: pooling'):
        #         pooling_methods[attr] += 1
        for attr in _deduplicate_keys(study.models, 'gnn-functionality: pooling'):
            pooling_methods[attr] += 1
    with plot_utils.figure('models/graph-pooling-as-barh.png') as (fig, ax):
        plot_utils.barh_chart_from_dict(pooling_methods, ax)


@utils.easy_log('Plotting Node transforms')
def plot_node_transforms_as_barh(args, data: list[data_loading.DataLoader]):
    methods = collections.defaultdict(int)
    for study in data:
        # for model in study.models:
        #     for attr in model.get_attributes('gnn-functionality: node-transform'):
        #         methods[attr] += 1
        for attr in _deduplicate_keys(study.models, 'gnn-functionality: node-transform'):
            methods[attr] += 1
    with plot_utils.figure('models/node-transforms-as-barh.png') as (fig, ax):
        plot_utils.barh_chart_from_dict(methods, ax)


@utils.easy_log('Plotting GNN message passing models')
def plot_gnn_message_passing_models(args, data: list[data_loading.DataLoader]):
    adjustments = {
        'custom edge-type aware message passing scheme': 'custom GNN layer',
        'custom message passing scheme': 'custom GNN layer',
        'custom edge-type aware message passing scheme w. attention': 'custom GNN layer'
    }
    methods = collections.defaultdict(int)
    for study in data:
        #for model in study.models:
        #    for attr in model.get_attributes('gnn-functionality: gnn'):
        #        methods[attr] += 1
        for attr in _deduplicate_keys(study.models, 'gnn-functionality: gnn'):
            methods[adjustments.get(attr, attr)] += 1
    methods = {k: v for k, v in methods.items() if v >= args.min_gnn_count}
    with plot_utils.figure('models/gnn-message-passing-as-barh.png', a4=True, height_size_hint=0.35) as (fig, ax):
        plot_utils.barh_chart_from_dict(methods, ax)


@utils.easy_log('Plotting tree stuff')
def plot_tree_stuff(args, data: list[data_loading.DataLoader]):
    adjustments = {
        'transformer (first bottom up w. attention, then top down without attention)': 'tree transformer',
        'tree-lstm variant': 'tree-LSTM',
        'tree-lstm': 'tree-LSTM',
        'child-sum tree-lstm': 'tree-LSTM',
        'recursively applied bottom-up auto-encoder for node embeddings': 'recursive bottom-up auto-encoder',
        'cnn over sequence, but based on original tree structure': 'tree adjusted CNN'
    }
    methods = collections.defaultdict(int)
    for study in data:
        # for model in study.models:
        #     for attr in model.get_attributes('gnn-functionality: tree'):
        #         methods[attr] += 1
        for attr in _deduplicate_keys(study.models, 'gnn-functionality: tree'):
            methods[adjustments.get(attr, attr)] += 1
    methods = {k: v for k, v in methods.items() if v >= args.min_tree_count}
    with plot_utils.figure('models/tree-stuff-as-barh.png', a4=True, height_size_hint=0.25) as (fig, ax):
        plot_utils.barh_chart_from_dict(methods, ax)


@utils.easy_log('Plotting the remaining stuff')
def plot_the_remaining_stuff(args, data: list[data_loading.DataLoader]):
    hist = collections.defaultdict(int)
    for study in data:
        unique = set()
        for model in study.models:
            attrs = model.get_attributes_complement(
                'gnn-functionality: node-transform',
                'gnn-functionality: gnn',
                'gnn-functionality: pooling',
                'gnn-functionality: tree',
                prefix='gnn-functionality'
            )
            # for attr in attrs:
            #     hist[attr] += 1
            unique |= set(attrs)
        for attr in unique:
            hist[attr] += 1
    with plot_utils.figure('models/the-remaining-stuff-as-barh.png') as (fig, ax):
        plot_utils.barh_chart_from_dict(hist, ax)


@utils.easy_log('Plotting Classic Models')
def plot_classic_models(args, data: list[data_loading.DataLoader]):
    models = collections.defaultdict(int)
    translation_map = {}
    classic = {
        'clustering: spectral clustering',
        'clustering: k-means',
        'clustering: agglomerative clustering w. graph kernel'
    }
    for study in data:
        unique = set()
        for model in study.models:
            type_info = model.get_attributes('base-type')
            if 'clustering' in type_info or 'classic' in type_info:
                assert len(type_info) == 1
                attrs = model.get_attributes('misc: model')
                has_adaboost = 'meta: adaboost' in attrs
                if has_adaboost:
                    attrs.remove('meta: adaboost')
                for key in attrs:
                    if key.startswith('misc:'):
                        key = key.replace('misc:', 'other:')
                    if key.startswith('ranking:'):
                        key = key.replace('ranking:', 'other:')
                    if has_adaboost:
                        unique.add(f'{key} (with adaboost)')
                    else:
                        unique.add(key)
                    if model.cluster is not None:
                        prefix, _ = key.rsplit(': ', 1)
                        if key in classic:
                            translation_map[key] = f'{prefix}: {model.cluster} (generic algorithm)'
                        else:
                            translation_map[key] = f'{prefix}: {model.cluster}'
        for x in unique:
            models[x] += 1
    for key, value in translation_map.items():
        models[value] += models.pop(key)
    models_as_tree = {}
    while models:
        key, value = models.popitem()
        parts = key.split(': ')
        current = models_as_tree
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value
    with adjusted_font_scale(1):
        with plot_utils.figure('models/classic-models.png', a4=True, height_size_hint=0.53) as (fig, ax):
            sb = plot_utils.Sunburst(radius=1, x_to_y_axis_ratio=1 / 0.53, y_stretch=1.1)
            sb.plot(models_as_tree, ax)


@utils.easy_log('Plotting Pooling By Type')
def plot_pooling_as_starburst(args, data: list[data_loading.DataLoader]):
    pooling_methods = collections.defaultdict(int)
    for study in data:
        # for model in study.models:
        #     for attr in model.get_attributes('gnn-functionality: pooling'):
        #         pooling_methods[attr] += 1
        for attr in _deduplicate_keys(study.models, 'gnn-functionality: pooling'):
            pooling_methods[attr] += 1
    pooling_categories = {
        'graph paths: mean pooling': ['summing', 'mean pooling'],
        'graph: attention weighted sum': ['summing', 'attention weighted sum'],
        'graph: bidirectional lstm': ['misc', 'bidirectional lstm'],
        'graph: combined sum and max pooling': ['misc', 'combined sum and max pooling'],
        'graph: conv w. max pooling over node feature matrix': ['misc', 'conv w. max pooling over node feature matrix'],
        'graph: dmonpooling': ['graph coarsening', 'DMoNPool'],
        'graph: dynamic pooling': ['misc', 'max pooling'],
        'graph: edge pooling': ['graph coarsening', 'edge pooling'],
        'graph: global attention pooling': ['summing', 'global attention pooling'],
        'graph: graph pooling (reduce nodes by half)': ['node sampling', 'unspecified'],
        'graph: h-sagpool': ['node sampling', 'SAGPool'],
        'graph: hierarchical self-attention graph pooling': ['node sampling', 'SAGPool'],
        'graph: max pooling': ['misc', 'max pooling'],
        'graph: mean biaffine attention pooling': ['misc', 'mean bi-affine attention pooling'],
        'graph: mean pooling': ['summing', 'mean pooling'],
        'graph: mincutpool': ['graph coarsening', 'MinCutPool'],
        'graph: sagpool': ['node sampling', 'SAGPool'],
        'graph: set2set': ['misc', 'set2set'],
        'graph: sigmoid attention sum': ['summing', 'gated sum'],
        'graph: sort pooling': ['node sampling', 'SortPooling'],
        'graph: sum pooling': ['summing', 'sum'],
        'graph: top-k pooling': ['node sampling', 'top-k pooling'],
        'graph: unspecified': ['unspecified'],
        'graph: weighted sum pooling': ['summing', 'weighted sum'],
        'node-type: mean pooling': ['summing', 'mean pooling'],
        'tree: bottom-up attention weighted sum of self and child nodes': ['summing', 'attention weighted sum'],
        'tree: child-sum pooling': ['summing', 'child-sum']
    }
    pooling = {}
    for key, value in pooling_methods.items():
        current = pooling
        if not pooling_categories[key]:
            continue
        *path, last = pooling_categories[key]
        for p in path:
            p = p.replace(' ', '\n')
            current = current.setdefault(p, {})
        if last not in current:
            current[last] = 0
        current[last] += value
    with adjusted_font_scale(1):
        with plot_utils.figure('models/pooling-by-type.png', a4=True, height_size_hint=0.6) as (fig, ax):
            sb = plot_utils.Sunburst(radius=1,
                                     x_to_y_axis_ratio=1 / 0.6,
                                     y_stretch=1.2)
            alignment = {
                'misc': {
                    'combined sum and max pooling': {'horizontal': 'right', 'vertical': 'center'},
                    # The stack
                    'mean bi-affine attention pooling': {'horizontal': 'right',
                                                         'vertical': 'bottom',
                                                         'raise-by': 0.1},
                    'set2set': {'horizontal': 'right',
                                'vertical': 'bottom',
                                'raise-by': 0.25},
                    'conv w. max pooling over node feature matrix': {'horizontal': 'left',
                                                                     'vertical': 'bottom',
                                                                     'raise-by': 0.2},
                    'bidirectional lstm': {'horizontal': 'left',
                                           'vertical': 'bottom',
                                           'raise-by': 0.05},
                },
                'summing': {
                    'weighted sum': {'horizontal': 'right', 'vertical': 'bottom'},
                },
                'node\nsampling': {
                    'SAGPool': {'horizontal': 'left', 'vertical': 'top'},
                    'unspecified': {'horizontal': 'left', 'vertical': 'top'},
                },
                'graph\ncoarsening': {
                    'DMonPool': {'horizontal': 'left', 'vertical': 'top'},
                    'edge pooling': {'horizontal': 'left', 'vertical': 'bottom'},
                },
                'unspecified': {'horizontal': 'left', 'vertical': 'center', 'raise-by': 0.1}
            }
            sb.plot(pooling, ax, alignment_override=alignment)


def _deduplicate_keys(iterator, *keys: str):
    result = set()
    for item in iterator:
        for key in keys:
            for attr in item.get_attributes(key):
                result.add(attr)
    return result


####################################################################################################
####################################################################################################
# Graphs
####################################################################################################


@utils.easy_log('Plotting Graphs')
def plot_graphs(args, data: list[data_loading.DataLoader]):
    plot_graph_vertices(args, data)
    plot_graph_edges(args, data)
    plot_graph_edges_as_upset(args, data)
    plot_graph_edges_as_upset_by_domain(args, data)


@utils.easy_log('Plotting Graph Vertices as Bar Chart')
def plot_graph_vertices(args, data: list[data_loading.DataLoader]):
    counts = collections.defaultdict(int)
    for study in data:
        for graph in study.graphs:
            for vertex in graph.parse().vertices:
                counts[vertex.value] += 1
    counts = {k: v for k, v in counts.items() if v >= args.min_vertex_count}
    with plot_utils.figure('graphs/graph-vertices.png', a4=True, height_size_hint=0.5) as (fig, ax):
        plot_utils.barh_chart_from_dict(counts, ax)


@utils.easy_log('Plotting Graph Edges as Bar Chart')
def plot_graph_edges(args, data: list[data_loading.DataLoader]):
    counts = collections.defaultdict(int)
    for study in data:
        for graph in study.graphs:
            for edge in graph.parse().edges:
                counts[edge.value] += 1
    counts = {k: v for k, v in counts.items() if v >= args.min_edge_count}
    with plot_utils.figure('graphs/graph-edges.png', a4=True, height_size_hint=0.5) as (fig, ax):
        plot_utils.barh_chart_from_dict(counts, ax)


@utils.easy_log('Plotting Graph Edges as Upset Plot')
def plot_graph_edges_as_upset(args, data: list[data_loading.DataLoader]):
    edges = [sorted([e.value for e in g.parse().edges]) for study in data for g in study.graphs]
    hist = collections.defaultdict(int)
    for col in edges:
        hist[tuple(col)] += 1
    edges = [e for e in edges if hist[tuple(e)] >= args.min_edge_upset]
    df = upsetplot.from_memberships(edges)
    with plot_utils.figure('graphs/graph-edges-as-upset.png',
                           nrows=2,
                           ncols=2,
                           tight=3) as (fig, axes):
        plot_utils.upset_plot(df, fig, axes, min_size=args.min_edge_upset)


@utils.easy_log('Plotting Graph Edges as Upset Plot By Domain')
def plot_graph_edges_as_upset_by_domain(args, data: list[data_loading.DataLoader]):
    studies_by_domain = collections.defaultdict(list)
    for study in data:
        for domain in study.domains:
            studies_by_domain[domain].append(study)
    hist = collections.defaultdict(int)
    all_edges = [sorted([e.value for e in g.parse().edges]) for study in data for g in study.graphs]
    for col in all_edges:
        hist[tuple(col)] += 1
    for domain, studies in studies_by_domain.items():
        edges = [sorted([e.value for e in g.parse().edges])
                 for study in studies for g in study.graphs]
        edges = [e for e in edges if hist[tuple(e)] > 1]
        df = upsetplot.from_memberships(edges)
        with plot_utils.figure(f'graphs/graph-edges-as-upset-by-domain-{domain}.png',
                               nrows=2,
                               ncols=2,
                               tight=3) as (fig, axes):
            plot_utils.upset_plot(df, fig, axes, min_size=args.min_edge_upset_domains)


####################################################################################################
####################################################################################################
# Main
####################################################################################################


@utils.easy_log('Loading Data')
def load_data() -> list[data_loading.DataLoader]:
    ids = data_loading.get_all_paper_ids()
    with alive_progress.alive_bar(len(ids)) as bar:
        result = []
        for key in ids:
            result.append(data_loading.load_data(key))
            bar()
        return result


def main(args):
    data = load_data()
    with warnings.catch_warnings(action='ignore'):
        match args.category:
            case 'domains':
                plot_domains(args, data)
            case 'artefacts':
                plot_artefacts(args, data)
            case 'models':
                plot_models(args, data)
            case 'features':
                plot_features(args, data)
            case 'graphs':
                plot_graphs(args, data)
            case _:
                raise ValueError(f'Unknown category {args.category}')
        pass


if __name__ == '__main__':
    # Setup parsers
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(dest='category')
    domains = subparser.add_parser('domains')
    artefacts = subparser.add_parser('artefacts')
    models = subparser.add_parser('models')
    features = subparser.add_parser('features')
    graphs = subparser.add_parser('graphs')
    # Add arguments
    # Artefacts
    pass
    # Domains
    pass
    # Features
    features.add_argument('--min-feature-count', type=int, default=1)
    features.add_argument('--min-feature-upset', type=int, default=1)
    features.add_argument('--min-encoding-count', type=int, default=1)
    # Graphs
    graphs.add_argument('--min-vertex-count', type=int, default=1)
    graphs.add_argument('--min-edge-count', type=int, default=1)
    graphs.add_argument('--min-edge-upset', type=int, default=1)
    graphs.add_argument('--min-edge-upset-domains', type=int, default=1)
    # Models
    models.add_argument('--min-gnn-count', type=int, default=1)
    models.add_argument('--min-tree-count', type=int, default=1)
    # Call main
    args = parser.parse_args()
    main(args)
