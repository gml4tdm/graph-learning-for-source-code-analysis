#!/bin/bash
SHARED_ARGS='--paper-only'
DOMAIN_ARGS=''
ARTEFACT_ARGS=''
FEATURES_ARGS='--min-feature-count 5 --min-feature-upset 2 --min-encoding-count 1'
MODELS_ARGS='--min-gnn-count 5 --min-tree-count 2'
GRAPH_ARGS='--min-vertex-count 5 --min-edge-count 5 --min-edge-upset 5 --min-edge-upset-domains 1'

if [ "$1" = "domains" ];  then
  python3 plotting.py $SHARED_ARGS domains $DOMAIN_ARGS
elif [ "$1" = "artefacts" ]; then
  python3 plotting $SHARED_ARGS artefacts $ARTEFACT_ARGS
elif [ "$1" = "graphs" ]; then
  python3 plotting.py $SHARED_ARGS graphs $GRAPH_ARGS
elif [ "$1" = "features" ]; then
  python3 plotting.py $SHARED_ARGS features $FEATURES_ARGS
elif [ "$1" = "models" ]; then
  python3 plotting.py $SHARED_ARGS models $MODELS_ARGS
elif [ "$1" = "all" ]; then
  python3 plotting.py $SHARED_ARGS domains $DOMAIN_ARGS
  python3 plotting.py $SHARED_ARGS artefacts $ARTEFACT_ARGS
  python3 plotting.py $SHARED_ARGS graphs $GRAPH_ARGS
  python3 plotting.py $SHARED_ARGS features $FEATURES_ARGS
  python3 plotting.py $SHARED_ARGS models $MODELS_ARGS
else
  echo "Invalid argument"
fi