"""
Module to provide a uniform interface to
the collected data across different files.
"""

##############################################################################
##############################################################################
# Imports
##############################################################################

from __future__ import annotations

import abc
import collections
import csv
import functools
import json
import os.path
import typing

import yaml

import libedit

SNOWBALLING_FILE = '../resolver/snowballing.json5'
SCOPUS_FILE = '../resolver/initial-merged.csv'
CROSSREF_DIRECTORY = '../resolver/cache'
DATA_DIRECTORIES = [
    '../data-extraction',
    '../data-extraction-2',
    '../data-extraction-sb',
]

_scopus_data: dict[str, dict[str, str]] | None = None
_snowballing_data: dict[str, dict[str, str]] | None = None


##############################################################################
##############################################################################
# Data Loading
##############################################################################


def _init_snowballing_data():
    global _snowballing_data
    with open(SNOWBALLING_FILE) as file:
        data = json.load(file)
    _snowballing_data = {x['uid']: x for x in data}


def _init_scopus_data():
    global _scopus_data
    with open(SCOPUS_FILE, encoding='utf8') as file:
        reader = csv.reader(file)
        header = next(reader)
        _scopus_data = {
            row[header.index('Paper ID')]: {k: v for k, v in zip(header, row, strict=True)}
            for row in reader
        }


##############################################################################
##############################################################################
# Paper access
##############################################################################


def get_all_paper_ids() -> list[str]:
    if _snowballing_data is None:
        _init_snowballing_data()
    if _scopus_data is None:
        _init_scopus_data()
    assert _scopus_data is not None
    assert _snowballing_data is not None
    return list(_scopus_data) + list(_snowballing_data)


##############################################################################
##############################################################################
# Paper-level data loading
##############################################################################


