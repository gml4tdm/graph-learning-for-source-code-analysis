# A Systematic Mapping Study on Graph Machine Learning for Static Source Code Analysis

## Content

- [Repository Files](#directory-structure-)
  - [Directory Structure](#repository-directory-structure)
  - [File Descriptions](#overview-of-files)
- [Runnable Scripts & Tools](#scripts--tools)
  - [Clustering](#clustering)
  - [Annotator Tool](#annotator-tool)
  - [libedit.py](#libedit-)
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
        [Relevant Part of the Scripts & Tools Section](#clustering) 
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
  - `libedit.py`
    <br/> Script for dealing with the refinement data. 
    See the [Entry in the Tool Section](#libedit-) and 
    the [Entry in the Data Section](#refinement) for more details.
  - `plotting.py` & `plot.sh`
    <br/>Used for generating the plots presented in the paper,
    as well as other additional plots.
    

## Scripts & Tools

### Clustering

### Annotator Tool
The annotator tool was used to refine the raw data extracted from the 
papers into the final tags as found in `data.json`. 

The tool can also be used to conveniently browse all the currently 
assigned tags, and view the amount of entries with each tag assigned
(**note: there is currently a bug in the tool which causes the exact
counts in the tool to be incorrect. They are currently only suitable as 
an estimate of the order of magnitude**).

The tool can be ran by installing the 
[Rust programming language](https://www.rust-lang.org/) and running
`cargo run --release` in the directory of the tool. 

In the tool, navigate to one of the files in the 
`data-extraction/raw/refinement-steps/` directory and open 
it to view the tags.

### Libedit 
`libedit.py` is a small library to handle the refinement files at a more 
fine-grained level.

### Plotting

## Data Format

### Raw Data

### Refinement

### data.json