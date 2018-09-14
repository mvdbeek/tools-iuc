from collections import OrderedDict

import click
import pandas as pd
from rpy2.robjects import pandas2ri
from rpy2.robjects.packages import importr


pandas2ri.activate()
zerone = importr('zerone')


def generate_dataframe(controls, treatments):
    c = OrderedDict()
    for control in controls:
        c[control] = pd.read_csv(control, usecols=[3], sep='\t', header=None, dtype=int)[3]

    t = OrderedDict()
    for treatment in treatments:
        t[treatment] = pd.read_csv(treatment, usecols=[3], sep='\t', header=None, dtype=int)[3]

    control_series = pd.DataFrame(c).sum(axis=1)
    control_df = pd.DataFrame(control_series)
    control_df.columns = ['Control']
    treatment_df = pd.DataFrame(t)
    chroms = pd.read_csv(treatments[0], usecols=[0], sep='\t', header=None)
    chroms.columns = ['chrom']
    df = pd.DataFrame.merge(control_df, treatment_df, left_index=True, right_index=True)
    df = chroms.merge(df, left_index=True, right_index=True)
    return df


def discretize(df):
    r = zerone.zerone(df, returnall=True)
    return pandas2ri.ri2py_dataframe(r.rx('path'))['path'] == 2


@click.command()
@click.option('--control_files', type=click.Path(exists=True), multiple=True)
@click.option('--fusion_files', type=click.Path(exists=True), multiple=True, required=True)
@click.option('--output', type=click.Path(exists=False), required=True)
def main(control_files, fusion_files, output):
    """Run zerone discretization for control and fusion files"""
    df = generate_dataframe(controls=control_files, treatments=fusion_files)
    s = discretize(df)
    template = pd.read_csv(control_files[0], usecols=[0, 1, 2], sep='\t', header=None)
    template['result'] = s.astype(int)
    template.to_csv(output, header=None, sep='\t', index=None)


if __name__ == '__main__':
    main()
