import polars as pl
from sklearn.metrics import cohen_kappa_score, accuracy_score


def agreement_round_0():
    AUTHOR_A_COLUMN = 'Included/Excluded (Author 1)'
    AUTHOR_B_COLUMN = 'Author 2'

    df = pl.read_csv('round0/round0.csv')
    author_a = []
    author_b = []
    for row in df.rows(named=True):
        author_a.append(row[AUTHOR_A_COLUMN].lower() == 'include')
        author_b.append(row[AUTHOR_B_COLUMN].lower() == 'include')
    print('Agreement:', accuracy_score(author_a, author_b))
    print('Kappa:', cohen_kappa_score(author_a, author_b))


def agreement_round_1():
    AUTHOR_A_COLUMN = 'Include/Exclude'
    AUTHOR_B_COLUMN = 'Author 2'

    df = pl.read_csv('round1.csv')
    author_a = []
    author_b = []
    for row in df.rows(named=True):
        if not row[AUTHOR_B_COLUMN]:
            continue    # Paper not double-checked
        author_a.append(row[AUTHOR_A_COLUMN].lower() == 'include')
        author_b.append(row[AUTHOR_B_COLUMN].lower() == 'include')
    print('Agreement:', accuracy_score(author_a, author_b))
    print('Kappa:', cohen_kappa_score(author_a, author_b))


def agreement_round_2():
    INCLUDE_AUTHOR_A_RE_TAG = True
    INCLUDE_AUTHOR_B_RE_TAG = True
    AUTHOR_A_MAIN_COLUMN = 'Included/Excluded'
    AUTHOR_A_RE_TAG_COLUMN = 'Author 1 Re-tag'
    AUTHOR_B_MAIN_COLUMN = 'Author 2'
    AUTHOR_B_RE_TAG_COLUMN = 'Author 2 Re-tag'

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


def main():
    print('Round 0')
    agreement_round_0()
    print('=' * 72)
    print('Round 1')
    agreement_round_1()
    print('=' * 72)
    print('Round 2')
    agreement_round_2()



if __name__ == '__main__':
    main()
