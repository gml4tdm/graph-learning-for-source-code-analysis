import polars


def main():
    base = polars.read_csv('./SMS - Selection Round 3.csv')
    supplement = polars.read_csv('./SMS - Selection Round 3 -- Supplement.csv')

    supplement = supplement.rename({'Inclusion': 'Included/Excluded'})

    print(base.columns, supplement.columns)
    order = [
        'Authors',
        'Title',
        'Abstract',
        'Document Type',
        'Year',
        'Link',
        'Source title',
        #'Paper Available',
        'Round 3 ID',
        'Included/Excluded',
        'Reason',
        #'Needs Double Check',
        'Notes'
    ]
    base = base.drop(*(x for x in base.columns if x not in order))
    supplement = supplement.drop(*(x for x in supplement.columns if x not in order))
    base = base.select([polars.col(x) for x in order])
    supplement = supplement.select([polars.col(x) for x in order])
    base = base.extend(supplement)

    mapping = {
        'Exclude - Double Check': 'Exclude',
        'Include -  Double Check Results': 'Include',
        'Exclude': 'Exclude',
        'Include -- Linearised AST': 'Include',
        'Include': 'Include',
        'Include -- Double Check Inclusion': 'Include'
    }

    base = base.with_columns(temp=polars.col('Included/Excluded').replace(mapping))
    base = base.drop('Included/Excluded')
    base = base.rename({'temp': 'Included/Excluded'})
    base = base.select([polars.col(x) for x in order])

    base.write_csv('./round3.csv')


if __name__ == '__main__':
    main()
