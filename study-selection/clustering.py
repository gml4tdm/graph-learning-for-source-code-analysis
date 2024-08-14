# /// script
# dependencies = [
#   "pandas",
#   "umap-learn",
#   "hdbscan",
#   "sentence-transformers"
# ]
# requires-python = ">=3.11"
# ///

import argparse

import hdbscan
import pandas as pd
from umap import UMAP
from sentence_transformers import SentenceTransformer


def main(filename: str, seed: int):
    print('Loading data from CSV file...')
    df = pd.read_csv(filename)
    documents = df[['Title', 'Abstract']].apply('. '.join, axis=1).values.tolist()

    print('Embedding using SentenceTransformer...')
    model = SentenceTransformer('sentence-transformers/paraphrase-distilroberta-base-v1')
    embeddings = model.encode(documents, show_progress_bar=True)

    print('Reducing dimensionality with UMAP...')
    umap = UMAP(n_neighbors=15,
                n_components=5,
                min_dist=0.0,
                metric='cosine',
                random_state=seed)
    projections = umap.fit_transform(embeddings)

    print('Clustering with HDBSCAN...')
    clusterer = hdbscan.HDBSCAN(min_cluster_size=10,
                                min_samples=3,
                                cluster_selection_epsilon=0.2,
                                cluster_selection_method='leaf')
    labels = clusterer.fit_predict(projections)

    print('Saving results to CSV file...')
    df['Cluster'] = labels
    df.to_csv('clusters.csv', index=False)

    print('Results saved to `clusters.csv`')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__name__)
    parser.add_argument('--file', '-f', type=str, required=True)
    parser.add_argument('--seed', '-s', type=int, default=42)
    args = parser.parse_args()
    main(args.file, args.seed)
