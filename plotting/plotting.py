#! ../venv/bin/python

####################################################################################################
####################################################################################################
# Imports, Constants, Config
####################################################################################################

import argparse
import collections
import contextlib
import math
import os
import re
import statistics
import warnings
import sys

import alive_progress
import matplotlib.pyplot as pyplot

sys.path.insert(0, os.path.abspath('./UpSetPlot'))
import upsetplot
if upsetplot.__file__ != os.path.abspath('./UpSetPlot/upsetplot/__init__.py'):
    raise ValueError('Not using local upsetplot. Is the submodule initialised?')

import data_loading
import utils
import plot_utils

import seaborn


@contextlib.contextmanager
def adjusted_font_scale(scale):
    _set_seaborn_theme(scale)
    yield
    _set_seaborn_theme(FONT_SCALE)


@contextlib.contextmanager
def adjusted_font_size(font_size):
    _set_seaborn_theme(1.0, font_size=font_size)
    yield
    _set_seaborn_theme(1.0)


def _set_seaborn_theme(font_scale, *, font_size=10):
    if font_scale != 1 and PAPER_ONLY:
        warnings.warn('Font scale is ignored in paper_only mode')
        font_scale = 1
        rc_extra = {
            "font.size": font_size,
            "axes.titlesize": font_size,
            "axes.labelsize": font_size,
            'xtick.labelsize': font_size,
            'ytick.labelsize': font_size,
        }
    else:
        rc_extra = {}
    seaborn.set_theme(
        context='paper',
        rc={
            'patch.force_edgecolor': False,  # No edge color to keep stack chart readable
            'grid.color': 'grey',
            'xtick.bottom': True,
            **rc_extra
        },
        font_scale=font_scale
    )


PAPER_ONLY = False
FONT_SCALE = 1.5
_set_seaborn_theme(FONT_SCALE)
pyplot.rcParams["font.family"] = "Hack"


# DOUBLE_COLUMN_SIZE = plot_utils.NiceFigure.mm_to_inches((210, 280))
# SINGLE_COLUMN_SIZE = plot_utils.NiceFigure.mm_to_inches((210 / 2, 280))

SINGLE_COLUMN_SIZE = (
    plot_utils.NiceFigure.mm_to_inches(255), plot_utils.NiceFigure.mm_to_inches(240),
)
DOUBLE_COLUMN_SIZE = (
    plot_utils.NiceFigure.points_to_inches(539), plot_utils.NiceFigure.mm_to_inches(240),
)
THICK_COLUMN_SIZE = (
    plot_utils.NiceFigure.points_to_inches(397), plot_utils.NiceFigure.mm_to_inches(240),
)

FIGURE_OFFSET = 2


def capitalize(x: str) -> str:
    known_abbreviations = {
        'gnn': 'GNN',
        'gcn': 'GCN',
        'gat': 'GAT',
        'ggnn': 'GGNN',
        'rgcn': 'R-GCN',
        'github': 'GitHub',
        'jupyter': 'Jupyter',
        'ast': 'AST',
        'ncs': 'NCS',
        'cbow': 'CBOW',
        'cbow/skipgram': 'CBOW/Skipgram',
        'mlp': 'MLP',
        'cnn': 'CNN',
        'rnn': 'RNN',
        'knn': 'KNN',
        'svm': 'SVM',
        'pagerank': 'PageRank',
        'graphsage': 'GraphSAGE',
        'gin': 'GIN',
        'tree-lstm': 'Tree-LSTM',
        'tree adjusted cnn': 'Tree-adjusted CNN',
        'tbcnn': 'TBCNN',
        'sortpooling': 'SortPooling',
        'set2set': 'Set2Set',
        'mincutpool': 'MinCutPool',
        'dmonpool': 'DMoNPool'
    }
    x = x.lower()
    words, splits = _split_map(x)
    words = [known_abbreviations.get(y, y) for y in words]
    if words[0].islower():
        words[0] = words[0].capitalize()
    return _join_map(words, splits)


def _split_map(x: str):
    chars = [' ', '(', ')', '/', '\n']
    pattern = '|'.join(re.escape(c) for c in chars)
    atoms = re.split(pattern, x)
    joiners = [c for c in x if c in chars]
    return atoms, joiners


def _join_map(x, y):
    parts = []
    assert len(x) == len(y) + 1
    for a, b in zip(x, y):
        parts.append(a)
        parts.append(b)
    parts.append(x[-1])
    return ''.join(parts)


####################################################################################################
####################################################################################################
# Domains
####################################################################################################


