import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import dash_auth

from app import app
import ops
from secrets import VALID_USERNAME_PASSWORD_PAIRS

server = app.server  # for gunicorn to work correctly

# Make the main app layout
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div([html.H1('DAX Ops Dashboard')]),
    html.Div(id='page-content')])

# This loads a css template maintained by the Dash developer
app.css.config.serve_locally = False
app.css.append_css({
    'external_url': 'https://codepen.io/chriddyp/pen/bWLwgP.css'})

# Set the title to appear on web pages
app.title = 'DAX ops Dashboard'

# Use very basic authentication
auth = dash_auth.BasicAuth(app, VALID_USERNAME_PASSWORD_PAIRS)


# Make the callback to load pages, others could be added here
@app.callback(
    Output('page-content', 'children'),
    [Input('url', 'pathname')])
def display_page(pathname):
    print('display_page:')
    return ops.layout


if __name__ == '__main__':
    app.run_server(host='0.0.0.0')
