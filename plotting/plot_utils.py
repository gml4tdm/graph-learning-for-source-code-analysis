import collections
import contextlib
import math
import os
import os.path
import textwrap

import matplotlib.patches
import matplotlib.lines
import matplotlib.pyplot as pyplot
import matplotlib.gridspec as gridspec
import numpy
import pandas
import upsetplot


@contextlib.contextmanager
def figure(filename: str,
           nrows=1,
           ncols=1, *,
           tight: bool | int | float = True,
           a4: bool = False,
           height_factor: float = 1,
           grid_spec: bool = False,
           height_size_hint=None,
           share_x=False,
           share_y=False):
    if not grid_spec:
        fig, axes = pyplot.subplots(nrows, ncols, sharex=share_x, sharey=share_y)
    else:
        fig = pyplot.figure()
        axes = gridspec.GridSpec(ncols=ncols, nrows=nrows, figure=fig)
    if a4:
        if height_size_hint:
            height_factor = 8.3 / 11.7 * height_size_hint
        fig.set_size_inches(8.3, 11.7 * height_factor)
    else:
        fig.set_size_inches(19.20, 10.80)
    yield fig, axes
    if tight:
        if not isinstance(tight, bool):
            fig.tight_layout(pad=tight)
        else:
            fig.tight_layout()
    os.makedirs('figures', exist_ok=True)
    path, _ = os.path.split(filename)
    if path:
        os.makedirs(os.path.join('figures', path), exist_ok=True)
    full_path = os.path.join('figures', filename)
    fig.savefig(full_path, dpi=100)
    if filename.endswith('.png'):
        fig.savefig(full_path.replace('.png', '.pdf'))
        #subprocess.run(f'inkscape -o {} {}')
    pyplot.close(fig)


def upset_plot(data, fig, axes, *, min_size=0, use_native_order=False):
    for axes_ in axes:
        for ax in axes_:
            ax.set_axis_off()
    upsetplot.plot(
        data,
        fig=fig,
        #sum_over='count',
        subset_size='count',
        show_counts=True,
        min_subset_size=min_size,
        #sort_by='cardinality' if not use_native_order else 'input',
        sort_categories_by='cardinality' if not use_native_order else 'input'
    )


def from_memberships(data, categories):
    #counts = collections.defaultdict(int)
    #for row in data:
    #    key = tuple(sorted(row, key=categories.index))
    #    counts[key] += 1
    frame_data = []
    for row in data:
        ident = [False] * len(categories)
        for item in row:
            ident[categories.index(item)] = True
        frame_data.append(ident)
    df = pandas.Series(
        [1] * len(data),
        #columns=categories,
        index=pandas.MultiIndex.from_tuples(
            frame_data,
            names=categories
        )
    )
    return df


def stack_chart_from_dict(data: dict[str, dict[int, int]], ax, *, draw_labels=True):
    # Create the matrix of values
    x_values = {x for inner in data.values() for x in inner }
    x_min = min(x_values)
    x_max = max(x_values)
    x_span = x_max - x_min + 1
    matrix = [[0] * x_span for _ in range(len(data))]
    # Sort so that most common category is at bottom
    categories = sorted(data,
                        key=lambda x: sum(data[x].values()),
                        reverse=True)
    for x in range(x_min, x_max + 1):
        for i, category in enumerate(categories):
            matrix[i][x - x_min] = data[category][x]
    # Plot
    x = list(range(x_min, x_max + 1))
    handles = ax.stackplot(x, matrix, labels=categories)
    if draw_labels:
        ax.legend(loc='upper left')
    return handles