@utils.easy_log('Plotting Domain Charts')
def plot_domains(args, data: list[data_loading.DataLoader]):
    if not args.paper_only:
        plot_domains_as_pie(args, data)
        plot_domains_as_stack_chart(args, data)
    plot_domains_joint(args, data)
    plot_domains_as_pie_with_annotations(args, data)


@utils.easy_log('Plotting Domain Pie Chart')
def plot_domains_as_pie(args, data: list[data_loading.DataLoader], ax=None):
    """Plot the domains as a pie chart."""
    hist = collections.defaultdict(int)
    for x in data:
        for domain in x.domains:
            if domain == 'general graph learning framework for code':
                domain = 'general purpose frameworks'
            hist[capitalize(domain)] += 1
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


def _split_outer(s: str) -> list[str]:
    opened = 0
    points = []
    for index, char in enumerate(s):
        if char == '{':
            opened += 1
        elif char == '}':
            opened -= 1
        #if opened == 0 and char == '/':
        #    break
        if opened == 0 and char == ',':
            points.append(index)
    # Split in all collected indices
    result = []
    offset = 0
    for point in points:
        result.append(s[offset:point])
        offset = point + 1
    result.append(s[offset:])
    return result


def _parse_annotation(data: list[data_loading.DataLoader], anno: str, *, __prefix=None):
    if anno[0] == '{' and anno[-1] == '}':
        groups = _split_outer(anno[1:-1])
    else:
        groups = [anno]
    result = {}
    for group in groups:
        if '/' in group:
            first, remainder = group.split('/', maxsplit=1)
            first = first.replace('%', '/')
            path = [first] if not __prefix else [*__prefix, first]
            path = tuple(path)
            print('Checking', path)
            result[first] = {'$': sum(d.matches_domain_path(path) for d in data)}
            result[first] |= _parse_annotation(data, remainder, __prefix=path)
        else:
            group = group.replace('%', '/')
            path = [group] if not __prefix else [*__prefix, group]
            path = tuple(path)
            print('Checking', path)
            result[group] = {'$': sum(d.matches_domain_path(path) for d in data)}
    return result


def _prepare_annotation(title, data):
    lines = []
    idx_title = title if title != 'general purpose frameworks' else 'general graph learning framework for code'
    stack = [(title, data[idx_title], 0)]
    while stack:
        name, item, indent = stack.pop()
        lines.append((indent, f'{name} ({item["$"]})'))
        for key in sorted(item, reverse=True):
            if key == '$':
                continue
            stack.append((key, item[key], indent + 1))
    formatted_lines = [
        '    '*indent + f'\u2022 {text.capitalize()}'
        for indent, text in lines
    ]
    return '\n'.join(formatted_lines)