class DataLoader(abc.ABC):

    _file_mapping = {
        'domains': '../data-synthesis/projects/domain_project_2.json',
        'artefacts': '../data-synthesis/projects/artefacts_project.json',
        'models': '../data-synthesis/projects/model_project.json',
        'graphs': '../data-synthesis/projects/graph_project.json',
        'features': '../data-synthesis/projects/feature_project.json',
        'models-cluster-type': '../data-synthesis/projects/model_cluster_granularity.json',
        'models-graph-granularity': '../data-synthesis/projects/model_class_reg_granularity.json',
        'models-rank': '../data-synthesis/projects/model_rank_project.json',
    }

    _cached_files = {}

    _cached_keys = {}

    def __init__(self, uid: str, raw_extraction_data: str):
        self.uid = uid
        self._raw = raw_extraction_data

    @property
    @abc.abstractmethod
    def year(self) -> int:
        pass

    @property
    @abc.abstractmethod
    def doi(self) -> str:
        pass

    def _resolve_rules(self, key: str) -> dict[str, typing.Any]:
        if key not in self._cached_files:
            self._cached_files[key] = libedit.load_raw(self._file_mapping[key])
        return self._cached_files[key]

    def _resolve_key(self, key: str, *, raise_error=True) -> str:
        if (key, self._raw) not in self._cached_keys:
            # First attempt document content match
            parsed = json.loads(self._raw)
            for r in self._cached_files[key]['raw']:
                if json.loads(r) == parsed:
                    self._cached_keys[(key, self._raw)] = r
                    break
            else:
                # Painful heuristic search as fallback
                search_keys = [
                    f'"paper-id": "{self.uid}",',
                    f'"paper-id": {self.uid},',
                ]
                hits = []
                rules = self._resolve_rules(key)
                for r in rules['raw']:
                    for search_key in search_keys:
                        if search_key in r:
                            hits.append(r)
                            break
                if len(hits) == 1:
                    self._cached_keys[(key, self._raw)] = hits[0]
                elif len(hits) > 1:
                    raise LookupError(f'Multiple keys resolved for paper {self.uid!r}')
                elif not raise_error:
                    self._cached_keys[(key, self._raw)] = ''
                else:
                    raise LookupError(f'Failed to resolve key for paper {self.uid!r}')
        return self._cached_keys[(key, self._raw)]

    def _resolve_property(self, key: str) -> list[str]:
        rules = self._resolve_rules(key)
        resolved_key = self._resolve_key(key)
        return libedit.resolve_one(resolved_key, rules['refinements'])

    def _resolve_entities(self, key: str) -> dict[str, list[str]]:
        rules = self._resolve_rules(key)
        resolved_key = self._resolve_key(key)
        raw_entries = libedit.resolve_while([resolved_key],
                                            rules['refinements'],
                                            lambda x: '@' in x or x[0] == '{')
        raw_by_entity = collections.defaultdict(list)
        for entry in raw_entries:
            entity, _ = entry.split('$', maxsplit=1)
            raw_by_entity[entity].append(entry)
        tags_by_entity = {
            key: [tag for tag in libedit.resolve_items(value, rules['refinements']) if tag is not None]
            for key, value in raw_by_entity.items()
        }
        return tags_by_entity

    def _resolve_graph_entities(self) -> dict[str, list[str]]:
        # "Arbitrary Graphs (?)",
        rules = self._resolve_rules('graphs')
        graphs = json.loads(self._raw)['graphs']
        if isinstance(graphs, str):
            return {'any': ['any graph']}       # Weird special case
        with open('../resolver/graph_key_overwrite.json') as file:
            overwrites = json.load(file)
        if self.uid in overwrites:
            mapping = overwrites[self.uid]
        else:
            mapping = {}
            for r in rules['raw']:
                if r == "Arbitrary Graphs (?)":
                    continue
                for key, value in graphs.items():
                    if json.loads(r) == value:
                        mapping[key] = r
        if len(mapping) != len(graphs):
            raise Exception('Mapping length mismatch')
        return {
            key: libedit.resolve_one(v, rules['refinements'])
            for key, v in mapping.items()
        }

    def _resolve_auxiliary_property(self, key: str) -> dict[str, str] | None:
        rules = self._resolve_rules(key)
        resolved_key = self._resolve_key(key, raise_error=False)
        if not resolved_key:
            return None
        raw = libedit.resolve_while([resolved_key],
                                    rules['refinements'],
                                    lambda x: x[0] == '{')
        if raw == [resolved_key]:
            return None
        assert len(raw) == 1
        items = raw[0].split('@')
        result = {}
        for entry in items:
            key = entry.split('$', maxsplit=1)[0]
            value = libedit.resolve_one(entry, rules['refinements'])
            assert len(value) == 1
            result[key] = value[0]
        return result

    @functools.cached_property
    def domains(self) -> list[str]:
        return self._resolve_property('domains')

    @functools.cached_property
    def artefacts(self) -> list[str]:
        rules = self._resolve_rules('artefacts')
        parsed = json.loads(self._raw)
        if isinstance((graphs := parsed['graphs']), dict):
            raw = [
                (
                    f'{artefact["name"]}'
                    if (det := artefact['details']) is None or det.lower() == 'n/a'
                    else f'{artefact["name"]} ({artefact["details"]})'
                ).lower()
                for graph in graphs.values()
                for artefact in graph['artefacts']
            ]
            result = []
            for item in raw:
                result.extend(libedit.resolve_one(item, rules['refinements']))
            return result
        else:
            return []

    @functools.cached_property
    def models(self) -> list[ModelDataLoader]:
        cluster_info = self._resolve_auxiliary_property('models-cluster-type')
        graph_info = self._resolve_auxiliary_property('models-graph-granularity')
        rank_info = self._resolve_auxiliary_property('models-rank')
        return [
            ModelDataLoader(
                k,
                *v,
                cluster=cluster_info.get(k, None) if cluster_info is not None else None,
                graph=graph_info.get(k, None) if graph_info is not None else None,
                rank=rank_info.get(k, None) if rank_info is not None else None
            )
            for k, v in self._resolve_entities('models').items()
        ]

    @functools.cached_property
    def features(self) -> list[FeatureDataLoader]:
        return [FeatureDataLoader(k, *v)
                for k, v in self._resolve_entities('features').items()]

    @functools.cached_property
    def graphs(self) -> list[GraphDataLoader]:
        return [GraphDataLoader(k, *v)
                for k, v in self._resolve_graph_entities().items()]


