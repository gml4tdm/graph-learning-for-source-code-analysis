# A Systematic Mapping Study on Graph Machine Learning for Static Source Code Analysis

[![DOI](https://zenodo.org/badge/841905953.svg)](https://doi.org/10.5281/zenodo.13961041)

**TL;DR: all data can be found in `./data-extraction/data.json`,
and the description of its schema can be found [here](#datajson).**

## Content

- [Repository Files](#directory-structure-)
  - [Directory Structure](#repository-directory-structure)
  - [File Descriptions](#overview-of-files)
- [Runnable Scripts & Tools](#scripts--tools)
  - [Clustering](#clustering-)
  - [Annotator Tool](#annotator-tool)
  - [plotting](#plotting)
- [Data Description](#data-format)
  - [Raw Data](#raw-data)
  - [Refinement Data](#refinement)
  - [data.json](#datajson)

## Directory Structure
We will give a brief overview of the files in this repository.

### Repository Directory Structure

We start with a brief overview of the directory structure
of the repository:

```
./
    data-extraction/
        annotator-app/
        raw/
            initial/
                form-1/
                form-2/
                form-3/
            backward-snowballing/
                form-3/
            refinement-steps/
            auxiliary/
                scopus_data.csv
                misc-paper-data.json
                crossref_data/
        data.json
    study-selection/
        clustering.py
        final-papers.bib
        initial/
            round0/
                clusters/
                round0.csv
            round1.csv
            round2.csv
            round3.csv
        backward-snowballing/
            round0/
                clusters/
                round0.csv
            round1.csv
            round2.csv
            round3.csv
    plotting/
        libedit.py
        data_loading.py
        plotting.py
        plot.sh
        requirements.txt
```

### Overview of Files

A description of a selection of all files:

- `./data-extraction/`
    - `./data-extraction/annotator-app/`
        <br/> Contains a tool which can be used to browse
        the full set of tags assigned to the different
        papers. See the [Annotator Tool Section](#annotator-tool)
        for more details.
    - `./data-extraction/raw/`
        <br/> Contains the raw data as it was extracted from the papers.
        We went through 3 iterations of the data extraction form.
        The data files for each paper are placed in directories
        according to the form used.
    - `./data-extraction/refinement-steps/`
        <br/> Contains the steps used to refine the raw data
        into the final tags contained in `data.json`.
        See the [Data Refinement Data Section](#refinement) for
        more details.
    - `./data-extraction/auxiliary/`
        <br/> Contains paper metadata (demographics data)
        downloaded from Scopus and Crossref.
    - `./data-extraction/data.json`
        <br/> Contains the final refined data for all papers.
        See the [Data Section](#datajson) for more details.
- `./study-selection/`
  - `./study-selection/clustering.py`
        <br/> The script used to perform the clustering of papers
        based on title and abstract. See the
        [Relevant Part of the Scripts & Tools Section](#clustering-)
        for more details.
  - `./study-selection/final-papers.bib`
        <br/> bib file containing reference data for all papers in the
        final selection.
  - `./study-selection/initial/`
        <br> Contains the inclusion/exclusion data per selection round.
    - `./study-selection/initial/round0/`
            <br/> Contains the clusters computed using `clustering.py`
            and a file of inclusion/exclusion decisions for the clusters.
  - `./study-selection/backward-snowballing`
        <br/> Same as `./study-selection/initial/` but for snowballing.
- `plotting/`
  - `plotting.py` & `plot.sh`
    <br/>Used for generating the plots presented in the paper,
    as well as other additional plots.


## Scripts & Tools

### Clustering
`clustering.py` is a utility script which can be used to reproduce the
clustering as described in the paper.

The dependencies of the script are listed in the file itself
in the `pyproject.toml` format, following the  guidelines
for self-contained metadata in scripts.
The dependencies can be installed using a package manager
supporting such metadata in script, or by manually installing
via pip by running

```shell
pip install sentence-transformers pandas umap-learn hdbscan
```

The script was tested using Python 3.11.

The script requires a CSV file as input, which must at least
contain two columns `Title` and `Abstract`.
Note that the Scopus `Export CSV` option is able to output such a CSV
for all studies found using a search query.

The script can be ran using

```shell
python clustering.py -f path/to/csv/file
```

Optionally, a numerical seed can be specified using the `-s` flag.

### Annotator Tool
The annotator tool was used to refine the raw data extracted from the
papers into the final tags as found in `data.json`.

The tool can also be used to conveniently browse all the currently
assigned tags, and view the amount of entries with each tag assigned
(**note: the numbers in the annotator do _not_ match up with
those in the paper because the paper shows number of studies,
while the annotator shows number of times a tag is assigned.
Hence, if a paper uses e.g. GCN multiple times, it is counted
once in the paper but multiple times in the annotator**).
Furthermore, the tool can be used to view the steps in which the raw data was refined to the final
tags.

The tool can be ran by installing the
[Rust programming language](https://www.rust-lang.org/) and running
`cargo run --release` in the directory of the tool.

In the tool, navigate to one of the files in the
`data-extraction/raw/refinement-steps/` directory and open
it to view the tags.

### Plotting
`plotting.py` contains code to generate all plots from the papers, and
also more additional plots. Its dependencies can be installed
using the following command:

```shell
pip install matplotlib seaborn upsetplot alive_progress
```

The script has two types of arguments.
The first one is a positional parameter indicating what to plot,
which must be one of the following:
`domains`, `artefacts`, `graphs`, `features`, `models`

Furthermore, several thresholds are used to determine what
to plot. Specifically, for `graphs`, `features`, and `models`,
techniques occurring in few studies are not plotted.
The thresholds can be set using the command line. Run

```shell
python plotting.py -h
```

to see the complete list of available options.

`plot.sh` is a convenience scripts which generates the plots with the same
settings as done in the paper. It only takes the aforementioned
positional argument as parameter. Alternatively, `all` can be passed
as parameter to the script to generate all plots.

## Data Format

### Raw Data
The raw data extracted from the papers is collected into yaml files
in the `data-extraction/raw/{backward-snowballing,initial}` directories.
The yaml files roughly follow the structure of the data extraction
form as presented in the paper.

There were three different iterations of the data extraction form.
What follows is a brief description:

1. The first data version of the form also collected information about
    hyperparameters, datasets used, and evaluation metrics.
2. The second version of the form contains the fields as described in
    the paper, but instead of a list of `architecture attributes`,
    it contains a paragraph of text describing the machine learning model
3. The form as found in the paper, where `architecture attributes` is a
    list of properties of a machine learning model.

### Refinement
The raw data was later processed into large overarching categories.
The exact process is documented in the files in the
`data-extraction/raw/refinements-steps` directory.

Every file has the following basic format:

```json
{
  "raw": [],
  "refinements": []
}
```

Here, `raw` is a list of (a subset of) the raw data extracted from
the papers. `refinements` is a list of refinement steps.
There are three different types of refinement steps:

#### refine
The `refine` step is a 1-to-1 modification of a tag. An example would be
the generalisation of the feature `node depth in ast` to
`node positional information in ast`.

A `refine` step is documented in the following format:

```json
{
  "action": "refine",
  "old": "old tag",
  "new": "new tag"
}
```

#### split
The `split` operation is used to split a single tag into 2 different
tags. It is documented in the following format:

```json
{
  "action": "split",
  "old": "old tag",
  "new_1": "new tag 1",
  "new_2": "new tag 2"
}
```

#### n-ary split
The `n-ary-split` operation is used to split a single tag into an arbitrary
number of new tags. It is documented in the following format:

```json
{
  "action": "n-ary-split",
  "old": "old tag",
  "new": [
    "list",
    "of",
    "new",
    "tags"
  ]
}
```

The `refinements` list in the refinements file is a list of such
refinement actions, which are supposed to be applied sequentially
to the items in the `raw` list in order to obtain the final list of tags.

### data.json
This file contains all extracted data from all the
papers after applying the refining steps.
It also contains the bibliographical data for
all the included papers.

The top-level entry in the file is an object
mapping the IDs used for the different papers to
the data for said paper.
A typical entry for a single paper
has the following format:

```json
{
  "bibtex": {
    "type": "",
    "info": {}
  },
  "domains": ["list of strings"],
  "artefacts": ["list of strings"],
  "graphs": {
    "graph-id": {
      "vertices": [
        {
          "value": "vertex type",
          "details": "Special details regarding the vertex type",
          "modifiers": "Modifiers (sub-typing)"
        }
      ],
      "edges": [
        {
          "value": "edgex type",
          "details": "Special details regarding the edge type",
          "modifiers": "Modifiers (sub-typing)"
        }
      ],
      "name": "name of the graph (may be `none`)"
    }
  },
  "features": {
    "graph-id": ["list of strings"]
  },
  "models": {
    "model-id": {
      "tags": ["list of strings"],
      "classification-regression-granularity": "",
      "clustering granularity": "",
      "usage-details": ""
    }
  }
}
```

#### `bibtex`
Contains the bibliographical information for the paper,
as returned from the [Crossref](https://www.crossref.org/) API.
The `type` entry denotes the type (`article`, `inproceedings` etc.)
The `info` field contains all information which is
contained in the bibtex entry returned from the API.

#### `domains`
A list of domains the paper belongs to. For studies belonging to
the `misc` domain, the specific sub-domain is inserted in brackets,
e.g. `"misc (code smell detection)"`

#### `artefacts`
List of all the artefacts used in the study.

#### `graphs`
Collection of graphs used in the study. The top-level entry maps
identifiers (assigned during the extraction process) to the
information for every graph. For every graph, we have information
regarding its vertices, edges, and optionally its name.

The name of the graph is assigned by the researchers during the
extraction process and is mostly a mnemonic usable for
quick grouping. The most informative information
comes in the form of the vertices and edges.

For every vertex and edge (type) we record three types of data:
value, details, and modifies. The `value` is the base tag assigned
to the vertex or edge type. The `details`  tag gives more information
for cases where this might be necessary for understanding.
Finally, `modifiers` details how a vertex or edge may differ
from other types with the same `value` (e.g. `modifiers` can be seen
as a sub-type specifier)

#### `features`
Collection of features used in the study. The top-level entry maps
identifiers (corresponding to graph identifiers) to the
features used per graph. Non-graph features are associated with all
graphs. Features are given as a list of assigned tags.

Different types of features can be identified through their
prefixed. For instance, node features are prefixed with
`node feature:` and non-graph features with `other:`.

#### `models`
Collection of models used in the study. The top-level entry maps
identifiers (assigned during the extraction process) to the
information for every model.

For every model, we have a number of different attributes.
The `tags` attribute contains tags describing the model itself.
Examples include its type (e.g. RNN or GNN),
the type of task it is used for (e.g. classification/regression),
and the techniques used (e.g. Graph Attention Network).

The `classification-regression-granularity` field is `null` for
all models that do not perform classification or regression.
For classification or regression models, it contains the level
of granularity at which the model propagates,
which is commonly either `graph` (graph classification)
or `node` (node classification).

`clustering-granularity` is only non-`null` for clustering
models. For such models, it denotes at which level of granularity
the model operates. Usually this is `node` to denote models
which cluster nodes in a single graph together into groups.
The label `graph` denotes models which cluster multiple graphs
together into clusters of graphs.

`usage-details` denotes how the model is used.
It mainly contains two bits of information:
1) Does the model take the graph features or some other features as input.
2) Does the model perform the main classification task, or it is an
    auxiliary model which is used for e.g. embedding.