@utils.easy_log('Plotting domain pie chart with annotations')
def plot_domains_as_pie_with_annotations(args, data: list[data_loading.DataLoader]):
    """Plot the domains as a pie chart."""
    import warnings
    warnings.warn(
        'The annotations for the annotated domain pie chart are '
        'hard-coded and need manual adjustment for new data.'
    )
    # Data definitions
    misc_domains = [
        'algorithm recommendation',
        'automated code review (accept%reject)',
        'change propagation prediction (determine if code clones must co-evolve)',
        'code change embedding',
        'code performance prediction',
        'coding language migration',
        'commit classification',
        'commit untangling',
        'common code edit visualisation',
        'design pattern mining',
        'developer ability mining',
        'developer recommendation',
        'documentation assistance',
        'library recommendation',
        'log level prediction',
        'mapping of variables between programs',
        'microservice decomposition',
        'non-termination analysis of code',
        'program understanding assistance',
        'runtime configuration optimisation',
        'smell prediction & detection',
        'software modularisation',
        'static analysis output filtering (filter out false positives)',
        'code style improvement'
    ]
    annotation_groups = [
        'code generation/{code completion/api recommendation,code edit suggestion,code generation from prompt}',
        'code summarisation/{commit message generation,method name generation}',
        'defects & vulnerabilities/{defect & vulnerability prediction%detection,defect localisation/bug localisation/bug introduction detection,defect proneness prediction,defect repair,patch correctness prediction,vulnerability fixing commit detection,vulnerability prevention (predict future vulnerabilities introduced by specific users),vulnerability severity prediction,vulnerable community detection,dataset selection for cross-project bug prediction}',
        'general purpose methods/{SMOTE for code graphs,general finetunable graph embedding for code,general graph embedding pipeline for code,general graph learning for code research,general graph learning pipeline for code,general repository embedding pipeline}',
        'malicious code detection/{malicious repository detection,malicious script detection}',
        #f'misc/{{{",".join(misc_domains)}}}',
        'misc',
        'neural code search',
        'program semantics/{type prediction,variable name prediction,program semantics (code clones and code classification)/{code clone detection,program classification}}',
    ]
    annotation_group_renames = {
        'program semantics/program semantics (code clones and code classification)': None,    # Erase
        'defects & vulnerabilities/dataset selection for cross-project bug prediction': 'dataset selection',
        'defects & vulnerabilities/vulnerability prevention (predict future vulnerabilities introduced by specific users)': 'vulnerability prevention',
        #'misc/automated code review (accept%reject)': 'automated code review',
        #'misc/change propagation prediction (determine if code clones must co-evolve)': 'change propagation prediction',
        #'misc/static analysis output filtering (filter out false positives)': 'static analysis output filtering',
        'defects & vulnerabilities/defect & vulnerability prediction%detection': 'defect & vulnerability detection',
        'defects & vulnerabilities/defect localisation/bug localisation/bug introduction detection': 'defect introduction detection',
        'defects & vulnerabilities/defect localisation/bug localisation': None,
    }
    # Quick statistics for misc
    misc_numbs = []
    for subdomain in misc_domains:
        subdomain = subdomain.replace('%', '/')
        x = sum(d.matches_domain_path(('misc', subdomain)) for d in data)
        misc_numbs.append(x)
    print('Misc. Mean', statistics.mean(misc_numbs))
    print('Misc. Median', statistics.median(misc_numbs))

    for key in sorted(misc_domains):
        x = sum(d.matches_domain_path(('misc', key)) for d in data)
        print(f'{key.capitalize()} & {x} \\\\')

    # Main pie chart data collection
    hist = collections.defaultdict(int)
    for x in data:
        for domain in x.domains:
            #if domain == 'general graph learning framework for code':
            #    domain = 'general purpose frameworks'
            hist[capitalize(domain)] += 1
    labels = sorted(hist, key=lambda x: hist[x], reverse=True)
    values = [hist[label] for label in labels]
    total = sum(values)
    # Annotation data collection
    annotations = {}
    for group in annotation_groups:
        annotations |= _parse_annotation(data, group)

    #print(annotations)

    for key, value in annotation_group_renames.items():
        prev = None
        current = annotations
        last = None
        for part in key.split('/'):
            part = part.replace('%', '/')
            prev = current
            current = current[part]
            last = part
        if value is None:
            del prev[last]
            prev |= current
        else:
            del prev[last]
            prev[value] = current
    # Plotting
    if args.paper_only:
        context = plot_utils.NiceFigure(
            filename=f'figure_{FIGURE_OFFSET + 1}b.png',
            nrows=1,
            ncols=1,
            tight=True,
            page_size=DOUBLE_COLUMN_SIZE,
            width_to_height_ratio=1 / 0.5,
        )
    else:
        context = plot_utils.figure('domains/domains-as-pie-elaborate.png')
    if args.paper_only:
        # Works for fontsize = 6
        # offsets = {
        #     'misc': (0, 0.3),
        #     'code summarisation': (0, -0.1),
        #     'malicious code detection': (0, 0.0),
        #     'neural code search': (0, -0.05),
        #     'code generation': (0, -0.1),
        #     'program semantics': (0, -0.15)
        # }

        # Font size = 7
        offsets = {
            # 'misc': (0, 0.45),
            # 'code summarisation': (0, -0.35),
            # 'general purpose frameworks': (0, -0.25),
            'malicious code detection': (0, 0.1),
            'neural code search': (0, -0.0),
            'code generation': (0, -0.15),
            'program semantics': (0, -0.35),
            #'general purpose methods': (0, -0.1)
            'misc': (0, -0.1)
        }

        styles = {
            # 'misc': 'angle3,angleA=0,angleB={deg}', # 'angle3,armA=0,armB=0,fraction=0,angle={deg}',
            'malicious code detection': 'angle3,angleA=45,angleB={deg}',
        }
    else:
        offsets = {}
        styles = {}
    with context as (fig, ax):
        import matplotlib.axes
        assert isinstance(ax, matplotlib.axes.Axes)
        ax.pie(
            values,
        )
        cumulative = 0
        for label, count in zip(labels, values):
            angle = 2 * math.pi * (cumulative + count/2) / total
            x = math.cos(angle)
            y = math.sin(angle)
            alignment = 'left' if x >= 0 else 'right'
            connection_style = 'angle,angleA=0,angleB={deg}'
            dx, dy = offsets.get(label.lower(), (0, 0))
            ax.annotate(
                _prepare_annotation(label.lower(), annotations),
                xy=(x, y),
                xytext=(1.15*(1 if x >= 0 else -1) + dx, 1.1*y + dy),
                horizontalalignment=alignment,
                arrowprops={
                    'arrowstyle': '-',
                    'connectionstyle': styles.get(label.lower(), connection_style).format(deg=math.degrees(angle)),
                    'mutation_scale': 5,
                    'ec': 'k',
                    'fc': 'k',
                    'lw': 1
                },
                bbox={
                    'boxstyle': 'square,pad=0.3',
                    'fc': 'w', 'ec': 'k', 'lw': 0.72
                },
                zorder=0,
                va='center',
                multialignment='left',
                fontsize='x-large' if not args.paper_only else 7
            )
            # import matplotlib.patches
            # patch = matplotlib.patches.FancyArrowPatch(
            #     posA=(x, y),
            #     posB=(1.2*(1 if x >= 0 else -1), 1.1*y),
            #     arrowstyle='-',
            #     connectionstyle=f'angle,angleA=0,angleB={math.degrees(angle)}',
            #     fill=True,
            #     fc='k',
            #     ec='k',
            # )
            # ax.add_patch(patch)

            cumulative += count