def bar_chart_from_nested_dict(data: dict[str, dict[str, int]], ax):
    x = range(len(data))
    categories = set()
    for inner in data.values():
        categories |= inner.keys()
    categories = sorted(categories)
    classes = sorted(data)
    bars = []
    width = 1 / (len(categories) + 1)
    for a, category in enumerate(categories):
        offset = a * width
        rectangles = ax.bar(
            [x_ + offset for x_ in x],
            [data[cls].get(category, 0) for cls in classes],
            width=width,
            label=category,
        )
        ax.bar_label(rectangles, padding=3)
        bars.append(rectangles)
    ax.set_ylabel('Something')
    ax.set_xlabel('Something Else')
    ax.set_xticks([x_ + width / 2 for x_ in x], classes)
    ax.legend(loc='upper left', ncols=len(categories))


def barh_chart_from_dict(data: dict[str, int],
                         ax, *,
                         title: str | None = None,
                         color='b'):
    categories = sorted(data)
    included_categories = [cat for cat in categories if data[cat]]
    included = [data[cat] for cat in categories if data[cat]]
    y = range(len(included))
    rectangles = ax.barh(y, included, color=color)
    ax.bar_label(rectangles, padding=3)
    ax.set_ylabel(title)
    #ax.set_xlabel('Something Else')
    ax.set_yticks(y, included_categories)
    ax.set_xticks(
        [tick for tick in ax.get_xticks() if abs(int(tick) - tick) < 0.1]
    )


def categorical_bubble_plot(data: dict[tuple[str, str], int], ax, *, r_max=1):
    x_ticks = sorted({key[0] for key in data})
    y_ticks = sorted({key[1] for key in data})
    maximum = max(data.values())
    x_values = []
    y_values = []
    sizes = []
    for (x, y), value in data.items():
        x_values.append(x_ticks.index(x))
        y_values.append(y_ticks.index(y))
        sizes.append(value / maximum * r_max * 100)
    ax.scatter(x_values, y_values, s=sizes, c='r')
    ax.set_xticks(range(len(x_ticks)), x_ticks, rotation='vertical')
    ax.set_yticks(range(len(y_ticks)), y_ticks)


def _join_helper(items):
    if len(items) == 1:
        return items[0]
    *bulk, last = items
    return ', '.join(bulk) + ' and ' + last


