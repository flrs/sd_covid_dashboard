from itertools import cycle
from typing import Optional, List, Union
import plotly.graph_objects as go
from pandas.core.util.hashing import hash_pandas_object
from plotly.colors import qualitative
from .db_helpers import get_cases_per_week_by_zip, get_cases_by_week
from .data_helpers import add_cases_per_100k_col, get_population_per_zip
import pandas as pd

ZIP_COLORS = cycle(qualitative.Plotly)
next(ZIP_COLORS)
next(ZIP_COLORS)

CACHED_REL_TRENDS_HASH: Optional[pd.Series] = None
CACHED_REL_TRENDS: Optional[pd.DataFrame] = None


def _get_rel_trends(data):
    global CACHED_REL_TRENDS, CACHED_REL_TRENDS_HASH

    hash = hash_pandas_object(data)
    if CACHED_REL_TRENDS_HASH is not None and CACHED_REL_TRENDS_HASH.equals(hash):
        return CACHED_REL_TRENDS

    end_date = data['date'].max()

    def rel_trend(group):
        nonlocal end_date
        all_keys = pd.date_range(start=group['date'].min(), end=end_date, freq='7d')
        group = pd.Series(group['cases_per_100k'].values, index=group['date'])
        zip_data = pd.Series(index=all_keys, dtype='float')
        group = zip_data.align(group, join='left', fill_value=0)[1]
        return group

    rel_trends = data.groupby('zip').apply(rel_trend).reset_index()
    rel_trends = rel_trends.rename(columns={0: 'cases_per_100k'})
    CACHED_REL_TRENDS_HASH = hash
    CACHED_REL_TRENDS = rel_trends
    return rel_trends


def plot_cases_per_week_by_zip(data_with_cases_per_100k: Optional[pd.DataFrame] = None,
                               population_per_zip: Optional[pd.DataFrame] = None,
                               zips: Optional[Union[int, List[int]]] = None,
                               title: str = 'Weekly Covid-19 Cases per 100k Residents by San Diego County ZIP Code',
                               fig: Optional = None):
    if data_with_cases_per_100k is None:
        data = get_cases_per_week_by_zip()
        data = add_cases_per_100k_col(data)
    else:
        data = data_with_cases_per_100k

    if population_per_zip is None:
        population_per_zip = get_population_per_zip()

    if zips is None:
        zips = []
    if isinstance(zips, int):
        zips = [zips]

    rel_trends = _get_rel_trends(data)

    if fig is None:
        listed_zips = list(data['zip'].unique())
        all_pop = population_per_zip[listed_zips].sum()
        data_overall = get_cases_by_week()
        data_overall['cases_per_100k'] = data_overall['cases'] / (all_pop / 100000)

        q10 = rel_trends.groupby('date')['cases_per_100k'].quantile(0.1)
        q25 = rel_trends.groupby('date')['cases_per_100k'].quantile(0.25)
        mean = pd.Series(data_overall['cases_per_100k'].values, index=data_overall['date'])
        q75 = rel_trends.groupby('date')['cases_per_100k'].quantile(0.75)
        q90 = rel_trends.groupby('date')['cases_per_100k'].quantile(0.9)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=q10.index, y=q10.values,
                                 fill=None,
                                 mode='lines',
                                 line=dict(width=1),
                                 line_color='rgba(131,179,213,0.6)',
                                 legendgroup='q90',
                                 showlegend=False,
                                 hoverinfo='skip'
                                 ))
        fig.add_trace(go.Scatter(
            x=q90.index,
            y=q90.values,
            fill='tonexty',  # fill area between trace0 and trace1
            mode='lines',
            line=dict(width=1),
            line_color='rgba(131,179,213,0.6)',
            legendgroup='q90',
            name='90% of all ZIP Codes',
            hoverinfo='skip'
        ))

        fig.add_trace(go.Scatter(x=q25.index, y=q25.values,
                                 fill=None,
                                 mode='lines',
                                 line=dict(width=1),
                                 line_color='rgba(72,141,190,0.6)',
                                 legendgroup='q75',
                                 showlegend=False,
                                 hoverinfo='skip'
                                 ))
        fig.add_trace(go.Scatter(
            x=q75.index,
            y=q75.values,
            fill='tonexty',  # fill area between trace0 and trace1
            mode='lines',
            line=dict(width=1),
            line_color='rgba(72,141,190,0.6)',
            legendgroup='q90',
            name='50% of all ZIP Codes',
            hoverinfo='skip'
        ))
        fig.add_trace(go.Scatter(
            x=mean.index,
            y=mean.values,
            mode='lines',
            line=dict(width=3, color='rgba(4,67,111,0.9)'),
            name='Average of all ZIP Codes',
            hovertemplate='Average: %{y:.1f}<extra></extra>',
        ))

        fig.update_yaxes(rangemode='nonnegative')
        fig.update_layout(
            title=title,
            xaxis_title="Week",
            yaxis_title="Cases per 100k Residents",
            hovermode='x unified',
            margin=dict(l=90, r=90, t=30, b=90)
        )
    else:
        print('zips incoming in function')
        print(zips)
        print('current zips in graph')
        for data in fig.data:
            if data['name'].startswith('ZIP Code'):
                print(int(data['name'].replace('ZIP Code ', '')))
                if int(data['name'].replace('ZIP Code ', '')) in zips:
                    print('--> keep {}'.format(int(data['name'].replace('ZIP Code ', ''))))
        print('-----')
        fig.data = [data for data in fig.data \
                    if (data['name'].startswith('ZIP Code') and int(data['name'].replace('ZIP Code ', '')) in zips) \
                    or (not data['name'].startswith('ZIP Code'))]
        existing_zips = [int(data['name'].replace('ZIP Code ', '')) for data in fig.data \
                         if data['name'].startswith('ZIP Code')]
        print('existing')
        print(existing_zips)
        zips = [zip for zip in zips if zip not in existing_zips]
        print('to add')
        print(zips)
        print('%%%%%%%%%%%%%%%%%%%')
    for zip in zips:
        zip_data = rel_trends[rel_trends['zip'] == zip][['date', 'cases_per_100k']]
        zip_data = pd.Series(zip_data['cases_per_100k'].values, index=zip_data['date'])

        fig.add_trace(go.Scatter(
            x=zip_data.index,
            y=zip_data.values,
            mode='lines',
            line=dict(width=5, color=next(ZIP_COLORS)),
            name='ZIP Code {}'.format(zip),
            hovertemplate=str(zip) + ': %{y:.1f}<extra></extra>'))

    return fig
