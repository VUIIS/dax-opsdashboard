import logging

import pandas as pd
import plotly
import plotly.graph_objs as go
import plotly.subplots
import dash_core_components as dcc
import dash_html_components as html
import dash_table as dt
from dash.dependencies import Input, Output
import dash

from app import app
import data
import utils
from shared import STATUS2RGB, STATUS2HEX


logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.DEBUG, datefmt='%Y-%m-%d %H:%M:%S')


def filter_jobs_data(df, projects, proctypes, user):

    # Filter by project
    if projects:
        df = df[df['PROJECT'].isin(projects)]

    if proctypes:
        df = df[df['PROCTYPE'].isin(proctypes)]

    if user:
        df = df[df['USER'].isin(user)]

    # Return the filtered dataframe
    return df


def get_job_graph_content(df):
    PIVOTS = ['USER', 'PROJECT', 'PROCTYPE']
    tabs_content = []

    # index we are pivoting on to count statuses
    for i, pindex in enumerate(PIVOTS):
        # Make a 1x1 figure
        fig = plotly.subplots.make_subplots(rows=1, cols=1)
        fig.update_layout(margin=dict(l=40, r=40, t=40, b=40))

        # Draw bar for each status, these will be displayed in order
        dfp = pd.pivot_table(
            df, index=pindex, values='LABEL', columns=['STATUS'],
            aggfunc='count', fill_value=0)

        for status, color in STATUS2RGB.items():
            ydata = sorted(dfp.index)
            if status not in dfp:
                xdata = [0] * len(dfp.index)
            else:
                xdata = dfp[status]

            fig.append_trace(go.Bar(
                x=xdata,
                y=ydata,
                name='{} ({})'.format(status, sum(xdata)),
                marker=dict(color=color),
                opacity=0.9, orientation='h'), 1, 1)

        # Customize figure
        fig['layout'].update(barmode='stack', showlegend=True, width=900)

        # Build the tab
        label = 'By {}'.format(pindex)
        graph = html.Div(dcc.Graph(figure=fig), style={
            'width': '100%', 'display': 'inline-block'})
        tab = dcc.Tab(label=label, value=str(i + 1), children=[graph])

        # Append the tab
        tabs_content.append(tab)

    return tabs_content


def get_job_content(df):
    JOB_SHOW_COLS = ['LABEL', 'STATUS', 'LASTMOD', 'WALLTIME', 'JOBID']

    job_graph_content = get_job_graph_content(df)

    job_columns = [{"name": i, "id": i} for i in JOB_SHOW_COLS]

    job_data = df.to_dict('records')

    job_content = [
        dcc.Loading(id="loading-job", children=[
            html.Div(dcc.Tabs(
                id='tabs-job',
                value='1',
                children=job_graph_content,
                vertical=True))]),
        html.Button('Refresh Data', id='button-job-refresh'),
        dcc.Dropdown(
            id='dropdown-job-proj', multi=True,
            placeholder='Select Project(s)'),
        dcc.Dropdown(
            id='dropdown-job-user', multi=True,
            placeholder='Select User(s)'),
        dcc.Dropdown(
            id='dropdown-job-proc', multi=True,
            placeholder='Select Processing Type(s)'),
        dt.DataTable(
            columns=job_columns,
            data=job_data,
            filter_action='native',
            page_action='none',
            sort_action='native',
            id='datatable-job',
            style_cell={'textAlign': 'left', 'padding': '5px'},
            style_data_conditional=[
                {'if': {'column_id': 'STATUS'}, 'textAlign': 'center'},
                {'if': {'filter_query': '{STATUS} = "RUNNING"'},  'backgroundColor': STATUS2HEX['RUNNING']},
                {'if': {'filter_query': '{STATUS} = "WAITING"'},  'backgroundColor': STATUS2HEX['WAITING']},
                {'if': {'filter_query': '{STATUS} = "PENDING"'},  'backgroundColor': STATUS2HEX['PENDING']},
                {'if': {'filter_query': '{STATUS} = "UNKNOWN"'},  'backgroundColor': STATUS2HEX['UNKNOWN']},
                {'if': {'filter_query': '{STATUS} = "FAILED"'},   'backgroundColor': STATUS2HEX['FAILED']},
                {'if': {'filter_query': '{STATUS} = "COMPLETE"'}, 'backgroundColor': STATUS2HEX['COMPLETE']},
                {'if': {'column_id': 'STATUS', 'filter_query': '{STATUS} = ""'}, 'backgroundColor': 'white'}
            ],
            style_header={'backgroundColor': 'white', 'fontWeight': 'bold'},
            fill_width=True,
            export_format='xlsx',
            export_headers='names',
            export_columns='visible')]

    return job_content


def get_layout():
    job_content = get_job_content(load_data())

    report_content = [
        html.Div(
            dcc.Tabs(id='tabs', value='1', vertical=False, children=[
                dcc.Tab(label='Job Queue', value='1', children=job_content),
            ]),
            style={
                'width': '100%', 'display': 'flex',
                'align-items': 'center', 'justify-content': 'center'})]

    footer_content = [
        html.Hr(),
        html.H5('UNKNOWN: status is ambiguous or incomplete'),
        html.H5('FAILED: job has failed, but has not yet been uploaded'),
        html.H5('COMPLETE: job has finished, but not yet been uploaded'),
        html.H5('RUNNING: job is currently running on the cluster'),
        html.H5('PENDING: job has been submitted, but is not yet running'),
        html.H5('WAITING: job has been built, but is not yet submitted')]

    return html.Div([
                html.Div(children=report_content, id='report-content'),
                html.Div(children=footer_content, id='footer-content')])


def load_data():
    return data.load_data()


def refresh_data():
    return data.refresh_data()


def was_triggered(callback_ctx, button_id):
    result = (
        callback_ctx.triggered and
        callback_ctx.triggered[0]['prop_id'].split('.')[0] == button_id)

    return result


@app.callback(
    [Output('dropdown-job-proc', 'options'),
     Output('dropdown-job-proj', 'options'),
     Output('dropdown-job-user', 'options'),
     Output('datatable-job', 'data'),
     Output('tabs-job', 'children')],
    [Input('dropdown-job-proc', 'value'),
     Input('dropdown-job-proj', 'value'),
     Input('dropdown-job-user', 'value'),
     Input('button-job-refresh', 'n_clicks')])
def update_everything(
        selected_proc,
        selected_proj,
        selected_user,
        n_clicks
):
    logging.debug('update')

    # Load the data
    ctx = dash.callback_context
    if was_triggered(ctx, 'button-job-refresh'):
        # Refresh data if refresh button clicked
        logging.debug('refresh:clicks={}'.format(n_clicks))
        df = refresh_data()
    else:
        df = load_data()

    # Get the dropdown options
    proc = utils.make_options(df.PROCTYPE.unique())
    proj = utils.make_options(df.PROJECT.unique())
    user = utils.make_options(df.USER.unique())

    logging.debug('applying data filters')
    df = filter_jobs_data(
        df,
        selected_proj,
        selected_proc,
        selected_user)

    logging.debug('getting job graph content')
    tabs = get_job_graph_content(df)

    # Extract records from dataframe
    records = df.to_dict('records')

    # Return dropdown options, table, figure
    logging.debug('update_everything:returning data')
    return [proc, proj, user, records, tabs]


# Build the layout that will used by top level index.py
layout = get_layout()