class ScopusDataLoader(DataLoader):

    def __init__(self, uid: str, raw_extraction_data: str, scopus_data: dict[str, typing.Any]):
        super().__init__(uid, raw_extraction_data)
        self._ref_data = scopus_data

    @property
    def year(self) -> int:
        return int(self._ref_data['Year'])

    @property
    def doi(self) -> str:
        return self._ref_data['DOI']

    @property
    def cited_by_count(self) -> int:
        return int(self._ref_data['Cited by'])


class CrossrefDataLoader(DataLoader):

    def __init__(self, uid: str, raw_extraction_data: str, crossref_data: dict[str, typing.Any]):
        super().__init__(uid, raw_extraction_data)
        self._ref_data = crossref_data

    @functools.cached_property
    def year(self) -> int:
        keys = [
            'published-print',
            'issued'
        ]
        for key in keys:
            try:
                return self._ref_data['message'][key]['date-parts'][0][0]
            except KeyError:
                pass
        else:
            raise LookupError(f'Failed to find year in crossref data for paper {self.uid!r}')

    @property
    def doi(self):
        return self._ref_data['message']['DOI']


class ManualDataLoader(DataLoader):

    def __init__(self, uid: str, raw_extraction_data: str, ref_data: dict[str, typing.Any]):
        super().__init__(uid, raw_extraction_data)
        self._ref_data = ref_data

    @property
    def year(self) -> int:
        return int(self._ref_data['year'])

    @property
    def doi(self):
        return self._ref_data['doi']


def load_data(paper_id: str) -> DataLoader:
    if paper_id.startswith('sb-'):
        return _load_data_snowballing(paper_id)
    else:
        return _load_data_initial(paper_id)


def _load_data_snowballing(paper_id: str) -> DataLoader:
    if _snowballing_data is None:
        _init_snowballing_data()
    assert _snowballing_data is not None
    try:
        entry = _snowballing_data[paper_id]
    except KeyError:
        raise LookupError(f'No paper with id {paper_id!r}')
    if entry['doi'] is None:
        return ManualDataLoader(paper_id, _load_raw_data(paper_id), entry['bibtex'])    # type: ignore
    with open(os.path.join(CROSSREF_DIRECTORY, entry['doi'].replace('/', '__'))) as file:
        return CrossrefDataLoader(paper_id, _load_raw_data(paper_id), json.load(file))


def _load_data_initial(paper_id: str) -> DataLoader:
    if _scopus_data is None:
        _init_scopus_data()
    assert _scopus_data is not None
    try:
        entry = _scopus_data[paper_id]
    except KeyError:
        raise LookupError(f'No paper with id {paper_id!r}')
    return ScopusDataLoader(paper_id, _load_raw_data(paper_id), entry)


def _load_raw_data(paper_id: str) -> str:
    filename = f'{paper_id}.yaml'
    for directory in DATA_DIRECTORIES:
        full_path = os.path.join(directory, filename)
        if os.path.exists(full_path):
            with open(full_path) as file:
                data = yaml.safe_load(file)
            return json.dumps(data, indent=2)
    raise LookupError(f'Failed to find file for paper with id {paper_id!r}')


##############################################################################
##############################################################################
# Auxiliary class
##############################################################################


