import polars as pl
from sklearn.metrics import cohen_kappa_score, accuracy_score


INCLUDE_AUTHOR_A_RE_TAG = True
INCLUDE_AUTHOR_B_RE_TAG = True
AUTHOR_A_MAIN_COLUMN = 'Included/Excluded'
AUTHOR_A_RE_TAG_COLUMN = 'Author 1 Re-tag'
AUTHOR_B_MAIN_COLUMN = 'Author 2'
AUTHOR_B_RE_TAG_COLUMN = 'Author 2 Re-tag'


def main():
    df = pl.read_csv('round2.csv')
    author_a = []
    author_b = []
    for row in df.rows(named=True):
        # First, check that this paper was double-checked
        if not row[AUTHOR_B_MAIN_COLUMN]:
            continue
        # Extract labels
        if INCLUDE_AUTHOR_A_RE_TAG and row[AUTHOR_A_RE_TAG_COLUMN]:
            author_a.append(row[AUTHOR_A_RE_TAG_COLUMN].lower() == 'include')
        else:
            author_a.append(row[AUTHOR_A_MAIN_COLUMN].lower() == 'include')
        if INCLUDE_AUTHOR_B_RE_TAG and row[AUTHOR_B_RE_TAG_COLUMN]:
            author_b.append(row[AUTHOR_B_RE_TAG_COLUMN].lower() == 'include')
        else:
            author_b.append(row[AUTHOR_B_MAIN_COLUMN].lower() == 'include')
    print('Agreement:', accuracy_score(author_a, author_b))
    print('Kappa:', cohen_kappa_score(author_a, author_b))


if __name__ == '__main__':
    main()
