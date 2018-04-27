import os
import click
import matplotlib
matplotlib.use('agg')

import pandas as pd  # noqa: E402
import seaborn as sns   # noqa: E402


def get_dataframe(files, labels, column, skiprows=1, sep='\t'):
    d = {}
    for file, label in zip(files, labels):
        d[label] = pd.read_csv(file, usecols=[column], sep=sep, skiprows=skiprows, header=None, squeeze=True)
    return pd.DataFrame.from_dict(d)


def plot_correlation(df, plot_path=None, method='pearson', correlation_matrix_path=None, figsize=(12, 12)):
    corr = df.corr(method=method)
    if correlation_matrix_path:
        corr.to_csv(correlation_matrix_path, sep="\t")
    if plot_path:
        g = sns.clustermap(corr, annot=True, method="centroid", figsize=figsize, cbar_kws={'label': "%s correlation" % method})
        g.fig.suptitle("Cluster based on %s correlation for all samples" % method)
        g.savefig(plot_path, bbox_inches='tight')


@click.command()
@click.argument("files", type=click.Path(exists=True), nargs=-1, required=True)
@click.option("-c", "--column", help="Use this numeric column to calculate correlation across files", default=1, required=True)
@click.option("--labels", help="File containing a list of labels, one label per line. Must match number of files", type=click.Path(exists=True), required=False)
@click.option("--plot_path", help="Write correlation plot to this path", type=click.Path(exists=False), required=False)
@click.option("--correlation_matrix_path", help="Write correlation plot to this path", type=click.Path(exists=False), required=False)
@click.option("--method", help="Use this method for calculating the correlation", required=False, type=click.Choice(['pearson', 'spearman', 'kendall']))
@click.option("--skiprows", help="Skip this number of rows", required=False, default=0)
@click.option("--sep", help="Use this field separator when reading files", required=False, default="\t")
def main(files, column, labels=None, method="pearson", skiprows=1, plot_path=None, correlation_matrix_path=None, figsize=(12, 12), sep='\t'):
    """Plot heatmap of pearson correlation and/or write matrix of pearson correlation values."""
    if labels:
        labels = [l.strip() for l in open(labels) if l.strip()]
        assert len(labels) == len(files), "Got %d files for plotting, but %d labels. Label and file length must be equal" % (len(files), len(labels))
    if not labels:
        labels = [os.path.basename(f) for f in files]
    if column != -1:
        # Adjust for 0-based column selection
        column -= 1
    df = get_dataframe(files, labels, column=column, skiprows=skiprows, sep=sep)
    plot_correlation(df, plot_path=plot_path, correlation_matrix_path=correlation_matrix_path, figsize=figsize, method=method)


if __name__ == '__main__':
    main()