class _AttributeMixin:

    def __init__(self, tags):
        self.__tags = tags

    @functools.cache
    def get_attributes(self, prefix=None):
        parts = [] if prefix is None else [part.strip() for part in prefix.split(':')]
        current = list(self.__tags)
        while parts:
            start = parts.pop(0)
            current = [
                x.removeprefix(start).removeprefix(':').strip()
                for x in current
                if x.startswith(start + ':')
            ]
        return current

    __get_attributes = get_attributes

    @functools.cache
    def get_next_attribute_level(self, prefix=None):
        attributes = self.__get_attributes(prefix)
        return [
            attr.split(':')[0].strip()
            for attr in attributes
        ]

    @functools.cache
    def get_attributes_complement(self, *prefixes: str, prefix=None):
        candidates = self.__get_attributes(prefix)
        return [
            x
            for x in candidates
            if not any(x.startswith(p.removeprefix(prefix + ':').strip()) for p in prefixes)
        ]


##############################################################################
##############################################################################
# Graph-level data loader
##############################################################################


class GraphDataLoader:

    def __init__(self, uid: str, *tags: str):
        self.uid = uid
        assert len(tags) == 1
        self.tags = tags
        assert not any(tag.startswith('{') for tag in tags)

    @functools.cache
    def parse(self) -> GraphData:
        tag = self.tags[0]
        if tag == 'any graph':
            return GraphData('any', [], [])
        assert tag.count('|') == 2, tag
        name, vertices, edge = tag.split('|')
        vertices = [GraphAttribute.from_string(vertex)
                    for vertex in vertices.split('/')]
        edges = [GraphAttribute.from_string(edge)
                 for edge in edge.split('/')]
        return GraphData(name, vertices, edges)


class GraphData:

    def __init__(self,
                 name: str,
                 vertices: list[GraphAttribute],
                 edges: list[GraphAttribute]):
        self.name = name
        self.vertices = vertices
        self.edges = edges


class GraphAttribute:

    def __init__(self, main_tag, details, tags):
        self.value = main_tag
        self.details = details
        self.modifiers = tuple(tags)

    @classmethod
    def from_string(cls, s: str):
        assert s.count('[') <= 1, s
        assert s.count('(') <= 1, s
        detail_index = index if (index := s.find('(')) >= 0 else None
        modifier_index = index if (index := s.find('[')) >= 0 else None
        if detail_index is not None:
            assert s.count(')') == 1, s
        if modifier_index is not None:
            assert s.count(']') == 1, s
        main_stop = min([len(s) + 1, detail_index, modifier_index],
                        key=lambda x: x if x is not None else float('inf'))
        main_tag = s[:main_stop].strip()
        details = s[detail_index+1:s.index(')')].strip().split(',') if detail_index is not None else []
        details = [x.strip() for x in details]
        modifiers = s[modifier_index+1:s.index(']')].strip().split(', ') if modifier_index is not None else []
        modifiers = [x.strip() for x in modifiers]
        return cls(main_tag, details, modifiers)


##############################################################################
##############################################################################
# Feature-level data loader
##############################################################################


class FeatureDataLoader(_AttributeMixin):

    def __init__(self, uid: str, *tags: str):
        super().__init__(tags)
        self.uid = uid
        self.tags = tags
        assert not any(tag.startswith('{') for tag in tags)


##############################################################################
##############################################################################
# Model-level data loader
##############################################################################


class ModelDataLoader(_AttributeMixin):

    def __init__(self, uid: str, *tags: str, graph, rank, cluster):
        super().__init__(tags)
        self.uid = uid
        self.tags = tags
        assert not any(tag.startswith('{') for tag in tags)
        self.graph = self._check_info_attr(graph)
        self.rank = self._check_info_attr(rank)
        self.cluster = self._check_info_attr(cluster)

    def _check_info_attr(self, attr):
        if attr is None:
            return None
        #if len(attr) != 1:
        #    raise ValueError(f'Invalid attribute for mode {self.uid}: {attr}')
        #return attr[0]
        return attr