@utils.easy_log('Plotting Domain Stack Chart')
def plot_domains_as_stack_chart(args, data: list[data_loading.DataLoader], ax=None):
    """Plot the domains as a stack plot"""
    # Compute count per domain per year
    count_per_domain_per_year = collections.defaultdict(lambda: collections.defaultdict(int))
    for z in data:
        for domain in z.domains:
            if domain == 'general graph learning framework for code':
                domain = 'general purpose frameworks'
            count_per_domain_per_year[capitalize(domain)][z.year] += 1
    if args.paper_only and ax is None:
        raise NotImplementedError
    else:
        if True:
            if ax is None:
                with plot_utils.figure('domains/domains-as-stack.png', tight=False) as (fig, ax):
                    return plot_utils.stack_chart_from_dict(count_per_domain_per_year, ax)
            else:
                return plot_utils.stack_chart_from_dict(count_per_domain_per_year, ax, draw_labels=False)


@utils.easy_log('Plotting Domains Joint')
def plot_domains_joint(args, data: list[data_loading.DataLoader]):
    if args.paper_only:
        with adjusted_font_scale(1):
            nice_fig = plot_utils.NiceFigure(filename=f'figure_{FIGURE_OFFSET + 1}.png',
                                       nrows=1,
                                       ncols=3,
                                       tight=True,
                                       page_size=DOUBLE_COLUMN_SIZE,
                                       width_to_height_ratio=1 / 0.4,
                                       render_axes=False,
                                       return_grid_spec=True)
            if True:
                with nice_fig as (fig, spec):
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
                    nice_fig.render_ax(ax2, 'a')
    else:
        with adjusted_font_scale(1):
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
    if not args.paper_only:
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
        'dependency files',
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
    order = [capitalize(x) for x in order]
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
            [capitalize(translate.get(x, x)) for x in art]
        )
    #artefact_items.sort(key=lambda row: min(order.index(y) for y in row))
    #df = upsetplot.from_memberships(artefact_items)
    #print(df.head())
    df = plot_utils.from_memberships(artefact_items, categories=order)
    if args.paper_only:
        with adjusted_font_size(10):
            with plot_utils.NiceFigure(f'figure_{FIGURE_OFFSET + 2}.png',
                                       nrows=2,
                                       ncols=3,
                                       page_size=DOUBLE_COLUMN_SIZE,
                                       width_to_height_ratio=1.5,
                                       tight=3) as (fig, axes):
                plot_utils.upset_plot(df, fig, axes, use_native_order=True, font_size=8)
    else:
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
    if not args.paper_only:
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
    if not args.paper_only:
        plot_domain_other_features_as_upset(args, data)
        plot_domain_node_features_as_barh(args, data)
        plot_domain_other_features_as_upset(args, data)
        plot_domain_node_features_as_barh(args, data)


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
            attrs = map(capitalize, attrs)
            total += collections.Counter(attrs)
        total = {k: v for k, v in total.items() if v >= args.min_feature_count}
        histograms.append(total)
    if args.paper_only:
        with adjusted_font_scale(1):
            with plot_utils.NiceFigure(f'figure_{FIGURE_OFFSET + 5}.png',
                                       width_to_height_ratio=1.5,
                                       page_size=THICK_COLUMN_SIZE) as (fig, axes):
                ax = axes
                offset = 0
                labels = []
                symbols = ['///', 'xxx', '|||']
                for (title, color), histogram, symbol in zip(plot_data, histograms, symbols):
                    y_values = [y + offset for y in range(len(histogram))]
                    categories = list(histogram)
                    handles = ax.barh(y_values,
                                      [histogram[c] for c in categories],
                                      color=color,
                                      label=title,
                                      hatch=symbol)
                    ax.bar_label(handles, padding=3)
                    offset += len(histogram)
                    labels.extend(categories)
                ax.set_yticks(list(range(offset)), labels)
                ax.legend(bbox_to_anchor=(0, 1.02, 1, 0.2),
                          loc="lower left",
                          mode="expand",
                          borderaxespad=0,
                          ncol=1)
    else:
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