class Sunburst:

    _base_maps = [
        'Reds', 'Blues', 'Greens', 'Purples', 'Oranges',  'Greys',
    ]

    def __init__(self, *,
                 radius,
                 x_to_y_axis_ratio,
                 y_stretch: float = 1.1):
        self.radius = radius
        self.ax_ratio = x_to_y_axis_ratio
        self.y_scale = y_stretch

    def plot(self, data, ax, *, alignment_override=None):
        ax.set_aspect('equal')
        ax.set_axis_off()
        d = self._depth(data) + 1
        y_bound = self.y_scale * d * self.radius
        ax.set_xlim(self.ax_ratio * -y_bound, self.ax_ratio * y_bound)
        ax.set_ylim(-y_bound, y_bound)
        data = self._sort_by_cat_size(data)
        if alignment_override is None:
            alignment_override = {}
        patches = self._plot_recursive(data,
                                       self._count_total(data),
                                       alignment_override=alignment_override)
        for patch, text, label, line in patches:
            ax.add_patch(patch)
            ax.add_artist(text)
            ax.add_artist(label)
            if line is not None:
                ax.add_artist(line)

    def _plot_recursive(self,
                        data,
                        total,
                        angle_start=0,
                        angle_span=360,
                        depth=0,
                        colors=None, *,
                        alignment_override):
        color_index = 0
        for key, value in data.items():
            if isinstance(value, dict):
                size = self._count_total(value)
            else:
                size = value
            span = size / total * angle_span
            if colors is None:
                colors_for_wedge = self._compute_colors(
                    color_index,
                    self._count_patches(value) if isinstance(value, dict) else 1
                )
                color_index += 1
            else:
                colors_for_wedge = colors
            item_font, item_color = colors_for_wedge.pop()
            wedge = matplotlib.patches.Wedge(
                center=(0, 0),
                r=(depth + 1) * self.radius,
                theta1=angle_start,
                theta2=angle_start + span,
                width=self.radius,
                color=item_color,
                fill=True
            )
            label, line = self._make_name_annotation(
                is_outer_ring=not isinstance(value, dict), depth=depth,
                angle_start=angle_start, span=span, text=key, color=item_font,
                alignment_override=alignment_override
            )
            text = self._make_count_annotation(depth, angle_start, span, str(size), item_font)
            yield wedge, text, label, line
            if isinstance(value, dict):
                yield from self._plot_recursive(value, size, angle_start, span, depth + 1,
                                                colors=colors_for_wedge,
                                                alignment_override=alignment_override.get(key, {}))
            angle_start += span

    def _make_name_annotation(self, *,
                              is_outer_ring: bool = False,
                              depth: int,
                              angle_start: int,
                              span: int,
                              text: str,
                              color,
                              alignment_override):
        if not is_outer_ring:
            r = (depth + 0.6) * self.radius
            angle = math.radians(angle_start + span / 2)
            text = matplotlib.pyplot.Text(
                x=r * math.cos(angle),
                y=r * math.sin(angle),
                text=text,
                color=color,
                verticalalignment='center',
                horizontalalignment='center'
            )
            return text, None
        else:
            angle = math.radians(angle_start + span / 2)
            if 2 * math.pi / 4 <= angle < 2 * math.pi * 3 / 4:
                horizontal_alignment = 'right'
            else:
                horizontal_alignment = 'left'
            override = alignment_override.get(text, None)
            if override is None:
                vertical_alignment = 'center'
            else:
                horizontal_alignment = override['horizontal']
                vertical_alignment = override['vertical']
            if override is None or 'raise-by' not in override:
                r = (depth + 1.1) * self.radius
                line = None
            else:
                r0 = (depth + 1.1) * self.radius
                r = r1 = (depth + 1.1 + override['raise-by']) * self.radius
                line = matplotlib.lines.Line2D(
                    [r0 * math.cos(angle), r1 * math.cos(angle)],
                    [r0 * math.sin(angle), r1 * math.sin(angle)],
                    color='k'
                )
            text = matplotlib.pyplot.Text(
                x=r * math.cos(angle),
                y=r * math.sin(angle),
                text=text,  # '\n'.join(textwrap.wrap(key, 20)),
                color='k',
                verticalalignment=vertical_alignment,
                horizontalalignment=horizontal_alignment
            )
            return text, line

    def _make_count_annotation(self,
                               depth: int,
                               angle_start: int,
                               span: int,
                               count: str,
                               color):
        r = (depth + 0.9) * self.radius
        angle = math.radians(angle_start + span / 2)
        return matplotlib.pyplot.Text(
            x=r * math.cos(angle),
            y=r * math.sin(angle),
            text=count,
            color=color,
            verticalalignment='center',
            horizontalalignment='center'
        )

    def _depth(self, data):
        return max(
            self._depth(item) + 1 if isinstance(item, dict) else 0
            for item in data.values()
        )

    def _count_total(self, data):
        return sum(
            self._count_total(item) if isinstance(item, dict) else item
            for item in data.values()
        )

    def _count_patches(self, data):
        return 1 + sum(
            self._count_patches(item) if isinstance(item, dict) else 1
            for item in data.values()
        )

    def _compute_colors(self, index, count):
        cmap = matplotlib.cm.get_cmap(self._base_maps[index])
        space = numpy.linspace(0.25, 0.9, count)
        colors = [tuple(x) for x in cmap(space)]
        fonts = ['k' if x <= 0.7 else 'w' for x in space]
        return list(
            reversed(
                list(
                    zip(fonts, colors)
                )
            )
        )

    def _sort_by_cat_size(self, data):
        if isinstance(data, dict):
            return {
                key: self._sort_by_cat_size(value)
                for key, value in sorted(
                    data.items(),
                    key=lambda pair: self._count_total(pair[1]) if isinstance(pair[1], dict) else pair[1]
                )
            }
        else:
            return data