@utils.easy_log('Plot domain feature types as barh')
def plot_domain_feature_types_as_barh(args, data: list[data_loading.DataLoader], keys, filename_base):
    studies_by_domain = collections.defaultdict(list)
    for study in data:
        for d in study.domains:
            studies_by_domain[d].append(study)
    for domain, studies in studies_by_domain.items():
        plot_global_feature_types_as_barh(args, studies, keys, f'{filename_base}-{domain}.png')


@utils.easy_log('Plot domain node features as barh')
def plot_domain_node_features_as_barh(args, data: list[data_loading.DataLoader]):
    keys = [
        'node feature (internal)',
        'node feature (terminal)',
        'node feature (root/terminal)',
        'node feature',
    ]
    plot_domain_feature_types_as_barh(args, data, keys, 'features/domain-node-feature-types-as-barh')


@utils.easy_log('Plot domain other features as barh')
def plot_domain_other_features_as_barh(args, data: list[data_loading.DataLoader]):
    keys = [
        'other'
    ]
    plot_domain_feature_types_as_barh(args, data, keys, 'features/domain-other-feature-types-as-barh')


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
    data = [
        [
            _remove_brackets(item)
            for feature in study.features
            for feat in keys
            for item in feature.get_next_attribute_level(feat)
        ]
        for study in data
    ]
    if all(not x for x in data):
        print(f'WARNING: Not generating file {filename}! (no data)', )
        return
    df = upsetplot.from_memberships(data)
    with plot_utils.figure(filename,
                           nrows=2,
                           ncols=2,
                           tight=3) as (fig, axes):
        plot_utils.upset_plot(df, fig, axes, min_size=args.min_feature_upset)


@utils.easy_log('Plot domain feature types as upset')
def plot_domain_feature_types_as_upset(args, data: list[data_loading.DataLoader], keys, filename_base):
    studies_by_domain = collections.defaultdict(list)
    for study in data:
        for d in study.domains:
            studies_by_domain[d].append(study)
    for domain, studies in studies_by_domain.items():
        plot_global_feature_types_as_upset(args, studies, keys, f'{filename_base}-{domain}.png')


@utils.easy_log('Plot domain node features as upset')
def plot_domain_node_features_as_upset(args, data: list[data_loading.DataLoader]):
    keys = [
        'node feature (internal)',
        'node feature (terminal)',
        'node feature (root/terminal)',
        'node feature',
    ]
    plot_domain_feature_types_as_upset(args, data, keys, 'features/domain-node-feature-types-as-upset')


@utils.easy_log('Plot domain other features as upset')
def plot_domain_other_features_as_upset(args, data: list[data_loading.DataLoader]):
    keys = [
        'other'
    ]
    plot_domain_feature_types_as_upset(args, data, keys, 'features/domain-other-feature-types-as-upset')


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
    if not args.paper_only:
        plot_models_by_type(args, data)
        plot_models_by_domain(args, data)
        plot_models_by_year(args, data)
    plot_models_by_type_as_upset(args, data)
    if not args.paper_only:
        plot_graph_pooling_as_barh(args, data)
    if not args.paper_only:
        plot_node_transforms_as_barh(args, data)
        plot_gnn_message_passing_models(args, data)
        plot_the_remaining_stuff(args, data)
        plot_tree_stuff(args, data)
    plot_gnn_and_tree_models_jointly(args, data)
    plot_classic_models(args, data)
    plot_pooling_as_starburst(args, data)
    if not args.paper_only:
        plot_models_by_type_per_domain(args, data)
        plot_models_by_type_as_upset_per_domain(args, data)


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


@utils.easy_log('Plotting models by type per domain')
def plot_models_by_type_per_domain(args, data: list[data_loading.DataLoader]):
    models_by_type = collections.defaultdict(lambda: collections.defaultdict(int))
    for study in data:
        for model in study.models:
            model_type = '/'.join(
                sorted(
                    model.get_attributes('base-type')
                )
            )
            for domain in study.domains:
                models_by_type[domain][model_type] += 1
    for domain, models in models_by_type.items():
        with plot_utils.figure(f'models/models-by-type-per-domain-{domain}.png') as (fig, ax):
            plot_utils.barh_chart_from_dict(models, ax)


@utils.easy_log('Plotting models by type as upset plot')
def plot_models_by_type_as_upset(args, data: list[data_loading.DataLoader]):
    models = [list(m.get_attributes('base-type')) for study in data for m in study.models]
    for m in models:
        if 'classic' in m:
            m.remove('classic')
            m.append('traditional')
        if 'ensemble' in m:
            m.remove('ensemble')
        word2vec = False
        for x in ['cbow', 'skipgram']:
            if x in m:
                word2vec = True
                m.remove(x)
        if word2vec:
            m.append('cbow/skipgram')
    models = [[capitalize(x) for x in m] for m in models]
    df = upsetplot.from_memberships(models)
    if args.paper_only:
        with plot_utils.NiceFigure(f'figure_{FIGURE_OFFSET + 6}.png',
                                   nrows=2,
                                   ncols=2,
                                   tight=3,
                                   page_size=DOUBLE_COLUMN_SIZE,
                                   width_to_height_ratio=2) as (fig, axes):
            plot_utils.upset_plot(df, fig, axes)
    else:
        with plot_utils.figure('models/models-by-type-as-upset.png',
                               nrows=2,
                               ncols=2,
                               tight=3) as (fig, axes):
            plot_utils.upset_plot(df, fig, axes)


@utils.easy_log('Plotting models by type as upset plot per domain')
def plot_models_by_type_as_upset_per_domain(args, data: list[data_loading.DataLoader]):
    models_by_domain = collections.defaultdict(list)
    for study in data:
        for model in study.models:
            for domain in study.domains:
                models_by_domain[domain].append(model.get_attributes('base-type'))
    for domain, models in models_by_domain.items():
        df = upsetplot.from_memberships(models)
        with plot_utils.figure(f'models/models-by-type-as-upset-per-domain-{domain}.png',
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


@utils.easy_log('Plotting tree and GNN models jointly')
def plot_gnn_and_tree_models_jointly(args, data: list[data_loading.DataLoader]):
    gnn = collections.defaultdict(int)
    tree = collections.defaultdict(int)
    gnn_adjustments = {
        'custom edge-type aware message passing scheme': 'custom GNN layer',
        'custom message passing scheme': 'custom GNN layer',
        'custom edge-type aware message passing scheme w. attention': 'custom GNN layer'
    }
    tree_adjustments = {
        'transformer (first bottom up w. attention, then top down without attention)': 'tree transformer',
        'tree-lstm variant': 'tree-LSTM',
        'tree-lstm': 'tree-LSTM',
        'child-sum tree-lstm': 'tree-LSTM',
        'recursively applied bottom-up auto-encoder for node embeddings': 'recursive bottom-up auto-encoder',
        'cnn over sequence, but based on original tree structure': 'tree adjusted CNN'
    }
    for study in data:
        for attr in _deduplicate_keys(study.models, 'gnn-functionality: gnn'):
            gnn[gnn_adjustments.get(attr, attr)] += 1
        for attr in _deduplicate_keys(study.models, 'gnn-functionality: tree'):
            tree[tree_adjustments.get(attr, attr)] += 1
    gnn = {capitalize(k): v for k, v in gnn.items() if v >= args.min_gnn_count}
    tree = {capitalize(k): v for k, v in tree.items() if v >= args.min_tree_count}
    # with plot_utils.NiceFigure(f'figure_{FIGURE_OFFSET + 8}.png',
    #                            nrows=1,
    #                            ncols=2,
    #                            width_to_height_ratio=2,
    #                            page_size=DOUBLE_COLUMN_SIZE,
    #                            tight=True,
    #                            render_axes=True) as (fig, axes):
    with plot_utils.NiceFigure(f'figure_{FIGURE_OFFSET + 8}.png',
                               nrows=1,
                               ncols=2,
                               width_to_height_ratio=4,
                               page_size=DOUBLE_COLUMN_SIZE,
                               tight=True,
                               render_axes=True) as (fig, axes):
        #axes[0].set_title('GNN Models')
        width = plot_utils.barh_chart_from_dict(gnn, axes[0], width=0.5)
        #axes[1].set_title('Tree Models')
        plot_utils.barh_chart_from_dict(tree, axes[1], width=0.5)


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
            hist[capitalize(attr)] += 1
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
                attrs = list(model.get_attributes('misc: model'))
                has_adaboost = 'meta: adaboost' in attrs
                uses_kernel = bool(model.get_attributes('misc: kernel'))
                if has_adaboost:
                    attrs.remove('meta: adaboost')
                for key in attrs:
                    if key.startswith('misc:'):
                        key = key.replace('misc:', 'other:')
                    if key.startswith('ranking:'):
                        key = key.replace('ranking:', 'other:')
                    if key == 'other: graph filter with symmetric absorbing random walks':
                        key = 'other: graph filter'
                    if has_adaboost:
                        unique.add(f'{key} (with adaboost)')
                    elif key.endswith('svm'):
                        if uses_kernel:
                            unique.add(f'{key}: graph kernel')
                        else:
                            unique.add(f'{key}: regular kernel')
                    else:
                        unique.add(key)
                    if model.cluster is not None:
                        prefix, _ = key.rsplit(': ', 1)
                        if key in classic:
                            translation_map[key] = f'{prefix}: {model.cluster} clustering (generic algorithm)'
                        else:
                            translation_map[key] = f'{prefix}: {model.cluster} clustering (graph-specific algorithm)'
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
            current = current.setdefault(capitalize(part), {})
        current[capitalize(parts[-1])] = value
    if args.paper_only:
        with adjusted_font_size(7):
            with plot_utils.NiceFigure(f'figure_{FIGURE_OFFSET + 7}.png',
                                       page_size=DOUBLE_COLUMN_SIZE,
                                       width_to_height_ratio=1/0.53) as (fig, ax):
                align = {
                    capitalize('supervised'): {
                        capitalize('random forest'): {
                            'horizontal': 'right',
                            'vertical': 'top',
                            'raise-by': 0
                        }
                    }
                }
                sb = plot_utils.Sunburst(radius=1, x_to_y_axis_ratio=1 / 0.53, y_stretch=0.85)
                sb.plot(models_as_tree, ax, alignment_override=align)
    else:
        with adjusted_font_scale(1):
            with plot_utils.figure('models/classic-models.png', a4=True, height_size_hint=0.53) as (fig, ax):
                align = {
                    capitalize('supervised'): {
                        capitalize('random forest'): {
                            'horizontal': 'right',
                            'vertical': 'top',
                            'raise-by': 0
                        }
                    }
                }
                sb = plot_utils.Sunburst(radius=1, x_to_y_axis_ratio=1 / 0.53, y_stretch=0.85)
                sb.plot(models_as_tree, ax, alignment_override=align)


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
        last = capitalize(last)
        for p in path:
            p = capitalize(p)
            p = p.replace(' ', '\n')
            current = current.setdefault(p, {})
        if last not in current:
            current[last] = 0
        current[last] += value
    if args.paper_only:
        with adjusted_font_size(7):
            with plot_utils.NiceFigure(f'figure_{FIGURE_OFFSET + 9}.png',
                                       page_size=DOUBLE_COLUMN_SIZE,
                                       width_to_height_ratio=1/0.6) as (fig, ax):
                sb = plot_utils.Sunburst(radius=1,
                                         x_to_y_axis_ratio=1 / 0.6,
                                         y_stretch=1.2)
                alignment = {
                    capitalize('misc'): {
                        capitalize('combined sum and max pooling'): {'horizontal': 'right', 'vertical': 'center'},
                        # The stack
                        capitalize('mean bi-affine attention pooling'): {'horizontal': 'right',
                                                             'vertical': 'bottom',
                                                             'raise-by': 0.1},
                        capitalize('set2set'): {'horizontal': 'right',
                                    'vertical': 'bottom',
                                    'raise-by': 0.25},
                        capitalize('conv w. max pooling over node feature matrix'): {'horizontal': 'left',
                                                                         'vertical': 'bottom',
                                                                         'raise-by': 0.2},
                        capitalize('bidirectional lstm'): {'horizontal': 'left',
                                               'vertical': 'bottom',
                                               'raise-by': 0.05},
                    },
                    capitalize('summing'): {
                        capitalize('weighted sum'): {'horizontal': 'right', 'vertical': 'bottom'},
                    },
                    capitalize('node\nsampling').replace(' ', '\n'): {
                        capitalize('SAGPool'): {'horizontal': 'left', 'vertical': 'top'},
                        capitalize('unspecified'): {'horizontal': 'left', 'vertical': 'top'},
                    },
                    capitalize('graph\ncoarsening').replace(' ', '\n'): {
                        capitalize('DMonPool'): {'horizontal': 'left', 'vertical': 'top'},
                        capitalize('edge pooling'): {'horizontal': 'left', 'vertical': 'bottom'},
                    },
                    capitalize('unspecified'): {'horizontal': 'left', 'vertical': 'center', 'raise-by': 0.1}
                }
                sb.plot(pooling, ax, alignment_override=alignment)
    else:
        with adjusted_font_scale(1):
            with plot_utils.figure('models/pooling-by-type.png', a4=True, height_size_hint=0.6) as (fig, ax):
                sb = plot_utils.Sunburst(radius=1,
                                         x_to_y_axis_ratio=1 / 0.6,
                                         y_stretch=1.2)
                alignment = {
                    capitalize('misc'): {
                        capitalize('combined sum and max pooling'): {'horizontal': 'right', 'vertical': 'center'},
                        # The stack
                        capitalize('mean bi-affine attention pooling'): {'horizontal': 'right',
                                                                         'vertical': 'bottom',
                                                                         'raise-by': 0.1},
                        capitalize('set2set'): {'horizontal': 'right',
                                                'vertical': 'bottom',
                                                'raise-by': 0.25},
                        capitalize('conv w. max pooling over node feature matrix'): {'horizontal': 'left',
                                                                                     'vertical': 'bottom',
                                                                                     'raise-by': 0.2},
                        capitalize('bidirectional lstm'): {'horizontal': 'left',
                                                           'vertical': 'bottom',
                                                           'raise-by': 0.05},
                    },
                    capitalize('summing'): {
                        capitalize('weighted sum'): {'horizontal': 'right', 'vertical': 'bottom'},
                    },
                    capitalize('node\nsampling').replace(' ', '\n'): {
                        capitalize('SAGPool'): {'horizontal': 'left', 'vertical': 'top'},
                        capitalize('unspecified'): {'horizontal': 'left', 'vertical': 'top'},
                    },
                    capitalize('graph\ncoarsening').replace(' ', '\n'): {
                        capitalize('DMonPool'): {'horizontal': 'left', 'vertical': 'top'},
                        capitalize('edge pooling'): {'horizontal': 'left', 'vertical': 'bottom'},
                    },
                    capitalize('unspecified'): {'horizontal': 'left', 'vertical': 'center', 'raise-by': 0.1}
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
    if not args.paper_only:
        plot_graph_vertices(args, data)
        plot_graph_edges(args, data)
    plot_graph_vertices_and_edges_joint(args, data)
    plot_graph_edges_as_upset(args, data)
    if not args.paper_only:
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


@utils.easy_log('Plotting Graph Vertices and Edges Jointly')
def plot_graph_vertices_and_edges_joint(args, data: list[data_loading.DataLoader]):
    vertices = collections.defaultdict(int)
    edges = collections.defaultdict(int)
    for study in data:
        for graph in study.graphs:
            for vertex in graph.parse().vertices:
                vertices[vertex.value] += 1
            for edge in graph.parse().edges:
                edges[edge.value] += 1
    vertices = {capitalize(k): v for k, v in vertices.items() if v >= args.min_vertex_count}
    edges = {capitalize(k): v for k, v in edges.items() if v >= args.min_edge_count}
    with adjusted_font_scale(1):
        with plot_utils.NiceFigure(f'figure_{FIGURE_OFFSET + 3}.png',
                                   nrows=1,
                                   ncols=2,
                                   tight=True,
                                   width_to_height_ratio=3,
                                   page_size=DOUBLE_COLUMN_SIZE,
                                   render_axes=True) as (fig, axes):
            #axes[0].set_title('(a) Nodes', loc='bottom')
            plot_utils.barh_chart_from_dict(vertices, axes[0])
            plot_utils.barh_chart_from_dict(edges, axes[1])
            #axes[1].set_title('(b) Edges', loc='bottom')
        # with plot_utils.NiceFigure(f'figure_{FIGURE_OFFSET + 3}b.png',
        #                            nrows=1,
        #                            ncols=1,
        #                            tight=True,
        #                            width_to_height_ratio=1.75,
        #                            page_size=SINGLE_COLUMN_SIZE) as (fig, ax):
        #     plot_utils.barh_chart_from_dict(edges, ax)


@utils.easy_log('Plotting Graph Edges as Upset Plot')
def plot_graph_edges_as_upset(args, data: list[data_loading.DataLoader]):
    edges = [sorted([e.value for e in g.parse().edges]) for study in data for g in study.graphs]
    hist = collections.defaultdict(int)
    for col in edges:
        hist[tuple(col)] += 1
    edges = [[capitalize(x) for x in e] for e in edges if hist[tuple(e)] >= args.min_edge_upset]
    df = upsetplot.from_memberships(edges)
    if args.paper_only:
        with adjusted_font_size(8):
            with plot_utils.NiceFigure(f'figure_{FIGURE_OFFSET + 4}.png',
                                       nrows=2,
                                       ncols=2,
                                       tight=3,
                                       width_to_height_ratio=1.75,
                                       page_size=DOUBLE_COLUMN_SIZE) as (fig, axes):
                plot_utils.upset_plot(df, fig, axes, min_size=args.min_edge_upset, font_size=8)
    else:
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
    parser.add_argument('--paper-only', action='store_true', default=False)
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
    parsed_args = parser.parse_args()
    if parsed_args.paper_only:
        PAPER_ONLY = True
        _set_seaborn_theme(FONT_SCALE)
    main(parsed_args)
