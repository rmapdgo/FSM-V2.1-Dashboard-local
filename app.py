import dash
from dash import Dash, dcc, html, Input, Output, State, callback, ctx
import boto3
import base64
import json
import io
import openpyxl
import dash_daq as daq
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import glob
from src.snirf.create_snirf import create_snirf
from src.data_quality_check.data_quality_check import data_quality_check
import numpy as np
from src.concentrations_ucln_srs.ucln_srs import UCLN, SRS
from src.concentrations_ucln_srs.dualSlope import dual_slope_wavelength
import plotly.express as px
import flask
import plotly.graph_objects as go
import os
from openpyxl.utils.dataframe import dataframe_to_rows
import plotly.express as px
import logging
import os
from scipy.signal import butter, filtfilt, medfilt
import numpy as np
import pandas as pd
from dash import callback_context
from dash import html, callback_context
import base64
from dash.exceptions import PreventUpdate
import xlsxwriter
import io
from openpyxl.utils.dataframe import dataframe_to_rows
import openpyxl
from datetime import datetime
from dash import no_update
from datetime import datetime, timedelta
from plotly.subplots import make_subplots
from io import StringIO
from dash import Dash, dcc, html, Input, Output, State, callback, ctx, no_update, callback_context
import dash_bootstrap_components as dbc
import dash_daq as daq
import plotly.graph_objects as go
import plotly.express as px
import flask
import boto3
import openpyxl
import xlsxwriter
import numpy as np
import pandas as pd
#from scipy.signal import butter, filtfilt, medfilt
import h5py


# Create the Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# AWS S3 client setup
s3 = boto3.client('****',
    aws_access_key_id='***',
    aws_secret_access_key='****'
)

# Bucket mapping
bucket_map = {
    'upload-raw': '***',
    'upload-concentration':'***',
    'upload-ctg': '***'
}

# Upload modal component
def get_upload_modal():
    return html.Div(
        id='upload-modal',
        style={
            'display': 'none',
            'position': 'fixed',
            'top': '0',
            'left': '0',
            'width': '100%',
            'height': '100%',
            'backgroundColor': 'rgba(0, 0, 0, 0.6)',
            'zIndex': '1000',
            'display': 'flex',
            'justifyContent': 'center',
            'alignItems': 'center',
            'backdropFilter': 'blur(4px)'
        },
        children=html.Div(
            style={
                'background': 'linear-gradient(135deg, #ffffff 0%, #f0f4ff 100%)',
                'padding': '40px 50px',
                'borderRadius': '20px',
                'width': '520px',
                'boxShadow': '0 12px 30px rgba(0, 0, 0, 0.25)',
                'textAlign': 'left',
                'fontFamily': "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
                'color': '#333',
                'position': 'relative'
            },
            children=[
                html.H2("Upload data to cloud", style={
                    'marginBottom': '30px',
                    'fontWeight': '700',
                    'fontSize': '2rem',
                    'textAlign': 'center'
                }),

                html.Div([
                    html.H4("Raw intensity data", style={'marginBottom': '8px', 'fontWeight': '600'}),
                    dcc.Upload(
                        id='upload-raw',
                        children=html.Div(["Drag and drop or click to select files"]),
                        style={
                            'padding': '20px',
                            'border': '2px dashed #007BFF',
                            'borderRadius': '12px',
                            'marginBottom': '10px',
                            'cursor': 'pointer',
                            'fontSize': '1rem',
                            'color': '#007BFF',
                            'backgroundColor': '#f9faff',
                            'textAlign': 'center',
                        },
                        multiple=False
                    ),
                    html.Div(id='filename-raw', style={'marginBottom': '20px', 'color': '#007BFF'})
                ]),

                html.Div([
                    html.H4("Concentrations data", style={'marginBottom': '8px', 'fontWeight': '600'}),
                    dcc.Upload(
                        id='upload-concentration',
                        children=html.Div(["Drag and drop or click to select files"]),
                        style={
                            'padding': '20px',
                            'border': '2px dashed #28a745',
                            'borderRadius': '12px',
                            'marginBottom': '10px',
                            'cursor': 'pointer',
                            'fontSize': '1rem',
                            'color': '#28a745',
                            'backgroundColor': '#f4fff7',
                            'textAlign': 'center',
                        },
                        multiple=False
                    ),
                    html.Div(id='filename-concentration', style={'marginBottom': '20px', 'color': '#28a745'})
                ]),

                html.Div([
                    html.H4("CTG data", style={'marginBottom': '8px', 'fontWeight': '600'}),
                    dcc.Upload(
                        id='upload-ctg',
                        children=html.Div(["Drag and drop or click to select files"]),
                        style={
                            'padding': '20px',
                            'border': '2px dashed #fd7e14',
                            'borderRadius': '12px',
                            'marginBottom': '10px',
                            'cursor': 'pointer',
                            'fontSize': '1rem',
                            'color': '#fd7e14',
                            'backgroundColor': '#fff8f1',
                            'textAlign': 'center',
                        },
                        multiple=False
                    ),
                    html.Div(id='filename-ctg', style={'marginBottom': '30px', 'color': '#fd7e14'})
                ]),

                html.Div(
                    style={'display': 'flex', 'justifyContent': 'center', 'gap': '20px'},
                    children=[
                        html.Button('Submit', id='submit-modal', n_clicks=0, style={
                            'padding': '12px 32px',
                            'fontSize': '1rem',
                            'borderRadius': '30px',
                            'border': 'none',
                            'backgroundColor': '#28a745',
                            'color': 'white',
                            'cursor': 'pointer',
                            'fontWeight': '600',
                        }),
                        html.Button('Close', id='close-modal', n_clicks=0, style={
                            'padding': '12px 32px',
                            'fontSize': '1rem',
                            'borderRadius': '30px',
                            'border': 'none',
                            'backgroundColor': '#dc3545',
                            'color': 'white',
                            'cursor': 'pointer',
                            'fontWeight': '600',
                        })
                    ]
                ),

                html.Div(id='upload-alerts', style={'marginTop': '20px'})
            ]
        )
    )


# Layout
app.layout = html.Div([
    html.Div(
        style={
            'height': '70px',
            'padding': '0 15px',
            'background': '#003f5c',
            'color': 'white',
            'display': 'flex',
            'alignItems': 'center',
            'justifyContent': 'space-between',
            'fontSize': '30px',
            'fontWeight': '100',
            'boxShadow': '0 4px 8px rgba(0, 0, 0, 0.2)',
            'borderBottom': '5px solid #ed6a28'
        },
        children=[
            html.H1('FetalsenseM V2.1 Dashboard', style={'margin': '0'}),
            html.Button(
                'Upload to cloud', id='upload-cloud-button', n_clicks=0,
                style={
                    'height': '40px',
                    'borderWidth': '1px',
                    'borderStyle': 'dashed',
                    'borderRadius': '5px',
                    'textAlign': 'center',
                    'fontSize': '18px',
                    'marginRight': '0px',
                    'padding': '0 15px',
                    'cursor': 'pointer'
                }
            ),
        ]
    ),
    get_upload_modal(),  # Add modal to layout
    html.Br(),
    # Flex container for the left and right sections
    html.Div([
        # Left side (1/4th width)
        html.Div([
            # Tabs for General, Data Clean, Data Analysis, and Concentrations
            dcc.Tabs(id='left-tabs', children=[
                dcc.Tab(label='General', children=[
                    # File Upload Section inside the General tab
                    html.Div([
                        html.Div([
                            html.H3('File Upload', style={
                                'background': '#003f5c',
                                'padding': '15px',
                                'textAlign': 'center',
                                'color': 'white',
                                'fontWeight': 'bold',
                                'fontSize': '48px'
                            }),
                            dcc.Upload(
                                id='upload-data',
                                children=html.Div(['Drag and Drop or ', html.A('Select Files')]),
                                style={'width': '95%', 'height': '70px', 'lineHeight': '70px',
                                       'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
                                       'textAlign': 'center', 'margin': '15px', 'fontSize': '24px'},
                                multiple=False,
                            ),
                        ]),
                        html.Div(id='file-names'),
                        dcc.Store(id='store-file-path'),
                        html.Br(),
                        html.Div([
                            html.H3('Download SNIRF', style={
                                'background': '#003f5c',
                                'padding': '15px',
                                'textAlign': 'center',
                                'color': 'white',
                                'fontWeight': 'bold',
                                'fontSize': '48px'
                            }),
                            html.Button("Download Raw Data SNIRF", id="btn_rawdata_snirf", style={
                                'width': '95%', 'height': '70px', 'lineHeight': '70px',
                                'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
                                'textAlign': 'center', 'margin': '15px', 'fontSize': '24px'}),
                            dcc.Download(id="download-file-snirf"),
                            dcc.Store(id="snirf-download-status"),
                            html.Div(id='snirf-download-display', style={
    'fontSize': '18px',
    'textAlign': 'center',
    'color': '#2B2D42',
    'marginTop': '10px',
    'fontFamily': 'Courier New'
}),
                        ]),
                        html.Br(),
                        html.Div([
                            html.H3('View Intensities', style={
                                'background': '#003f5c',
                                'padding': '15px',
                                'textAlign': 'center',
                                'color': 'white',
                                'fontWeight': 'bold',
                                'fontSize': '48px'
                            }),
                            html.Div([
                                html.H4('Select one or more:', style={
                                    'textAlign': 'left',
                                    'fontSize': '30px',
                                    'marginBottom': '15px',
                                    'color': '#003f5c',
                                    "font-weight": "100"
                                }),
                                dcc.Dropdown(
                                    id='intensities-options-dropdown',
                                    options=[{'label': option, 'value': option} for option in [
                                        'LED_A_782_DET1', 'LED_A_782_DET2', 'LED_A_782_DET3',
                                        'LED_A_801_DET1', 'LED_A_801_DET2', 'LED_A_801_DET3',
                                        'LED_A_808_DET1', 'LED_A_808_DET2', 'LED_A_808_DET3',
                                        'LED_A_828_DET1', 'LED_A_828_DET2', 'LED_A_828_DET3',
                                        'LED_A_848_DET1', 'LED_A_848_DET2', 'LED_A_848_DET3',
                                        'LED_A_887_DET1', 'LED_A_887_DET2', 'LED_A_887_DET3',
                                        'LED_A_DARK_DET1', 'LED_A_DARK_DET2', 'LED_A_DARK_DET3',
                                        'LED_B_782_DET1', 'LED_B_782_DET2', 'LED_B_782_DET3',
                                        'LED_B_801_DET1', 'LED_B_801_DET2', 'LED_B_801_DET3',
                                        'LED_B_808_DET1', 'LED_B_808_DET2', 'LED_B_808_DET3',
                                        'LED_B_828_DET1', 'LED_B_828_DET2', 'LED_B_828_DET3',
                                        'LED_B_848_DET1', 'LED_B_848_DET2', 'LED_B_848_DET3',
                                        'LED_B_887_DET1', 'LED_B_887_DET2', 'LED_B_887_DET3',
                                        'LED_B_DARK_DET1', 'LED_B_DARK_DET2', 'LED_B_DARK_DET3'
                                    ]],
                                    multi=True,
                                    value=[],
                                    style={'borderColor': '#003f5c', 'fontSize': '24px'}
                                )
                            ]),
                            html.Div(id='intensity-selection-status', children='Select to view', style={
                                'fontFamily': 'Courier New',
                                'fontSize': '20px',
                                'textAlign': 'center',
                                'marginTop': '15px',
                                'color': '#2B2D42'
                            }),
                            html.Br(),
                            html.Div([
        html.H4('Select Groups', style={
        'textAlign': 'left',
        'fontSize': '30px',
        'marginBottom': '15px',
        'color': '#003f5c',
        "font-weight": "100"
    }),
    # Group A and Group B selectors placed side by side using flexbox
    html.Div([
        html.Div([
            html.H4('GroupA_Detector1', style={'fontSize': '20px', 'color': '#003f5c', "font-weight": "100"}),
            daq.BooleanSwitch(
                id='groupA_dect1_spectras',
                on=False,
                style={'transform': 'scale(1.1)'}
            )
        ], style={'display': 'flex', 'alignItems': 'center', 'flex': '1', 'marginRight': '10px'}),

        html.Div([
            html.H4('GroupB_Detector1', style={'fontSize': '20px', 'color': '#003f5c', "font-weight": "100"}),
            daq.BooleanSwitch(
                id='groupB_dect1_spectras',
                on=False,
                style={'transform': 'scale(1.1)'}
            )
        ], style={'display': 'flex', 'alignItems': 'center', 'flex': '1', 'marginLeft': '10px'})
    ], style={'display': 'flex', 'marginBottom': '10px'}),  # Flexbox for side-by-side
    
    html.Div([
        html.Div([
            html.H4('GroupA_Detector2', style={'fontSize': '20px', 'color': '#003f5c', "font-weight": "100"}),
            daq.BooleanSwitch(
                id='groupA_dect2_spectras',
                on=False,
                style={'transform': 'scale(1.1)'}
            )
        ], style={'display': 'flex', 'alignItems': 'center', 'flex': '1', 'marginRight': '10px'}),

        html.Div([
            html.H4('GroupB_Detector2', style={'fontSize': '20px', 'color': '#003f5c', "font-weight": "100"}),
            daq.BooleanSwitch(
                id='groupB_dect2_spectras',
                on=False,
                style={'transform': 'scale(1.1)'}
            )
        ], style={'display': 'flex', 'alignItems': 'center', 'flex': '1', 'marginLeft': '10px'})
    ], style={'display': 'flex', 'marginBottom': '10px'}),

    # Adding GroupB_Detector3 under GroupB_Detector2
    html.Div([
        html.Div([
            html.H4('GroupA_Detector3', style={'fontSize': '20px', 'color': '#003f5c', "font-weight": "100"}),
            daq.BooleanSwitch(
                id='groupA_dect3_spectras',
                on=False,
                style={'transform': 'scale(1.1)'}
            )
        ], style={'display': 'flex', 'alignItems': 'center', 'flex': '1', 'marginRight': '10px'}),

        html.Div([
            html.H4('GroupB_Detector3', style={'fontSize': '20px', 'color': '#003f5c', "font-weight": "100"}),
            daq.BooleanSwitch(
                id='groupB_dect3_spectras',
                on=False,
                style={'transform': 'scale(1.1)'}
            )
        ], style={'display': 'flex', 'alignItems': 'center', 'flex': '1', 'marginLeft': '10px'})
    ], style={'display': 'flex', 'marginBottom': '10px'}),

    # Adding GroupB_Detector3 under GroupB_Detector2
    html.Div([
        html.Div([
            html.H4('Select All', style={'fontSize': '20px', 'color': '#003f5c', "font-weight": "100"}),
            daq.BooleanSwitch(
                id='select_all_switch',
                on=False,
                style={'transform': 'scale(1.1)'}
            )
        ], style={'display': 'flex', 'alignItems': 'center', 'flex': '1', 'marginRight': '10px'}),

        html.Div([
            html.H4('Plot Sensor data', style={'fontSize': '20px', 'color': '#003f5c', "font-weight": "100"}),
            daq.BooleanSwitch(
                id='plot_sensor_data',
                on=False,
                style={'transform': 'scale(1.1)'}
            )
        ], style={'display': 'flex', 'alignItems': 'center', 'flex': '1', 'marginLeft': '10px'})
    ], style={'display': 'flex', 'marginBottom': '10px'}),
                            ]),
                            dbc.Button('View Intensity Over Time ', id='view-graph-btn', color='primary', style={
                                'padding': '15px', 'width': '100%', 'margin': '15px 0', 'fontSize': '22px'}),
                            html.Div(id='select-intensities', children='Select one or multiple groups', style={
                                'fontFamily': 'Courier New',
                                'fontSize': '20px',
                                'textAlign': 'center',
                                'marginTop': '15px',
                                'color': '#2B2D42'
                            }),
                            html.Br(),
html.Div(children=[
    html.H3('Raw Data Quality Check', style={
        'background': '#003f5c',
        'padding': '15px',
        'textAlign': 'center',
        'color': 'white',
        'fontWeight': 'bold',
        'fontSize': '48px',
    }),
    # Alert and button styles updated for clearer and larger font
    dbc.Alert(
        html.Div([
            html.H4('Signal Noise Ratio', style={'color': '#003f5c', 'marginLeft': '40px', 'textAlign': 'left', 'fontSize': '28px', 'fontWeight': 'lighter'}),
            html.Button('×', id='snr-close-btn', n_clicks=0, style={'background': 'none', 'border': 'none', 'color': 'black', 'fontSize': '28px', 'cursor': 'pointer', 'float': 'right', 'color': '#ed6a28'})
        ]),
        id='snr-alert',  # Unique ID
        is_open=True,
        dismissable=True,
        style={'marginTop': '15px', 'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
    ),
    dbc.Alert(
        html.Div([
            html.H4('Average Signal Noise Ratio', style={'color': '#003f5c', 'marginLeft': '40px', 'textAlign': 'left', 'fontSize': '28px', 'fontWeight': 'lighter'}),
            html.Button('×', id='avg-snr-close-btn', n_clicks=0, style={'background': 'none', 'border': 'none', 'color': 'black', 'fontSize': '28px', 'cursor': 'pointer', 'float': 'right', 'color': '#ed6a28'})
        ]),
        id='avg-snr-alert',  # Unique ID
        is_open=True,
        dismissable=True,
        style={'marginTop': '15px', 'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
    ),
    dbc.Alert(
        html.Div([
            html.H4('Noise Equivalent Power', style={'color': '#003f5c', 'marginLeft': '40px', 'textAlign': 'left', 'fontSize': '28px', 'fontWeight': 'lighter'}),
            html.Button('×', id='nep-close-btn', n_clicks=0, style={'background': 'none', 'border': 'none', 'color': 'black', 'fontSize': '28px', 'cursor': 'pointer', 'float': 'right', 'color': '#ed6a28'})
        ]),
        id='nep-alert',  # Unique ID
        is_open=True,
        dismissable=True,
        style={'marginTop': '15px', 'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
    ),
    dbc.Alert(
        html.Div([
            html.H4('Scatter Plot', style={'color': '#003f5c', 'marginLeft': '40px', 'textAlign': 'left', 'fontSize': '28px', 'fontWeight': 'lighter'}),
            html.Button('×', id='scatter-plot-btn', n_clicks=0, style={'background': 'none', 'border': 'none', 'color': 'black', 'fontSize': '28px', 'cursor': 'pointer', 'float': 'right', 'color': '#ed6a28'})
        ]),
        id='scatter-plot-alert',  # Unique ID
        is_open=True,
        dismissable=True,
        style={'marginTop': '15px', 'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
    ),
    dbc.Alert(
        html.Div([
            html.H4('Distance from Dark', style={'color': '#003f5c', 'marginLeft': '40px', 'textAlign': 'left', 'fontSize': '28px', 'fontWeight': 'lighter'}),
            html.Button('×', id='distance-from-dark-btn', n_clicks=0, style={'background': 'none', 'border': 'none', 'color': 'black', 'fontSize': '28px', 'cursor': 'pointer', 'float': 'right', 'color': '#ed6a28'})
        ]),
        id='distance-from-dark-alert',  # Unique ID
        is_open=True,
        dismissable=True,
        style={'marginTop': '15px', 'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
    ),
    dbc.Alert(
        html.Div([
            html.H4('Saturation Percentage', style={'color': '#003f5c', 'marginLeft': '40px', 'textAlign': 'left', 'fontSize': '28px', 'fontWeight': 'lighter'}),
            html.Button('×', id='saturation-percentage-btn', n_clicks=0, style={'background': 'none', 'border': 'none', 'color': 'black', 'fontSize': '28px', 'cursor': 'pointer', 'float': 'right', 'color': '#ed6a28'})
        ]),
        id='saturation-percentage-alert',  # Unique ID
        is_open=True,
        dismissable=True,
        style={'marginTop': '15px', 'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
    ),
    html.Br(),
    html.Div([
                                html.H4('Select one:', style={
                                    'textAlign': 'left',
                                    'fontSize': '30px',
                                    'marginBottom': '15px',
                                    'color': '#003f5c',
                                    "font-weight": "100"
                                }),
                                dcc.Dropdown(
                                    id='data_quality-check-dropdown',
                                    options=[{'label': option, 'value': option} for option in [
                                        'LED_A_782_DET1', 'LED_A_782_DET2', 'LED_A_782_DET3',
                                        'LED_A_801_DET1', 'LED_A_801_DET2', 'LED_A_801_DET3',
                                        'LED_A_808_DET1', 'LED_A_808_DET2', 'LED_A_808_DET3',
                                        'LED_A_828_DET1', 'LED_A_828_DET2', 'LED_A_828_DET3',
                                        'LED_A_848_DET1', 'LED_A_848_DET2', 'LED_A_848_DET3',
                                        'LED_A_887_DET1', 'LED_A_887_DET2', 'LED_A_887_DET3',
                                        'LED_A_DARK_DET1', 'LED_A_DARK_DET2', 'LED_A_DARK_DET3',
                                        'LED_B_782_DET1', 'LED_B_782_DET2', 'LED_B_782_DET3',
                                        'LED_B_801_DET1', 'LED_B_801_DET2', 'LED_B_801_DET3',
                                        'LED_B_808_DET1', 'LED_B_808_DET2', 'LED_B_808_DET3',
                                        'LED_B_828_DET1', 'LED_B_828_DET2', 'LED_B_828_DET3',
                                        'LED_B_848_DET1', 'LED_B_848_DET2', 'LED_B_848_DET3',
                                        'LED_B_887_DET1', 'LED_B_887_DET2', 'LED_B_887_DET3',
                                        'LED_B_DARK_DET1', 'LED_B_DARK_DET2', 'LED_B_DARK_DET3'
                                    ]],
                                    multi=False,
                                    value=[],
                                    style={'borderColor': '#003f5c', 'fontSize': '24px'}
                                )
                            ]),
    dbc.Button('Check Raw Data Quality', id='check-data-quality-btn', color='primary', style={
        'padding': '15px', 'width': '100%', 'margin': '15px 0', 'fontSize': '22px'}),
    html.Div(id='check-raw-data-quality-desc', children='Check data quality', style={
        'fontFamily': 'Courier New',
        'fontSize': '20px',
        'textAlign': 'center',
        'marginTop': '15px',
        'color': '#2B2D42'
    })
]),
]),
]),
]),
#============================Movement Analsysis=====================================================================================================================
dcc.Tab(label='Movement Analysis', children=[
    html.Div([
        # Title Header
        html.H3(
            'View Intensities with Sensor Data',
            style={
                'background': '#003f5c',
                'padding': '12px 16px',
                'textAlign': 'center',
                'color': '#ECF0F1',
                'fontWeight': 'bold',
                'fontSize': '36px',
                'borderRadius': '8px',
                'marginBottom': '16px'
            }
        ),

        # 1. Plot Button
        dbc.Button(
            'Plot Intensity with Sensor Data',
            id='plot-intensity-sensor-btn',
            color='primary',
            style={
                'padding': '10px',
                'fontSize': '20px',
                'width': '100%',
                'marginBottom': '24px'
            }
        ),

        # 2. Threshold display
        # ================= LAYOUT =================
        html.Label(
        'Movement Threshold (Magnitude)',
        style={
            'fontSize': '40px',
            'fontWeight': '600',
            'color': '#333',
            'marginBottom': '6px',
            'display': 'block'
        }
        ),
        html.Div(
        id='movement-threshold-display',
        style={
            'fontSize': '32px',
            'fontWeight': '500',
            'color': '#555',
            'marginBottom': '20px'
        }
        ),
        html.Br(),

        # 3. Movement Metrics Section Header & Button
        html.H4(
            "Movement Metrics",
            style={
                'fontSize': '28px',
                'fontWeight': '700',
                'color': '#003f5c',
                'textAlign': 'center',
                'marginTop': '30px',
                'marginBottom': '16px'
            }
        ),
        # 4. Movement Metrics Cards as Alerts
        html.Div([
            dbc.Alert(
                [
                    html.Div([
                        html.H4(
                            'Total Duration',
                            style={
                                'color': '#003f5c',
                                'fontSize': '24px',
                                'fontWeight': '500',
                                'marginBottom': '4px'
                            }
                        ),
                        html.H3(
                            id='total-duration-card',
                             
                            style={
                                'fontWeight': '700',
                                'fontSize': '28px',
                                'marginBottom': '0'
                            }
                        )
                    ], style={'display': 'inline-block'}),
                    html.Button(
                        '×',
                        id='total-duration-btn',
                        n_clicks=0,
                        style={
                            'background': 'none',
                            'border': 'none',
                            'color': '#ed6a28',
                            'fontSize': '24px',
                            'float': 'right',
                            'lineHeight': '1',
                            'cursor': 'pointer',
                            'padding': '0 6px'
                        }
                    )
                ],
                id='total-duration-alert',
                is_open=True,
                dismissable=True,
                style={'padding': '10px 20px', 'marginTop': '12px'}
            ),
            dbc.Alert(
                [
                    html.Div([
                        html.H4(
                            'Movement Duration',
                            style={
                                'color': '#003f5c',
                                'fontSize': '24px',
                                'fontWeight': '500',
                                'marginBottom': '4px'
                            }
                        ),
                        html.H3(
                            id='movement-duration-card',
                             
                            style={
                                'fontWeight': '700',
                                'fontSize': '28px',
                                'marginBottom': '0'
                            }
                        )
                    ], style={'display': 'inline-block'}),
                    html.Button(
                        '×',
                        id='movement-duration-btn',
                        n_clicks=0,
                        style={
                            'background': 'none',
                            'border': 'none',
                            'color': '#ed6a28',
                            'fontSize': '24px',
                            'float': 'right',
                            'lineHeight': '1',
                            'cursor': 'pointer',
                            'padding': '0 6px'
                        }
                    )
                ],
                id='movement-duration-alert',
                is_open=True,
                dismissable=True,
                style={'padding': '10px 20px', 'marginTop': '12px'}
            ),
            dbc.Alert(
                [
                    html.Div([
                        html.H4(
                            'Movement %',
                            style={
                                'color': '#003f5c',
                                'fontSize': '24px',
                                'fontWeight': '500',
                                'marginBottom': '4px'
                            }
                        ),
                        html.H3(
                            id='movement-percentage-card',
                             
                            style={
                                'fontWeight': '700',
                                'fontSize': '28px',
                                'marginBottom': '0'
                            }
                        )
                    ], style={'display': 'inline-block'}),
                    html.Button(
                        '×',
                        id='movement-percentage-btn',
                        n_clicks=0,
                        style={
                            'background': 'none',
                            'border': 'none',
                            'color': '#ed6a28',
                            'fontSize': '24px',
                            'float': 'right',
                            'lineHeight': '1',
                            'cursor': 'pointer',
                            'padding': '0 6px'
                        }
                    )
                ],
                id='movement-percentage-alert',
                is_open=True,
                dismissable=True,
                style={'padding': '10px 20px', 'marginTop': '12px'}
            ),

            dbc.Alert(
                [
                    html.Div([
                        html.H4(
                            'Peak Acceleration',
                            style={
                                'color': '#003f5c',
                                'fontSize': '24px',
                                'fontWeight': '500',
                                'marginBottom': '4px'
                            }
                        ),
                        html.H3(
                            id='peak-acceleration-card',
                             
                            style={
                                'fontWeight': '700',
                                'fontSize': '28px',
                                'marginBottom': '0'
                            }
                        )
                    ], style={'display': 'inline-block'}),
                    html.Button(
                        '×',
                        id='peak-acceleration-btn',
                        n_clicks=0,
                        style={
                            'background': 'none',
                            'border': 'none',
                            'color': '#ed6a28',
                            'fontSize': '24px',
                            'float': 'right',
                            'lineHeight': '1',
                            'cursor': 'pointer',
                            'padding': '0 6px'
                        }
                    )
                ],
                id='peak-acceleration-alert',
                is_open=True,
                dismissable=True,
                style={'padding': '10px 20px', 'marginTop': '12px'}
            ),
            dbc.Alert(
                [
                    html.Div([
                        html.H4(
                            'Peak Gyroscope',
                            style={
                                'color': '#003f5c',
                                'fontSize': '24px',
                                'fontWeight': '500',
                                'marginBottom': '4px'
                            }
                        ),
                        html.H3(
                            id='peak-gyro-card',
                             
                            style={
                                'fontWeight': '700',
                                'fontSize': '28px',
                                'marginBottom': '0'
                            }
                        )
                    ], style={'display': 'inline-block'}),
                    html.Button(
                        '×',
                        id='peak-gyro-btn',
                        n_clicks=0,
                        style={
                            'background': 'none',
                            'border': 'none',
                            'color': '#ed6a28',
                            'fontSize': '24px',
                            'float': 'right',
                            'lineHeight': '1',
                            'cursor': 'pointer',
                            'padding': '0 6px'
                        }
                    )
                ],
                id='peak-gyro-alert',
                is_open=True,
                dismissable=True,
                style={'padding': '10px 20px', 'marginTop': '12px'}
            ),
            dbc.Alert(
                [
                    html.Div([
                        html.H4(
                            'Movement Episodes',
                            style={
                                'color': '#003f5c',
                                'fontSize': '24px',
                                'fontWeight': '500',
                                'marginBottom': '4px'
                            }
                        ),
                        html.H3(
                            id='movement-episodes-card',
                             
                            style={
                                'fontWeight': '700',
                                'fontSize': '28px',
                                'marginBottom': '0'
                            }
                        )
                    ], style={'display': 'inline-block'}),
                    html.Button(
                        '×',
                        id='movement-episodes-btn',
                        n_clicks=0,
                        style={
                            'background': 'none',
                            'border': 'none',
                            'color': '#ed6a28',
                            'fontSize': '24px',
                            'float': 'right',
                            'lineHeight': '1',
                            'cursor': 'pointer',
                            'padding': '0 6px'
                        }
                    )
                ],
                id='movement-episodes-alert',
                is_open=True,
                dismissable=True,
                style={'padding': '10px 20px', 'marginTop': '12px'}
            ),
            dbc.Button(
            "View Movement Metrics",
            id='view-metrics-btn',
            color='info',
            style={
                'padding': '10px',
                'fontSize': '18px',
                'width': '100%',
                'marginBottom': '24px'
            }
        ),
        ]),

        # 5. Artifact Removal Section
        html.H4(
            "Artifact Removal",
            style={
                'fontSize': '28px',
                'fontWeight': '700',
                'color': '#003f5c',
                'textAlign': 'center',
                'marginTop': '36px',
                'marginBottom': '16px'
            }
        ),
        dbc.Button(
            "Apply Movement Artifact Removal",
            id='artifact-removal-btn',
            color='danger',
            style={
                'padding': '10px',
                'fontSize': '20px',
                'width': '100%',
                'marginBottom': '24px'
            }
        ),
    ], style={'padding': '24px'})
]),

#=========================================================================================================================================================================================================================================================================
                # Data Clean Tab
                dcc.Tab(label='Data Clean', children=[
                    html.Div([
                        html.H3('Data Cleaning', style={
                            'background': '#003f5c',
                            'padding': '12px',
                            'textAlign': 'center',
                            'color': '#ECF0F1',
                            'fontWeight': 'bold',
                            'fontSize': '38px',
                            'borderRadius': '8px',
                        }),
                        html.Br(),
                        html.Div(
                                            style={
                                                'background': '#ffffff',
                                                'padding': '20px',
                                                'boxShadow': '0 4px 10px rgba(0, 0, 0, 0.5)',
                                                'marginBottom': '20px'
                                            },
                                            children=[
                                                html.Br(),
                                                # Subtract Dark Section
                html.Br(),
html.Div('Subtract Dark', style={
    'background': '#003f5c',
    'padding': '10px',
    'textAlign': 'center',
    'color': 'white',
    'fontWeight': 'bold',
    'fontSize': '30px'
}),
html.Br(),
html.Div(
    children=[
        dcc.Checklist(
            id='preprocessing-options-subtract-dark',
            options=[{'label': 'Subtract Dark', 'value': 'subtract-dark'}],
            value=['subtract-dark'],
            style={'textAlign': 'Center', 'fontSize': '28px', 'marginBottom': '10px', 'color': '#003f5c'},
            inputStyle={'transform': 'scale(1.5)', 'marginRight': '10px'}
        ),
        html.Div('Subtract Noise', style={'fontFamily': 'Courier New', 'fontSize': '16px', 'textAlign': 'center', 'color': '#2B2D42'}),
        html.Br()
    ]
),
html.Br(),
                html.Div('High-Pass Filtering', style={
    'background': '#003f5c',
    'padding': '10px',
    'textAlign': 'center',
    'color': 'white',
    'fontWeight': 'bold',
    'fontSize': '30px'
}),
html.Br(),
html.Div(
    children=[
        dcc.Checklist(
            id='preprocessing-options-highpass',
            options=[
                {'label': 'High-Pass Filtering', 'value': 'highpass'},
            ],
            className='alignment-settings-section',
            style={
                'textAlign': 'Center',
                'fontSize': '28px',
                'marginBottom': '10px',
                'color': '#003f5c',
                "font-weight": "100",
                'alignItems': 'center'
            },
            inputStyle={
                'transform': 'scale(1.5)',  # Adjust this value to make the checkbox larger or smaller
                'marginRight': '10px',  # Optional: add space between the checkbox and the label
            }
        ),
        html.Br(),
        # Cutoff Frequency input
        html.Div(
            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
            children=[
                html.Div(
                    className='app-controls-name',
                    children='Cutoff Frequency (Hz)',
                    style={
                        'textAlign': 'left',
                        'fontSize': '26px',
                        'marginBottom': '10px',
                        'color': '#003f5c',
                        "font-weight": "100",
                        'marginLeft': '30px'
                    }
                ),
                dcc.Input(
                    id='highpass-cutoff-input',
                    type='number',
                    min=0.001,
                    max=10000,
                    step=0.001,
                    value=0.001,
                    style={
                        'width': '30%',
                        'padding': '5px',
                        'height': '24px',  # Adjusted height
                        'textAlign': 'center',
                        'borderColor': '#003f5c',
                        'marginRight': '30px',
                        'fontSize': '24px'
                    }
                )
            ]
        ),
        html.Div(
            children='Set Cutoff Frequency for High-Pass Filtering',
            style={
                'fontFamily': 'Courier New',
                'fontSize': '16px',
                'textAlign': 'center',
                'marginTop': '10px',
                'color': '#003f5c',
            }
        ),
        html.Br(),
        # Filter Order input
        html.Div(
            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
            children=[
                html.Div(
                    className='app-controls-name',
                    children='Filter Order',
                    style={
                        'textAlign': 'left',
                        'fontSize': '26px',
                        'marginBottom': '10px',
                        'color': '#003f5c',
                        "font-weight": "100",
                        'marginLeft': '30px'
                    }
                ),
                dcc.Input(
                    id='highpass-order-input',
                    type='number',
                    min=1,
                    max=10000,
                    step=1,
                    value=1,
                    style={
                        'width': '30%',
                        'padding': '5px',
                        'height': '24px',  # Adjusted height
                        'textAlign': 'center',
                        'borderColor': '#003f5c',
                        'marginRight': '30px',
                        'fontSize': '24px'
                    }
                )
            ]
        ),
        html.Div(
            children='Set Filter Order for High-Pass Filtering',
            style={
                'fontFamily': 'Courier New',
                'fontSize': '16px',
                'textAlign': 'center',
                'marginTop': '10px',
                'color': '#003f5c',
            }
        ),
        html.Br(),
        html.Br(),
        # Sampling Rate Input (Optional)
        html.Div(
            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
            children=[
                html.Div(
                    className='app-controls-name',
                    children='Sampling Rate (Hz)',
                    style={
                        'textAlign': 'left',
                        'fontSize': '26px',
                        'marginBottom': '10px',
                        'color': '#003f5c',
                        "font-weight": "100",
                        'marginLeft': '30px'
                    }
                ),
                dcc.Input(
                    id='highpass-sampling-rate-input',
                    type='number',
                    min=1,
                    max=10000,
                    step=1,
                    value=1,
                    style={
                        'width': '30%',
                        'padding': '5px',
                        'height': '24px',  # Adjusted height
                        'textAlign': 'center',
                        'borderColor': '#003f5c',
                        'marginRight': '30px',
                        'fontSize': '24px'
                    }
                )
            ]
        ),
        html.Div(
            children='Set Sampling Rate for High-Pass Filtering',
            style={
                'fontFamily': 'Courier New',
                'fontSize': '16px',
                'textAlign': 'center',
                'marginTop': '10px',
                'color': '#003f5c',
            }
        ),
        html.Br(),
        html.Br(),
    ],
),
html.Br(),
html.Br(),
html.Div('Low-Pass Filtering', style={
    'background': '#003f5c',
    'padding': '10px',
    'textAlign': 'center',
    'color': 'white',
    'fontWeight': 'bold',
    'fontSize': '30px'
}),
html.Br(),
html.Div(
    children=[
        dcc.Checklist(
            id='preprocessing-options-lowpass',
            options=[
                {'label': 'Low-Pass Filtering', 'value': 'lowpass'},
            ],
            className='alignment-settings-section',
            style={
                'textAlign': 'Center',
                'fontSize': '28px',
                'marginBottom': '10px',
                'color': '#003f5c',
                "font-weight": "100",
                'alignItems': 'center'
            },
            inputStyle={
                'transform': 'scale(1.5)',  # Adjust this value to make the checkbox larger or smaller
                'marginRight': '10px',  # Optional: add space between the checkbox and the label
            }
        ),
        html.Br(),
        # Cutoff Frequency input
        html.Div(
            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
            children=[
                html.Div(
                    className='app-controls-name',
                    children='Cutoff Frequency (Hz)',
                    style={
                        'textAlign': 'left',
                        'fontSize': '26px',
                        'marginBottom': '10px',
                        'color': '#003f5c',
                        "font-weight": "100",
                        'marginLeft': '30px'
                    }
                ),
                dcc.Input(
                    id='lowpass-cutoff-input',
                    type='number',
                    min=0.001,
                    max=10000,
                    step=0.001,
                    value=0.001,
                    style={
                        'width': '30%',
                        'padding': '5px',
                        'height': '24px',  # Adjusted height
                        'textAlign': 'center',
                        'borderColor': '#003f5c',
                        'marginRight': '30px',
                        'fontSize': '24px'
                    }
                )
            ]
        ),
        html.Div(
            children='Set Cutoff Frequency for Low-Pass Filtering',
            style={
                'fontFamily': 'Courier New',
                'fontSize': '16px',
                'textAlign': 'center',
                'marginTop': '10px',
                'color': '#003f5c',
            }
        ),
        html.Br(),
        # Filter Order input
        html.Div(
            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
            children=[
                html.Div(
                    className='app-controls-name',
                    children='Filter Order',
                    style={
                        'textAlign': 'left',
                        'fontSize': '26px',
                        'marginBottom': '10px',
                        'color': '#003f5c',
                        "font-weight": "100",
                        'marginLeft': '30px'
                    }
                ),
                dcc.Input(
                    id='lowpass-order-input',
                    type='number',
                    min=1,
                    max=10000,
                    step=1,
                    value=1,
                    style={
                        'width': '30%',
                        'padding': '5px',
                        'height': '24px',  # Adjusted height
                        'textAlign': 'center',
                        'borderColor': '#003f5c',
                        'marginRight': '30px',
                        'fontSize': '24px'
                    }
                )
            ]
        ),
        html.Div(
            children='Set Filter Order for Low-Pass Filtering',
            style={
                'fontFamily': 'Courier New',
                'fontSize': '16px',
                'textAlign': 'center',
                'marginTop': '10px',
                'color': '#003f5c',
            }
        ),
        html.Br(),
        html.Br(),
        # Sampling Rate Input (Optional)
        html.Div(
            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
            children=[
                html.Div(
                    className='app-controls-name',
                    children='Sampling Rate (Hz)',
                    style={
                        'textAlign': 'left',
                        'fontSize': '26px',
                        'marginBottom': '10px',
                        'color': '#003f5c',
                        "font-weight": "100",
                        'marginLeft': '30px'
                    }
                ),
                dcc.Input(
                    id='lowpass-sampling-rate-input',
                    type='number',
                    min=1,
                    max=10000,
                    step=1,
                    value=1,
                    style={
                        'width': '30%',
                        'padding': '5px',
                        'height': '24px',  # Adjusted height
                        'textAlign': 'center',
                        'borderColor': '#003f5c',
                        'marginRight': '30px',
                        'fontSize': '24px'
                    }
                )
            ]
        ),
        html.Div(
            children='Set Sampling Rate for Low-Pass Filtering',
            style={
                'fontFamily': 'Courier New',
                'fontSize': '16px',
                'textAlign': 'center',
                'marginTop': '10px',
                'color':  '#003f5c',
            }
        ),
        html.Br(),
        html.Br(),
    ],
),
html.Br(),
html.Br(),
html.Div('Band-Pass Filtering', style={
    'background': '#003f5c',
    'padding': '10px',
    'textAlign': 'center',
    'color': 'white',
    'fontWeight': 'bold',
    'fontSize': '30px'
}),
html.Br(),
html.Div(
    children=[
        dcc.Checklist(
            id='preprocessing-options-bandpass',
            options=[
                {'label': 'Band-Pass Filtering', 'value': 'bandpass'},
            ],
            className='alignment-settings-section',
            style={
                'textAlign': 'Center',
                'fontSize': '28px',
                'marginBottom': '10px',
                'color':  '#003f5c',
                "font-weight": "100",
                'alignItems': 'center'
            },
            inputStyle={
                'transform': 'scale(1.5)',  # Adjust this value to make the checkbox larger or smaller
                'marginRight': '10px',  # Optional: add space between the checkbox and the label
            }
        ),
        html.Br(),
        # Lower Cutoff Frequency input
        html.Div(
            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
            children=[
                html.Div(
                    className='app-controls-name',
                    children='Lower Cutoff Frequency (Hz)',
                    style={
                        'textAlign': 'left',
                        'fontSize': '26px',
                        'marginBottom': '10px',
                        'color':  '#003f5c',
                        "font-weight": "100",
                        'marginLeft': '30px'
                    }
                ),
                dcc.Input(
                    id='bandpass-lower-cutoff-input',
                    type='number',
                    min=0.001,
                    max=10000,
                    step=0.001,
                    value=0.001,
                    style={
                        'width': '30%',
                        'padding': '5px',
                        'height': '24px',  # Adjusted height
                        'textAlign': 'center',
                        'borderColor': '#003f5c',
                        'marginRight': '30px',
                        'fontSize': '24px'
                    }
                )
            ]
        ),
        html.Div(
            children='Set Lower Cutoff Frequency for Band-Pass Filtering',
            style={
                'fontFamily': 'Courier New',
                'fontSize': '16px',
                'textAlign': 'center',
                'marginTop': '10px',
                'color': '#003f5c',
            }
        ),
        html.Br(),
        # Upper Cutoff Frequency input
        html.Div(
            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
            children=[
                html.Div(
                    className='app-controls-name',
                    children='Upper Cutoff Frequency (Hz)',
                    style={
                        'textAlign': 'left',
                        'fontSize': '26px',
                        'marginBottom': '10px',
                        'color': '#003f5c',
                        "font-weight": "100",
                        'marginLeft': '30px'
                    }
                ),
                dcc.Input(
                    id='bandpass-upper-cutoff-input',
                    type='number',
                    min=0.002,
                    max=10001,
                    step=0.002,
                    value=0.002,
                    style={
                        'width': '30%',
                        'padding': '5px',
                        'height': '24px',  # Adjusted height
                        'textAlign': 'center',
                        'borderColor': '#003f5c',
                        'marginRight': '30px',
                        'fontSize': '24px'
                    }
                )
            ]
        ),
        html.Div(
            children='Set Upper Cutoff Frequency for Band-Pass Filtering',
            style={
                'fontFamily': 'Courier New',
                'fontSize': '16px',
                'textAlign': 'center',
                'marginTop': '10px',
                'color': '#003f5c',
            }
        ),
        html.Br(),
        html.Br(),
        # Filter Order input
        html.Div(
            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
            children=[
                html.Div(
                    className='app-controls-name',
                    children='Filter Order',
                    style={
                        'textAlign': 'left',
                        'fontSize': '26px',
                        'marginBottom': '10px',
                        'color': '#003f5c',
                        "font-weight": "100",
                        'marginLeft': '30px'
                    }
                ),
                dcc.Input(
                    id='bandpass-order-input',
                    type='number',
                    min=1,
                    max=10000,
                    step=1,
                    value=1,
                    style={
                        'width': '30%',
                        'padding': '5px',
                        'height': '24px',  # Adjusted height
                        'textAlign': 'center',
                        'borderColor': '#003f5c',
                        'marginRight': '30px',
                        'fontSize': '24px'
                    }
                )
            ]
        ),
        html.Div(
            children='Set Filter Order for Band-Pass Filtering',
            style={
                'fontFamily': 'Courier New',
                'fontSize': '16px',
                'textAlign': 'center',
                'marginTop': '10px',
                'color': '#2B2D42'
            }
        ),
        html.Br(),
        html.Br(),
        # Sampling Rate Input (Optional)
        html.Div(
            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
            children=[
                html.Div(
                    className='app-controls-name',
                    children='Sampling Rate (Hz)',
                    style={
                        'textAlign': 'left',
                        'fontSize': '26px',
                        'marginBottom': '10px',
                        'color': '#003f5c',
                        "font-weight": "100",
                        'marginLeft': '30px'
                    }
                ),
                dcc.Input(
                    id='bandpass-sampling-rate-input',
                    type='number',
                    min=1,
                    max=10000,
                    step=1,
                    value=1,
                    style={
                        'width': '30%',
                        'padding': '5px',
                        'height': '24px',  # Adjusted height
                        'textAlign': 'center',
                        'borderColor': '#003f5c',
                        'marginRight': '30px',
                        'fontSize': '24px'
                    }
                )
            ]
        ),
        html.Div(
            children='Set Sampling Rate for Band-Pass Filtering',
            style={
                'fontFamily': 'Courier New',
                'fontSize': '16px',
                'textAlign': 'center',
                'marginTop': '10px',
                'color': '#2B2D42'
            }
        ),
        html.Br(),
        html.Br(),
    ],
),
html.Br(),
html.Br(),
html.Br(),
                       
                                                html.Br(),
                                                html.Div('Median Filtering', style={
                                                    'background': '#003f5c',
                                                    'padding': '10px',
                                                    'textAlign': 'center',
                                                    'color': 'white',
                                                    'fontWeight': 'bold',
                                                    'fontSize': '30px'
                                                }),
                                                html.Br(),
                                                html.Div(
                                                    children=[
                                                        dcc.Checklist(
                                                            id='preprocessing-options-median',
                                                            options=[
                                                                {'label': 'Median Filtering', 'value': 'median'},
                                                            ],
                                                            className='alignment-settings-section',
                                                            style={
                                                                'textAlign': 'Center',
                                                                'fontSize': '28px',
                                                                'marginBottom': '10px',
                                                                'color': '#003f5c',
                                                                "font-weight": "100",
                                                                'alignItems': 'center'
                                                            },
                                                            inputStyle={
                                                                'transform': 'scale(1.5)',  # Adjust this value to make the checkbox larger or smaller
                                                                'marginRight': '10px',  # Optional: add space between the checkbox and the label
                                                            }
                                                        ),
                                                        html.Br(),
                                                        html.Div(
                                                            style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
                                                            children=[
                                                                html.Div(
                                                                    className='app-controls-name',
                                                                    children='Filter Size',
                                                                    style={
                                                                        'textAlign': 'left',
                                                                        'fontSize': '26px',
                                                                        'marginBottom': '10px',
                                                                        'color': '#003f5c',
                                                                        "font-weight": "100",
                                                                        'marginLeft': '30px'
                                                                    }
                                                                ),
                                                                dcc.Input(
                                                    id='median-filter-size-input',
                                                    type='number',
                                                    min=1,
                                                    max=100,
                                                    step=1,
                                                    value=1,
                                                    style={
                                                        'width': '30%',
                                                        'padding': '5px',
                                                        'height': '24px',  # Increased height to fit the larger font
                                                        'textAlign': 'center',
                                                        'borderColor': '#003f5c',
                                                        'marginRight': '30px',
                                                        'fontSize': '24px'  # Increased font size for the number
                                                        }
                                                        )]
                                                        ),
                                                        html.Div(
                                                            children='Set Filter Size for Median Filtering',
                                                            style={
                                                                'fontFamily': 'Courier New',
                                                                'fontSize': '16px',
                                                                'textAlign': 'center',
                                                                'marginTop': '10px',
                                                                'color': '#2B2D42'
                                                            }
                                                        ),
                                                        html.Br(),
                                                        html.Br(),
                                                        html.Br(),
                                                    ],
                                                ),
                                                html.Div(
                                                    style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
                                                    children=[
                                                        html.Button(
                                                            'Apply',
                                                            id='apply-button',
                                                            n_clicks=0,
                                                            style={'padding': '10px', 'width': '100%', 'margin': '10px 0', 'fontSize': '20px'}
                                                        ),
                                                    ]
                                                ),
                                                html.Div('Apply the selected techniques and parameters set', id='status-apply', style={
                                                'fontFamily': 'Courier New',
                                                'fontSize': '15px',
                                                'textAlign': 'center',
                                                'marginTop': '10px',
                                                'color': '#2B2D42'
                                            }),
                                            ]),
                                            html.Div(
                                                children=[
                                                    html.Div('View Changes', style={
                                                    'background': '#003f5c',
                                                    'padding': '10px',
                                                    'textAlign': 'center',
                                                    'color': 'white',
                                                    'fontWeight': 'bold',
                                                    'fontSize': '30px'
                                                }),
                                                html.Br(),
                                                    html.Br(),
                                            html.Div([
                                                html.H4('Select one or more Groups to view', style={
                                                    'textAlign': 'left',
                                                    'fontSize': '24px',
                                                    'marginBottom': '10px',
                                                    'color': '#003f5c',
                                                    "font-weight": "100"
                                                }),
                                                html.Div([
                                                    html.Div([
                                                        html.H4('GroupA_Detector1', style={'fontSize': '20px', 'flex': '1', 'color': '#003f5c', "font-weight": "100"}),
                                                        daq.BooleanSwitch(
                                                            id='groupA_dect1_data_clean',
                                                            on=False,
                                                            style={'transform': 'scale(1.1)'}
                                                        ),
                                                    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px', 'flex': '1'}),
                                                    html.Div([
                                                        html.H4('GroupA_Detector2', style={'fontSize': '20px', 'flex': '1', 'color': '#003f5c', "font-weight": "100"}),
                                                        daq.BooleanSwitch(
                                                            id='groupA_dect2_data_clean',
                                                            on=False,
                                                            style={'transform': 'scale(1.1)'}
                                                        ),
                                                    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px', 'flex': '1'}),
                                                    html.Div([
                                                        html.H4('GroupA_Detector3', style={'fontSize': '20px', 'flex': '1', 'color': '#003f5c', "font-weight": "100"}),
                                                        daq.BooleanSwitch(
                                                            id='groupA_dect3_data_clean',
                                                            on=False,
                                                            style={'transform': 'scale(1.1)'}
                                                        ),
                                                    ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px', 'flex': '1'})
                                                ], style={'display': 'flex'}),
                                            ]),
                                            html.Div([
                                                html.Div([
                                                    html.H4('GroupB_Detector1', style={'fontSize': '20px', 'flex': '1', 'color': '#003f5c', "font-weight": "100"}),
                                                    daq.BooleanSwitch(
                                                        id='groupB_dect1_data_clean',
                                                        on=False,
                                                        style={'transform': 'scale(1.1)'}
                                                    )
                                                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px', 'flex': '1'}),
                                                html.Div([
                                                    html.H4('GroupB_Detector2', style={'fontSize': '20px', 'flex': '1', 'color': '#003f5c', "font-weight": "100"}),
                                                    daq.BooleanSwitch(
                                                        id='groupB_dect2_data_clean',
                                                        on=False,
                                                        style={'transform': 'scale(1.1)'}
                                                    )
                                                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px', 'flex': '1'}),
                                                html.Div([
                                                    html.H4('GroupB_Detector3', style={'fontSize': '20px', 'flex': '1', 'color': '#003f5c', "font-weight": "100"}),
                                                    daq.BooleanSwitch(
                                                        id='groupB_dect3_data_clean',
                                                        on=False,
                                                        style={'transform': 'scale(1.1)'}
                                                    )
                                                ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px', 'flex': '1'})
                                            ], style={'display': 'flex'}),
                                                    html.Br(),
                                                    html.Div(
                                                        style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between'},
                                                        children=[
                                                            html.Div(
                                                                children='View spectra',
                                                                style={'textAlign': 'left', 'fontSize': '24px', 'marginBottom': '10px', 'color': '#003f5c', "font-weight": "100", 'marginLeft': '30px'}
                                                            ),
                                                            html.Button(
                                                                'View',
                                                                id='view-button',
                                                                style={'padding': '10px', 'width': '50%', 'margin': '10px 0', 'fontSize': '20px'},
                                                                n_clicks=0                                        
                                                            )
                                                        ],
                                                    ),
                                                   html.Div(
                                                        children='Select Show to view the spectra',
                                                        style={
                                                            'fontFamily': 'Courier New',
                                                            'fontSize': '15px',
                                                            'textAlign': 'center',
                                                            'marginTop': '10px',
                                                            'color': '#2B2D42'
                                                        },
                                                ),
                    ]),
                ]),
                ]),
                dcc.Tab(label='Data Analysis', children=[
                    html.Div([
                        html.H3('Data Analysis', style={
                            'background': '#003f5c',
                            'padding': '12px',
                            'textAlign': 'center',
                            'color': '#ECF0F1',
                            'fontWeight': 'bold',
                            'fontSize': '38px',
                            'borderRadius': '8px',
                        }),
                        html.Br(),
                                                dbc.Alert(
                                                    html.Div([
                                                        html.H4('Histogram',
                                                                style={'color': '#003f5c', 'marginLeft': '40px',
                                                                       'textAlign': 'left', 'fontSize': '24px',
                                                                       'fontWeight': 'lighter',
                                                                       'display': 'inline-block', 'width': '45%'}),
                                                        html.Button(
                                                            '×', id='close-histogram-alert', n_clicks=0,
                                                            style={
                                                                'background': 'none',
                                                                'border': 'none',
                                                                'color': 'black',
                                                                'fontSize': '28px',
                                                                'cursor': 'pointer',
                                                                'float': 'right',
                                                                'marginTop': '-10px',
                                                                'color': '#003f5c'
                                                            }
                                                        )
                                                    ]),
                                                    id='histogram-alert',
                                                    is_open=True,
                                                    dismissable=False,
                                                    style={'marginTop': '10px',
                                                           'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
                                                ),
                                                dbc.Alert(
                                                    html.Div([
                                                        html.H4('Standard Deviation',
                                                                style={'color': '#003f5c', 'marginLeft': '40px',
                                                                       'textAlign': 'left', 'fontSize': '24px',
                                                                       'fontWeight': 'lighter',
                                                                       'display': 'inline-block', 'width': '45%'}),
                                                        html.Button(
                                                            '×', id='close-standard-deviation-alert', n_clicks=0,
                                                            style={
                                                                'background': 'none',
                                                                'border': 'none',
                                                                'color': 'black',
                                                                'fontSize': '28px',
                                                                'cursor': 'pointer',
                                                                'float': 'right',
                                                                'marginTop': '-10px',
                                                                'color': '#003f5c'
                                                            }
                                                        )
                                                    ]),
                                                    id='standard-deviation-alert',
                                                    is_open=True,
                                                    dismissable=False,
                                                    style={'marginTop': '10px',
                                                           'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
                                                ),
                                                dbc.Alert(
                                                    html.Div([
                                                        html.H4('Mean', style={'color': '#003f5c', 'marginLeft': '40px',
                                                                               'textAlign': 'left', 'fontSize': '24px',
                                                                               'fontWeight': 'lighter',
                                                                               'display': 'inline-block',
                                                                               'width': '45%'}),
                                                        html.Button(
                                                            '×', id='close-mean-alert', n_clicks=0,
                                                            style={
                                                                'background': 'none',
                                                                'border': 'none',
                                                                'color': 'black',
                                                                'fontSize': '28px',
                                                                'cursor': 'pointer',
                                                                'float': 'right',
                                                                'marginTop': '-10px',
                                                                'color': '#003f5c'
                                                            }
                                                        )
                                                    ]),
                                                    id='mean-alert',
                                                    is_open=True,
                                                    dismissable=False,
                                                    style={'marginTop': '10px',
                                                           'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
                                                ),
                                                dbc.Alert(
                                                    html.Div([
                                                        html.H4('Maximum',
                                                                style={'color': '#003f5c', 'marginLeft': '40px',
                                                                       'textAlign': 'left', 'fontSize': '24px',
                                                                       'fontWeight': 'lighter',
                                                                       'display': 'inline-block', 'width': '45%'}),
                                                        html.Button(
                                                            '×', id='close-maximum-alert', n_clicks=0,
                                                            style={
                                                                'background': 'none',
                                                                'border': 'none',
                                                                'color': 'black',
                                                                'fontSize': '28px',
                                                                'cursor': 'pointer',
                                                                'float': 'right',
                                                                'marginTop': '-10px',
                                                                'color': '#003f5c'
                                                            }
                                                        )
                                                    ]),
                                                    id='maximum-alert',
                                                    is_open=True,
                                                    dismissable=False,
                                                    style={'marginTop': '10px',
                                                           'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
                                                ),
                                                dbc.Alert(
                                                    html.Div([
                                                        html.H4('Minimum',
                                                                style={'color': '#003f5c', 'marginLeft': '40px',
                                                                       'textAlign': 'left', 'fontSize': '24px',
                                                                       'fontWeight': 'lighter',
                                                                       'display': 'inline-block', 'width': '45%'}),
                                                        html.Button(
                                                            '×', id='close-minimum-alert', n_clicks=0,
                                                            style={
                                                                'background': 'none',
                                                                'border': 'none',
                                                                'color': 'black',
                                                                'fontSize': '28px',
                                                                'cursor': 'pointer',
                                                                'float': 'right',
                                                                'marginTop': '-10px',
                                                                'color': '#003f5c'
                                                            }
                                                        )
                                                    ]),
                                                    id='minimum-alert',
                                                    is_open=True,
                                                    dismissable=False,
                                                    style={'marginTop': '10px',
                                                           'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
                                                ),
                                                dbc.Alert(
                                                    html.Div([
                                                        html.H4('Largest Variations',
                                                                style={'color': '#003f5c', 'marginLeft': '40px',
                                                                       'textAlign': 'left', 'fontSize': '24px',
                                                                       'fontWeight': 'lighter',
                                                                       'display': 'inline-block', 'width': '45%'}),
                                                        html.Button(
                                                            '×', id='close-variations-alert', n_clicks=0,
                                                            style={
                                                                'background': 'none',
                                                                'border': 'none',
                                                                'color': 'black',
                                                                'fontSize': '28px',
                                                                'cursor': 'pointer',
                                                                'float': 'right',
                                                                'marginTop': '-10px',
                                                                'color': '#003f5c'
                                                            }
                                                        )
                                                    ]),
                                                    id='variations-alert',
                                                    is_open=True,
                                                    dismissable=False,
                                                    style={'marginTop': '10px',
                                                           'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
                                                ),
                                                dbc.Alert(
                                                    html.Div([
                                                        html.H4('Scatter Effect',
                                                                style={'color': '#003f5c', 'marginLeft': '40px',
                                                                       'textAlign': 'left', 'fontSize': '24px',
                                                                       'fontWeight': 'lighter',
                                                                       'display': 'inline-block', 'width': '45%'}),
                                                        html.Button(
                                                            '×', id='close-scatter-effect-alert', n_clicks=0,
                                                            style={
                                                                'background': 'none',
                                                                'border': 'none',
                                                                'color': 'black',
                                                                'fontSize': '28px',
                                                                'cursor': 'pointer',
                                                                'float': 'right',
                                                                'marginTop': '-10px'
                                                            }
                                                        )
                                                    ]),
                                                    id='scatter-effect-alert',
                                                    is_open=True,
                                                    dismissable=False,
                                                    style={'marginTop': '10px',
                                                           'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
                                                ),
                                                dbc.Alert(
                                                    html.Div([
                                                        html.H4('3D Plot',
                                                                style={'color': '#003f5c', 'marginLeft': '40px',
                                                                       'textAlign': 'left', 'fontSize': '24px',
                                                                       'fontWeight': 'lighter',
                                                                       'display': 'inline-block', 'width': '45%'}),
                                                        html.Button(
                                                            '×', id='3d-plot-effect-alert', n_clicks=0,
                                                            style={
                                                                'background': 'none',
                                                                'border': 'none',
                                                                'color': 'black',
                                                                'fontSize': '28px',
                                                                'cursor': 'pointer',
                                                                'float': 'right',
                                                                'marginTop': '-10px',
                                                                'color': '#003f5c'
                                                            }
                                                        )
                                                    ]),
                                                    id='3d-effect-alert',
                                                    is_open=True,
                                                    dismissable=False,
                                                    style={'marginTop': '10px',
                                                           'boxShadow': '0 4px 6px rgba(0, 0, 0, 0.1)'}
                                                ),
                                                html.Br(),
                                                html.Br(),
                                                html.Div([
                                                    html.H4('Select intensity:', style={
                                                        'textAlign': 'left',
                                                        'fontSize': '28px',
                                                        'marginBottom': '10px',
                                                        'color': '#003f5c',
                                                        "font-weight": "100",
                                                        'opacity': 0.5,
                                                        # Make text
                                                        # semi-transparent to
                                                        # indicate it's not
                                                        # clickable
                                                    }),
                                                    dcc.Dropdown(
                                                        id='data-analysis-options-dropdown',
                                                        options=[{'label': option, 'value': option} for option in
                                                                 ['GroupA_Detector1', 'GroupA_Detector2',
                                                                  'GroupB_Detector1', 'GroupB_Detector2']],
                                                        multi=False,
                                                        value=[],
                                                        style={
                                                            'borderColor': 'transparent',  # Make the border transparent
                                                            'backgroundColor': 'transparent',
                                                            # Make background
                                                            # transparent
                                                            'fontSize': '24px',
                                                            'cursor': 'not-allowed',  # Set cursor to not-allowed
                                                            'opacity': 0.5
                                                            # Make dropdown
                                                            # semi-transparent
                                                            # to indicate it's
                                                            # not clickable
                                                        }
                                                    ),
                                                ]),
                                                html.Div(
                                                    style={
                                                        'display': 'flex',
                                                        'alignItems': 'center',
                                                        'justifyContent': 'space-between',
                                                        'opacity': 0.5,  # Make the button's div semi-transparent
                                                    },
                                                    children=[
                                                        html.Button(
                                                            'Perform Data Analysis',
                                                            id='data-analysis-button',
                                                            n_clicks=0,
                                                            style={
                                                                'padding': '10px',
                                                                'width': '100%',
                                                                'margin': '10px 0',
                                                                'fontSize': '20px',
                                                                'backgroundColor': 'transparent',
                                                                # Make button
                                                                # background
                                                                # transparent
                                                                'border': 'none',
                                                                # Remove border
                                                                # to make it
                                                                # look inactive
                                                                'cursor': 'not-allowed',  # Set cursor to not-allowed
                                                                'opacity': 0.5  # Make button semi-transparent
                                                            }
                                                        ),
                                                    ]
                                                ),
                    ]),
                ]),
                dcc.Tab(label='Concentrations', children=[
        html.Div([
            html.H3('Concentrations', style={
                'background': '#003f5c',
                'padding': '12px',
                'textAlign': 'center',
                'color': '#ECF0F1',
                'fontWeight': 'bold',
                'fontSize': '38px',
                'borderRadius': '8px',
            }),
            # Add the "Calculate Concentrations" button here
            html.Button('Calculate Concentrations', id='calculate-concentrations-btn', n_clicks=0, style={
                                'width': '95%', 'height': '70px', 'lineHeight': '70px',
                                'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
                                'textAlign': 'center', 'margin': '15px', 'fontSize': '24px'}),
            html.Br(),
            html.Button('Download Concentrations Excel File', id='download_concentrations_excel_btn',  n_clicks=0, style={
                                'width': '95%', 'height': '70px', 'lineHeight': '70px',
                                'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
                                'textAlign': 'center', 'margin': '15px', 'fontSize': '24px'}),
            html.Button('Download resampled concentrations', id='download_resampled_concentrations_btn',  n_clicks=0, style={
                                'width': '95%', 'height': '70px', 'lineHeight': '70px',
                                'borderWidth': '1px', 'borderStyle': 'dashed', 'borderRadius': '5px',
                                'textAlign': 'center', 'margin': '15px', 'fontSize': '24px'}),
            dcc.Download(id="download-conc-xlsx"),
            dcc.Download(id="download-resampled-conc-xlsx"), 
        html.Div(id='tabs-container'),
        ]),
    ]),
]),
        ], style={'width': '25%', 'padding': '15px', 'boxSizing': 'border-box'}),
        # Right side (3/4th width for Plot Section)
        html.Div([
            html.H3('Plot Section', style={
                'background': '#003f5c',
                'padding': '12px',
                'textAlign': 'center',
                'color': '#ECF0F1',
                'fontWeight': 'bold',
                'fontSize': '38px',
                'borderRadius': '8px',
            }),
            dcc.Tabs(id='tabs', children=[
                dcc.Tab(label='Intensity vs Time', children=[
                    html.Div(id='intensity-time-plot'),
                ]),
                dcc.Tab(label='Data Quality Check', children=[
                    html.Div(id='data-quality-plot'),
                ]),
                dcc.Tab(label='Movement Analysis', children=[
                    html.Div(id='movement-analysis-plot'),
                ]),
                dcc.Tab(label='Data Clean', children=[
                    html.Div(id='data-clean-plot'),
                ]),
                dcc.Tab(label='Concentrations', children=[
                    html.Div(id='concentrations-plot'),
                ]),
            ]),
        ], style={'width': '75%', 'padding': '10px', 'boxSizing': 'border-box', 'borderLeft': '2px solid #3498DB'})
    ], style={'display': 'flex', 'height': '100vh'}),
    dcc.Store(id='uploaded-data'),
    dcc.Store(id='resampled-data'),
    dcc.Store(id='resampling-method'),
    dcc.Store(id='quality-metrics'),
    dcc.Store(id='cleaned-data'),
    dcc.Store(id='concentrations'),
    dcc.Store(id='excel-path'),
    dcc.Store(id='study_date'),
    dcc.Store(id='Total duration of study'),
    dcc.Store(id='duration of movement during study'),
    dcc.Store(id='Percentage of movement data'),
    dcc.Store(id='SNR before movement artifact removal'),
    dcc.Store(id='SNR after movement artifact removal')
])

UPLOAD_FOLDER = 'src/uploads'
COLUMN_NAMES = [
    'Time', 'System Time (s)', 'Sample Time (s)', 'LED_A_782_DET1', 'LED_A_782_DET2', 'LED_A_782_DET3',
    'LED_A_801_DET1', 'LED_A_801_DET2', 'LED_A_801_DET3', 'LED_A_808_DET1', 'LED_A_808_DET2', 'LED_A_808_DET3',
    'LED_A_828_DET1', 'LED_A_828_DET2', 'LED_A_828_DET3', 'LED_A_848_DET1', 'LED_A_848_DET2', 'LED_A_848_DET3',
    'LED_A_887_DET1', 'LED_A_887_DET2', 'LED_A_887_DET3', 'LED_A_DARK_DET1', 'LED_A_DARK_DET2', 'LED_A_DARK_DET3',
    'LED_B_782_DET1', 'LED_B_782_DET2', 'LED_B_782_DET3', 'LED_B_801_DET1', 'LED_B_801_DET2', 'LED_B_801_DET3',
    'LED_B_808_DET1', 'LED_B_808_DET2', 'LED_B_808_DET3', 'LED_B_828_DET1', 'LED_B_828_DET2', 'LED_B_828_DET3',
    'LED_B_848_DET1', 'LED_B_848_DET2', 'LED_B_848_DET3', 'LED_B_887_DET1', 'LED_B_887_DET2', 'LED_B_887_DET3',
    'LED_B_DARK_DET1', 'LED_B_DARK_DET2', 'LED_B_DARK_DET3', 'Accelerometer X axis', 'Accelerometer Y axis',
    'Accelerometer Z axis', 'Gyroscope X axis', 'Gyroscope Y axis', 'Gyroscope Z axis', 'PCB Temp', 'Skin Temp'
]


def clear_folder(folder_path):
    """Delete all files in the specified folder."""
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)

def parse_date(date_format):
    for fmt in ("%d-%b-%Y", "%d-%b-%y"):
        try:
            return datetime.strptime(date_format, fmt).strftime("%d/%m/%Y")
        except ValueError:
            continue
    raise ValueError(f"Date format not recognized: {date_format}")

@app.callback(
    Output("file-names", "children"),
    Output("uploaded-data", "data"),
    Output("study_date", "data"),
    State("upload-data", "filename"),
    Input("upload-data", "contents"),
)
def save_uploaded_file(filename, contents):
    if contents is None or filename is None:
        return "No file uploaded yet.", None, None  # ✅ Return 3 values

    # Clear existing files in the upload folder
    clear_folder(UPLOAD_FOLDER)

    # Decode file content
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    try:
        decoded_str = decoded.decode('utf-8')
    except UnicodeDecodeError:
        return "Error: File is not UTF-8 encoded. Upload data in CSV format", None, None  # ✅ Return 3 values

    # Save to file
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    with open(file_path, 'wb') as f:
        f.write(decoded)

    # Parse CSV if valid
    if filename.endswith('.csv'):
        full_data = pd.read_csv(io.StringIO(decoded_str), nrows=6)
        print('full_data', full_data)
        date_format = full_data.iloc[4, 1]
        print('date_format', date_format)

        try:
            date = parse_date(date_format)
        except ValueError as e:
            return f"Date format error: {e}", None, None  # ✅ Return 3 values

        df = pd.read_csv(io.StringIO(decoded_str), skiprows=10, names=COLUMN_NAMES)
        df['Time'] = df['Time'].str.strip("'")
        data_json = df.to_json(date_format='iso', orient='split')
        return f"File '{filename}' uploaded successfully with {len(df)} rows.", data_json, date
    else:
        return f"File '{filename}' uploaded successfully, but it is not a CSV file.", None, None  # ✅ Return 3 values

#==================================================================================================================================
def parse_time(time_str: str) -> float | None:
    """
    Convert 'mm:ss.d', 'mm:ss.dd', 'hh:mm:ss.ddd', etc. to total seconds (float).
    Returns None if the string cannot be parsed.
    """
    try:
        # Accept numeric inputs directly
        if isinstance(time_str, (int, float)):
            return float(time_str)

        s = str(time_str).strip()

        # ► Common patterns in descending order of precision
        patterns = [
            "%H:%M:%S.%f", "%H:%M:%S",
            "%M:%S.%f",   "%M:%S",
            "%S.%f",      "%S"
        ]
        for fmt in patterns:
            try:
                t = datetime.strptime(s, fmt)
                return (
                    t.hour  * 3600 +
                    t.minute * 60 +
                    t.second +
                    t.microsecond / 1e6
                )
            except ValueError:
                continue

        # Fallback: manual split (covers odd cases such as '23:31.4')
        if ":" in s:
            min_part, sec_part = s.split(":")
            if "." in sec_part:
                sec, subsecs = sec_part.split(".")
                return int(min_part) * 60 + int(sec) + float(f"0.{subsecs}")
            return int(min_part) * 60 + int(sec_part)

        # Last resort – plain float
        return float(s)

    except Exception as err:
        print(f"parse_time failed for '{time_str}': {err}")
        return None


# ──────────────────────────────────────────────────────────────
# 2.  Dash callback for 1 Hz resampling
# ──────────────────────────────────────────────────────────────

@callback(
    Output("resample-status",   "children"),
    Output("resampled-data",    "data"),
    Output("resampling-method", "data"),
    Input("resample-option",    "value"),
    State("uploaded-data",      "data"),
    State("upload-data",        "filename"),
    prevent_initial_call=True,
)
def on_resample_option_selected(option, uploaded_data_json, original_filename):
    if uploaded_data_json is None or original_filename is None:
        return "⚠️ No uploaded data.", None, "No resampling"

    import pandas as pd
    import os

    df = pd.read_json(uploaded_data_json, orient="split")

    # Group by the exact Time string, don't convert it
    if option == "average":
        resampled_df = df.groupby("Time", sort=False).mean(numeric_only=True)
        method = "1 Hz Average"
    elif option == "accumulation":
        resampled_df = df.groupby("Time", sort=False).sum(numeric_only=True)
        method = "1 Hz Accumulation"
    else:
        return f"⚠️ Unknown resample option: {option}", None, "No resampling"

    # Preserve original Time strings
    resampled_df.insert(0, "Time", resampled_df.index)
    resampled_df.reset_index(drop=True, inplace=True)

    # Save to CSV
    RESAMPLED_FOLDER = "src/resampled_data"
    os.makedirs(RESAMPLED_FOLDER, exist_ok=True)
    if "clear_folder" in globals():
        clear_folder(RESAMPLED_FOLDER)

    csv_name = f"{os.path.splitext(original_filename)[0]}_resampled_data.csv"
    resampled_df.to_csv(os.path.join(RESAMPLED_FOLDER, csv_name), index=False)

    return (
        f"✅ Resampled using: {method}",
        resampled_df.to_json(date_format="iso", orient="split"),
        method
    )

#==================================================================================================================================

@app.callback(
    Output("download-file-snirf", "data"),
    Output("snirf-download-status", "data"),
    Input("btn_rawdata_snirf", "n_clicks"),
    State("upload-data", "filename"),
    prevent_initial_call=True
)
def generate_and_download_raw_snirf(n_clicks, filename):
    if not n_clicks:
        return no_update, no_update

    if not filename:
        return no_update, no_update

    try:
        # Call the SNIRF file creation function
        snirf_path, snirf_name = create_snirf(filename)

        # Ensure file exists
        if snirf_path and os.path.exists(snirf_path):
            return dcc.send_file(snirf_path), snirf_name

    except Exception as e:
        print(f"Error generating/downloading SNIRF: {e}")
    
    return no_update, no_update

#===============Create intensity plots=============================================================================================================================
GROUPS = {
    'GroupA_Detector1': ['LED_A_782_DET1', 'LED_A_801_DET1', 'LED_A_808_DET1', 'LED_A_828_DET1', 'LED_A_848_DET1', 'LED_A_887_DET1', 'LED_A_DARK_DET1'],
    'GroupA_Detector2': ['LED_A_782_DET2', 'LED_A_801_DET2', 'LED_A_808_DET2', 'LED_A_828_DET2', 'LED_A_848_DET2', 'LED_A_887_DET2', 'LED_A_DARK_DET2'],
    'GroupA_Detector3': ['LED_A_782_DET3', 'LED_A_801_DET3', 'LED_A_808_DET3', 'LED_A_828_DET3', 'LED_A_848_DET3', 'LED_A_887_DET3', 'LED_A_DARK_DET3'],
    'GroupB_Detector1': ['LED_B_782_DET1', 'LED_B_801_DET1', 'LED_B_808_DET1', 'LED_B_828_DET1', 'LED_B_848_DET1', 'LED_B_887_DET1', 'LED_B_DARK_DET1'],
    'GroupB_Detector2': ['LED_B_782_DET2', 'LED_B_801_DET2', 'LED_B_808_DET2', 'LED_B_828_DET2', 'LED_B_848_DET2', 'LED_B_887_DET2', 'LED_B_DARK_DET2'],
    'GroupB_Detector3': ['LED_B_782_DET3', 'LED_B_801_DET3', 'LED_B_808_DET3', 'LED_B_828_DET3', 'LED_B_848_DET3', 'LED_B_887_DET3', 'LED_B_DARK_DET3'],
}

def calculate_magnitude(df, x_col, y_col, z_col):
    return np.sqrt(df[x_col]**2 + df[y_col]**2 + df[z_col]**2)


def create_intensity_figure(df, spectra_list, title, time_unit, include_sensor_data=False):
    from plotly.subplots import make_subplots
    import plotly.graph_objs as go
    import numpy as np

    # Ensure 'Time' is in datetime format
    if not np.issubdtype(df['Time'].dtype, np.datetime64):
        try:
            df['Time'] = pd.to_datetime(df['Time'])
        except Exception as e:
            print(f"⚠️ Failed to convert 'Time' to datetime: {e}")
            df['Time'] = np.arange(len(df))  # fallback to index

    x_time = df['Time']

    # Count total rows
    rows = 1 + (2 if include_sensor_data else 0)

    fig = make_subplots(
        rows=rows, cols=1, shared_xaxes=True, vertical_spacing=0.05,
        subplot_titles=[title] + (["Accelerometer Magnitude (m/s²)", "Gyroscope Magnitude (°/s)"] if include_sensor_data else [])
    )

    # Intensity Plots
    for col in spectra_list:
        if col in df.columns:
            fig.add_trace(go.Scatter(x=x_time, y=df[col], mode='lines', name=col), row=1, col=1)

    if include_sensor_data:
        # Accelerometer Magnitude
        accel_mag = calculate_magnitude(df, 'Accelerometer X axis', 'Accelerometer Y axis', 'Accelerometer Z axis')
        fig.add_trace(go.Scatter(x=x_time, y=accel_mag, mode='lines', name='Accelerometer Magnitude', line=dict(color='orange')),
                      row=2, col=1)

        # Gyroscope Magnitude
        gyro_mag = calculate_magnitude(df, 'Gyroscope X axis', 'Gyroscope Y axis', 'Gyroscope Z axis')
        fig.add_trace(go.Scatter(x=x_time, y=gyro_mag, mode='lines', name='Gyroscope Magnitude', line=dict(color='green')),
                      row=3, col=1)

    # Generate tickvals at 1-minute intervals
    tickvals = pd.date_range(start=df['Time'].min(), end=df['Time'].max(), freq='1min')

    fig.update_layout(
        height=1050,
        width=2140,
        autosize=False,
        title={'text': title, 'font': {'size': 24}},
        xaxis=dict(
            title=f'Time ({time_unit})',
            tickformat='%H:%M',
            tickvals=tickvals,
            tickangle=45
        ),
        margin=dict(l=60, r=40, t=80, b=60)
    )

    return fig

@app.callback(
    Output('intensity-time-plot', 'children'),
    Input('view-graph-btn', 'n_clicks'),
    State('resampled-data', 'data'),
    State('uploaded-data', 'data'),
    State('intensities-options-dropdown', 'value'),
    State('groupA_dect1_spectras', 'on'),
    State('groupA_dect2_spectras', 'on'),
    State('groupA_dect3_spectras', 'on'),
    State('groupB_dect1_spectras', 'on'),
    State('groupB_dect2_spectras', 'on'),
    State('groupB_dect3_spectras', 'on'),
    State('select_all_switch', 'on'),
    State('plot_sensor_data', 'on'),
    prevent_initial_call=True
)
def update_intensity_plot(n_clicks, resampled_json, uploaded_json, selected_spectra,
                          groupA1, groupA2, groupA3, groupB1, groupB2, groupB3,
                          select_all, plot_sensor_data):
    if not n_clicks:
        return html.Div("Click 'View Intensity Over Time' to generate plots.")

    # Load data
    df = pd.read_json(resampled_json or uploaded_json, orient='split')
    if df is None or df.empty:
        return html.Div("No data available for plotting.")
    
    time_unit = 's' if resampled_json else 'ms'

    # Apply Select All override
    if select_all:
        groupA1 = groupA2 = groupA3 = groupB1 = groupB2 = groupB3 = True

    tabs = []

    def add_tab(label, group_key):
        fig = create_intensity_figure(df, GROUPS[group_key], label, time_unit, include_sensor_data=plot_sensor_data)
        tabs.append(
            dcc.Tab(
                label=label,
                children=[
                    dcc.Graph(figure=fig, config={'responsive': True},
                              style={'height': '1000px', 'width': '100%'})
                ]
            )
        )

    if groupA1: add_tab("GroupA_Detector1", 'GroupA_Detector1')
    if groupA2: add_tab("GroupA_Detector2", 'GroupA_Detector2')
    if groupA3: add_tab("GroupA_Detector3", 'GroupA_Detector3')
    if groupB1: add_tab("GroupB_Detector1", 'GroupB_Detector1')
    if groupB2: add_tab("GroupB_Detector2", 'GroupB_Detector2')
    if groupB3: add_tab("GroupB_Detector3", 'GroupB_Detector3')

    if selected_spectra:
        fig = create_intensity_figure(df, selected_spectra, "Selected Intensities", time_unit, include_sensor_data=plot_sensor_data)
        tabs.append(
            dcc.Tab(
                label="Selected Intensities",
                children=[
                    dcc.Graph(figure=fig, config={'responsive': True},
                              style={'height': '1000px', 'width': '100%'})
                ]
            )
        )
    return dcc.Tabs(children=tabs)


#======================DATA QUALITY CHECK======================================================================================================================

@app.callback(
    Output('data-quality-plot', 'children'),
    Output('quality-metrics', 'data'),  # NEW OUTPUT
    Input('check-data-quality-btn', 'n_clicks'),
    State('resampled-data', 'data'),
    State('uploaded-data', 'data'),
    State('data_quality-check-dropdown', 'value'),
    prevent_initial_call=True
)
def update_data_quality_tab(n_clicks, resampled_json, uploaded_json, selected_col):
    if not n_clicks:
        return no_update, no_update

    df = pd.read_json(resampled_json or uploaded_json, orient='split')

    if df is None or df.empty:
        return html.Div("No data available for quality check."), no_update

    snr_hist_fig, snr_plot, snr_bar_chart, nep_bar_chart, scatter_plot, distance_to_dark_plot, saturation_fig, gauge_fig  = data_quality_check(df, selected_col)

    # Extract values for storing
    snr_vals = snr_bar_chart['data'][0]['y']  # SNR Group 1, 2, 3
    nep_vals = nep_bar_chart['data'][0]['y']  # NEP Group 1, 2, 3

    metrics = {
        "SNR Short (A1 + B3)": snr_vals[0],
        "SNR Mid (A2 + B2)": snr_vals[1],
        "SNR Long (A3 + B1)": snr_vals[2],
        "NEP DET 1": nep_vals[0],
        "NEP DET 2": nep_vals[1],
        "NEP DET 3": nep_vals[2],
    }

    return html.Div([
        html.Div(dcc.Graph(figure=snr_hist_fig)),
        html.Div(dcc.Graph(figure=snr_plot)),
        html.Div([
            html.Div(dcc.Graph(figure=snr_bar_chart), style={'display': 'inline-block', 'width': '48%'}),
            html.Div(dcc.Graph(figure=nep_bar_chart), style={'display': 'inline-block', 'width': '48%'}),
        ]),
        html.Div(dcc.Graph(figure=scatter_plot)),
        html.Div(dcc.Graph(figure=distance_to_dark_plot)),
        html.Div(dcc.Graph(figure=saturation_fig)),
        html.Div(dcc.Graph(figure=gauge_fig))
    ]), metrics
#=================================Data Cleaning=============================================================
@app.callback(
    Output('data-clean-plot', 'children'),
    Output('cleaned-data', 'data'),
    Input('apply-button', 'n_clicks'),
    Input('view-button', 'n_clicks'),
    State('resampled-data', 'data'),
    State('uploaded-data', 'data'),
    State('upload-data', 'filename'),
    State('preprocessing-options-subtract-dark', 'value'),  
    State('preprocessing-options-highpass', 'value'),
    State('highpass-cutoff-input', 'value'),
    State('highpass-order-input', 'value'),
    State('highpass-sampling-rate-input', 'value'),
    State('preprocessing-options-lowpass', 'value'),
    State('lowpass-cutoff-input', 'value'),
    State('lowpass-order-input', 'value'),
    State('lowpass-sampling-rate-input', 'value'),
    State('preprocessing-options-bandpass', 'value'),
    State('bandpass-lower-cutoff-input', 'value'),
    State('bandpass-upper-cutoff-input', 'value'),
    State('bandpass-order-input', 'value'),
    State('bandpass-sampling-rate-input', 'value'),
    State('preprocessing-options-median', 'value'),
    State('median-filter-size-input', 'value'),
    State('groupA_dect1_data_clean', 'on'),
    State('groupA_dect2_data_clean', 'on'),
    State('groupA_dect3_data_clean', 'on'),
    State('groupB_dect1_data_clean', 'on'),
    State('groupB_dect2_data_clean', 'on'),
    State('groupB_dect3_data_clean', 'on'),
    prevent_initial_call=True
)
def data_cleaning(
    apply_clicks, view_clicks, resampled_json, uploaded_json, uploaded_filename,
    subtract_dark_opt,
    highpass_opt, hp_cutoff, hp_order, hp_sr,
    lowpass_opt, lp_cutoff, lp_order, lp_sr,
    bandpass_opt, bp_low, bp_high, bp_order, bp_sr,
    median_opt, median_size,
    gA1, gA2, gA3, gB1, gB2, gB3
):
    import os
    import pandas as pd
    from dash import html, dcc, callback_context
    from scipy.signal import butter, filtfilt, medfilt
    import plotly.graph_objs as go

    ctx = callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update

    if not any([apply_clicks, view_clicks]):
        return dash.no_update, dash.no_update

    data_json = resampled_json or uploaded_json
    if not data_json:
        return html.Div("No data available."), dash.no_update

    df = pd.read_json(data_json, orient='split')
    if df.empty:
        return html.Div("Loaded data is empty."), dash.no_update

    cleaned = df.copy()
    time = df['Time'] if 'Time' in df.columns else df.index
    cleaned['Time'] = time
    num_cols = cleaned.select_dtypes(include='number').columns.drop('Time', errors='ignore')

    # Step 1: Subtract Dark
    if subtract_dark_opt and 'subtract-dark' in subtract_dark_opt:
        dark_mapping = {
            f"LED_A_{wl}_DET{i}": f"LED_A_DARK_DET{i}"
            for wl in ['782', '801', '808', '828', '848', '887'] for i in [1, 2, 3]
        }
        dark_mapping.update({
            f"LED_B_{wl}_DET{i}": f"LED_B_DARK_DET{i}"
            for wl in ['782', '801', '808', '828', '848', '887'] for i in [1, 2, 3]
        })

        for main_col, dark_col in dark_mapping.items():
            if main_col in cleaned.columns and dark_col in df.columns:
                cleaned[main_col] = df[main_col] - df[dark_col]

        cleaned.drop(columns=[col for col in cleaned.columns if 'DARK' in col], inplace=True, errors='ignore')
        num_cols = cleaned.select_dtypes(include='number').columns.drop('Time', errors='ignore')

    def apply_filter(opt, cutoff, order, sr, btype):
        if opt and btype in opt:
            if isinstance(cutoff, (list, tuple)):
                low, high = cutoff
                if low <= 0 or high <= low or high >= sr / 2:
                    raise ValueError(f"Invalid band-pass range: {low}-{high} Hz")
                b, a = butter(order, [low, high], btype='bandpass', fs=sr)
            else:
                if cutoff <= 0 or cutoff >= sr / 2:
                    raise ValueError(f"Invalid {btype} cutoff: {cutoff} Hz")
                b, a = butter(order, cutoff, btype=btype, fs=sr)

            for col in num_cols:
                cleaned[col] = filtfilt(b, a, cleaned[col])

    try:
        apply_filter(highpass_opt, hp_cutoff, hp_order, hp_sr, 'highpass')
        apply_filter(lowpass_opt, lp_cutoff, lp_order, lp_sr, 'lowpass')
        apply_filter(bandpass_opt, [bp_low, bp_high], bp_order, bp_sr, 'bandpass')

        if median_opt and 'median' in median_opt:
            try:
                size = int(median_size)
                if size % 2 == 0 or size < 1:
                    raise ValueError("Median filter size must be a positive odd integer.")
            except Exception:
                raise ValueError("Invalid median filter size. Please enter a positive odd integer.")
            for col in num_cols:
                cleaned[col] = medfilt(cleaned[col], kernel_size=size)

    except ValueError as e:
        return html.Div(f"⚠️ {str(e)}"), dash.no_update

    # Plotting
    plots = []
    toggle_map = {
        'GroupA_Detector1': gA1,
        'GroupA_Detector2': gA2,
        'GroupA_Detector3': gA3,
        'GroupB_Detector1': gB1,
        'GroupB_Detector2': gB2,
        'GroupB_Detector3': gB3,
    }

    for group_name, enabled in toggle_map.items():
        if not enabled:
            continue

        figs = []
        for col in GROUPS[group_name]:
            if col in df.columns and col in cleaned.columns:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=time, y=df[col], name='Raw', line=dict(dash='dot')))
                fig.add_trace(go.Scatter(x=time, y=cleaned[col], name='Cleaned'))
                fig.update_layout(title=col, xaxis_title='Time', yaxis_title='Voltage', height=300)
                figs.append(dcc.Graph(figure=fig))

        if figs:
            plots.append(html.Div([
                html.H4(group_name, style={'marginTop': '20px', 'color': '#003f5c'}),
                *figs
            ]))

    # Save cleaned data
    out_dir = "src/cleaned_data/data_clean"
    os.makedirs(out_dir, exist_ok=True)
    for f in os.listdir(out_dir):
        try:
            os.remove(os.path.join(out_dir, f))
        except Exception as e:
            print(f"Warning: couldn't delete file: {e}")

    base = os.path.splitext(uploaded_filename or "resampled_data")[0]
    out_path = os.path.join(out_dir, f"{base}_cleaned.csv")
    cleaned.to_csv(out_path, index=False)

    if not plots:
        return html.Div("No groups selected or no matching signals found."), cleaned.to_json(orient='split')

    return html.Div(plots), cleaned.to_json(orient='split')


# ================================= update_movement_analysis_plot =============================================

import pandas as pd
import numpy as np
from plotly.subplots import make_subplots
import plotly.graph_objs as go
import os
from datetime import datetime
import shutil

# Save folder for artifact-removed data
ARTIFACT_FOLDER = "src/artifact_removed_data"
os.makedirs(ARTIFACT_FOLDER, exist_ok=True)

# Define SNR groups
groups_snr_cols = {
    'LED_A_Detector_1 + LED_B_Detector_3': [
        'LED_A_782_DET1','LED_A_801_DET1','LED_A_808_DET1','LED_A_828_DET1','LED_A_848_DET1','LED_A_887_DET1',
        'LED_B_782_DET3','LED_B_801_DET3','LED_B_808_DET3','LED_B_828_DET3','LED_B_848_DET3','LED_B_887_DET3'
    ],
    'LED_A_Detector_2 + LED_B_Detector_2': [
        'LED_A_782_DET2','LED_A_801_DET2','LED_A_808_DET2','LED_A_828_DET2','LED_A_848_DET2','LED_A_887_DET2',
        'LED_B_782_DET2','LED_B_801_DET2','LED_B_808_DET2','LED_B_828_DET2','LED_B_848_DET2','LED_B_887_DET2'
    ],
    'LED_A_Detector_3 + LED_B_Detector_1': [
        'LED_A_782_DET3','LED_A_801_DET3','LED_A_808_DET3','LED_A_828_DET3','LED_A_848_DET3','LED_A_887_DET3',
        'LED_B_782_DET1','LED_B_801_DET1','LED_B_808_DET1','LED_B_828_DET1','LED_B_848_DET1','LED_B_887_DET1'
    ]
}

# Map signals to dark columns
signal_dark_dictionary = {
    'LED_A_782_DET1': 'LED_A_DARK_DET1', 'LED_A_801_DET1': 'LED_A_DARK_DET1', 'LED_A_808_DET1': 'LED_A_DARK_DET1',
    'LED_A_828_DET1': 'LED_A_DARK_DET1', 'LED_A_848_DET1': 'LED_A_DARK_DET1', 'LED_A_887_DET1': 'LED_A_DARK_DET1',
    'LED_A_782_DET2': 'LED_A_DARK_DET2', 'LED_A_801_DET2': 'LED_A_DARK_DET2', 'LED_A_808_DET2': 'LED_A_DARK_DET2',
    'LED_A_828_DET2': 'LED_A_DARK_DET2', 'LED_A_848_DET2': 'LED_A_DARK_DET2', 'LED_A_887_DET2': 'LED_A_DARK_DET2',
    'LED_A_782_DET3': 'LED_A_DARK_DET3', 'LED_A_801_DET3': 'LED_A_DARK_DET3', 'LED_A_808_DET3': 'LED_A_DARK_DET3',
    'LED_A_828_DET3': 'LED_A_DARK_DET3', 'LED_A_848_DET3': 'LED_A_DARK_DET3', 'LED_A_887_DET3': 'LED_A_DARK_DET3',
    'LED_B_782_DET1': 'LED_B_DARK_DET1', 'LED_B_801_DET1': 'LED_B_DARK_DET1', 'LED_B_808_DET1': 'LED_B_DARK_DET1',
    'LED_B_828_DET1': 'LED_B_DARK_DET1', 'LED_B_848_DET1': 'LED_B_DARK_DET1', 'LED_B_887_DET1': 'LED_B_DARK_DET1',
    'LED_B_782_DET2': 'LED_B_DARK_DET2', 'LED_B_801_DET2': 'LED_B_DARK_DET2', 'LED_B_808_DET2': 'LED_B_DARK_DET2',
    'LED_B_828_DET2': 'LED_B_DARK_DET2', 'LED_B_848_DET2': 'LED_B_DARK_DET2', 'LED_B_887_DET2': 'LED_B_DARK_DET2',
    'LED_B_782_DET3': 'LED_B_DARK_DET3', 'LED_B_801_DET3': 'LED_B_DARK_DET3', 'LED_B_808_DET3': 'LED_B_DARK_DET3',
    'LED_B_828_DET3': 'LED_B_DARK_DET3', 'LED_B_848_DET3': 'LED_B_DARK_DET3', 'LED_B_887_DET3': 'LED_B_DARK_DET3'
}

# --- Helper: compute same SNR groups used in the concentrations exporter ---
def calculate_group_snr_dict(df):
    """
    Returns a dict with keys 'Short', 'Mid', 'Long' containing the mean SNR
    for the channel groups used in the concentration SNR summary.
    """
    def calc_snr_for_signal(signal_col, dark_col):
        try:
            s = pd.to_numeric(df[signal_col].dropna()).mean()
            d = pd.to_numeric(df[dark_col].dropna()).mean()
            return (s - d) / d if (d != 0 and not np.isnan(d)) else 0.0
        except Exception:
            return 0.0

    short_group = [
        'LED_A_782_DET1', 'LED_A_801_DET1', 'LED_A_808_DET1',
        'LED_B_887_DET3', 'LED_B_848_DET3', 'LED_B_828_DET3'
    ]
    mid_group = [
        'LED_A_782_DET2', 'LED_A_801_DET2', 'LED_A_808_DET2',
        'LED_B_887_DET2', 'LED_B_848_DET2', 'LED_B_828_DET2'
    ]
    long_group = [
        'LED_A_782_DET3', 'LED_A_801_DET3', 'LED_A_808_DET3',
        'LED_B_887_DET1', 'LED_B_848_DET1', 'LED_B_828_DET1'
    ]

    def group_mean(group):
        vals = []
        for s in group:
            d = signal_dark_dictionary.get(s)
            if s in df.columns and d in df.columns:
                vals.append(calc_snr_for_signal(s, d))
        return float(np.mean(vals)) if vals else 0.0

    return {'Short': group_mean(short_group),
            'Mid': group_mean(mid_group),
            'Long': group_mean(long_group)}


def calculate_group_snr(df):
    snr_dict = {}
    for sig, dark in signal_dark_dictionary.items():
        if sig in df.columns and dark in df.columns:
            s = pd.to_numeric(df[sig], errors='coerce')
            d = pd.to_numeric(df[dark], errors='coerce')
            snr_dict[sig] = (np.nanmean(s) - np.nanmean(d)) / (np.nanmean(d) + 1e-12)
        else:
            snr_dict[sig] = 0

    group_avg_snr = {}
    for group_name, cols in groups_snr_cols.items():
        values = [snr_dict[c] for c in cols if c in snr_dict]
        group_avg_snr[group_name] = np.mean(values) if values else 0
    return group_avg_snr
# ----------------- Updated movement callback -----------------
# ----------------------- update_movement_analysis_plot (full callback) -----------------------
@app.callback(
    Output('movement-analysis-plot', 'children'),
    Output('movement-threshold-display', 'children'),
    Input('plot-intensity-sensor-btn', 'n_clicks'),
    Input('view-metrics-btn', 'n_clicks'),
    Input('artifact-removal-btn', 'n_clicks'),
    State('resampled-data', 'data'),
    State('uploaded-data', 'data'),
    prevent_initial_call=True
)
def update_movement_analysis_plot(n_plot, n_metrics, n_artifact, resampled_json, uploaded_json):
    import json
    from dash import callback_context as ctx, no_update
    from datetime import datetime
    import shutil

    triggered_id = ctx.triggered_id
    print(f"Triggered by: {triggered_id}")

    # Ensure artifact folder exists and clear for fresh files
    shutil.rmtree(ARTIFACT_FOLDER, ignore_errors=True)
    os.makedirs(ARTIFACT_FOLDER, exist_ok=True)

    # Load data (priority resampled > uploaded)
    try:
        df = pd.read_json(resampled_json or uploaded_json, orient='split')
    except Exception as e:
        print("Failed to load JSON input:", e)
        return html.Div("No data available for plotting."), no_update

    if df is None or df.empty:
        return html.Div("No data available for plotting."), no_update

    # Parse Time
    if 'Time' in df.columns:
        parsed = pd.to_datetime(df['Time'], errors='coerce')
        if not parsed.isna().all():
            df['Time'] = parsed
            time_is_datetime = True
        else:
            df['Time'] = pd.to_numeric(df['Time'], errors='coerce')
            time_is_datetime = False
    else:
        df['Time'] = np.arange(len(df))
        time_is_datetime = False

    # Select valid group columns (falls back to empty if GROUPS missing)
    group_columns = GROUPS.get('GroupA_Detector1', []) if isinstance(GROUPS, dict) else []
    valid_columns = [c for c in group_columns if c in df.columns]

    # Sensor axes
    accel_cols = ['Accelerometer X axis', 'Accelerometer Y axis', 'Accelerometer Z axis']
    gyro_cols = ['Gyroscope X axis', 'Gyroscope Y axis', 'Gyroscope Z axis']
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if 'Time' in numeric_cols:
        numeric_cols.remove('Time')

    # Compute accel/gyro magnitudes and movement episodes
    accel_mag = None
    gyro_mag = None
    movement_episode = None
    if all(c in df.columns for c in accel_cols):
        df[accel_cols] = df[accel_cols].apply(pd.to_numeric, errors='coerce')
        accel_mag = np.sqrt(np.sum(np.square(df[accel_cols]), axis=1))
    if all(c in df.columns for c in gyro_cols):
        df[gyro_cols] = df[gyro_cols].apply(pd.to_numeric, errors='coerce')
        gyro_mag = np.sqrt(np.sum(np.square(df[gyro_cols]), axis=1))

    movement_threshold = None
    if accel_mag is not None:
        movement_threshold = float(accel_mag.mean() + 2 * accel_mag.std())
        movement_episode = (accel_mag > movement_threshold).astype(int)

    # Build the "normal" multi-subplot figure
    n_rows = 1 + (1 if accel_mag is not None else 0) + (1 if gyro_mag is not None else 0) + (1 if movement_episode is not None else 0)
    normal_fig = make_subplots(rows=n_rows, cols=1, shared_xaxes=True, vertical_spacing=0.05)
    row_idx = 1
    # Add group traces (if available)
    for col in valid_columns:
        normal_fig.add_trace(go.Scatter(x=df['Time'], y=df[col], mode='lines', name=col), row=row_idx, col=1)
    row_idx += 1
    if accel_mag is not None:
        normal_fig.add_trace(go.Scatter(x=df['Time'], y=accel_mag, mode='lines', name='Accel Mag', line=dict(color='orange')), row=row_idx, col=1)
        row_idx += 1
    if gyro_mag is not None:
        normal_fig.add_trace(go.Scatter(x=df['Time'], y=gyro_mag, mode='lines', name='Gyro Mag', line=dict(color='green')), row=row_idx, col=1)
        row_idx += 1
    if movement_episode is not None:
        normal_fig.add_trace(go.Scatter(x=df['Time'], y=movement_episode, mode='lines', name='Movement Episodes',
                                        line=dict(color='red', width=2, shape='hv')), row=row_idx, col=1)
    normal_fig.update_layout(height=320 * n_rows, width=2500, title="GroupA_Detector1 & Movement Analysis (Original)", font=dict(size=16))

    # Metrics & artifact content containers
    metrics_content, artifact_content = [], []
    snr_before = {}
    snr_after = {}

    # Respond only when metrics or artifact button triggered
    if triggered_id in ('view-metrics-btn', 'artifact-removal-btn') and accel_mag is not None:
        # Compute total time & movement stats
        if time_is_datetime:
            total_time = (df['Time'].iloc[-1] - df['Time'].iloc[0]).total_seconds()
        else:
            total_time = float(df['Time'].iloc[-1] - df['Time'].iloc[0])
        movement_time = int(movement_episode.sum())
        movement_pct = (movement_time / len(df)) * 100

        # Pie and stacked bar figures
        pie_fig = go.Figure(data=[go.Pie(labels=['Movement', 'No Movement'],
                                         values=[movement_time, len(df) - movement_time],
                                         hole=0.35, textinfo='label+percent')])
        pie_fig.update_layout(title="Movement vs No Movement", height=600, font=dict(size=22))

        stack_fig = go.Figure(data=[
            go.Bar(name="Movement", x=["Samples"], y=[movement_time]),
            go.Bar(name="No Movement", x=["Samples"], y=[len(df) - movement_time])
        ])
        stack_fig.update_layout(barmode="stack", title="Movement vs No Movement (Stacked)", height=600, font=dict(size=22))

        # SNR before (uses module-level helper if present; fall back to local)
        try:
            snr_before = calculate_group_snr(df)  # module-level helper if available
        except Exception:
            # fallback: compute group SNR by averaging per-signal SNR via signal_dark_dictionary & groups_snr_cols
            temp = {}
            for group_name, cols in groups_snr_cols.items():
                vals = []
                for sig in cols:
                    dark = signal_dark_dictionary.get(sig)
                    if sig in df.columns and dark in df.columns:
                        s = pd.to_numeric(df[sig], errors='coerce')
                        d = pd.to_numeric(df[dark], errors='coerce')
                        vals.append((np.nanmean(s) - np.nanmean(d)) / (np.nanmean(d) + 1e-12))
                temp[group_name] = float(np.mean(vals)) if vals else 0.0
            snr_before = temp

        # Artifact removal (only when artifact button clicked)
        df_artifact = df.copy()
        if triggered_id == 'artifact-removal-btn' and movement_episode is not None and movement_episode.any():
            mask = movement_episode.astype(bool)
            df_artifact.loc[mask, numeric_cols] = np.nan
            if time_is_datetime:
                df_artifact = df_artifact.set_index('Time')
                df_artifact = df_artifact[~df_artifact.index.isna()]
                df_artifact[numeric_cols] = df_artifact[numeric_cols].interpolate(method='time', limit_direction='both')
                df_artifact = df_artifact.reset_index()
            else:
                df_artifact[numeric_cols] = df_artifact[numeric_cols].interpolate(method='linear', limit_direction='both')
            df_artifact[numeric_cols] = df_artifact[numeric_cols].fillna(method='ffill').fillna(method='bfill')

            # Save artifact-removed dataframe
            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            save_path_data = os.path.join(ARTIFACT_FOLDER, f"artifact_removed_{ts}.csv")
            df_artifact.to_csv(save_path_data, index=False)
            print(f"Saved artifact removed data to {save_path_data}")

            # SNR after
            try:
                snr_after = calculate_group_snr(df_artifact)
            except Exception:
                # fallback same as above using groups_snr_cols
                temp_after = {}
                for group_name, cols in groups_snr_cols.items():
                    vals = []
                    for sig in cols:
                        dark = signal_dark_dictionary.get(sig)
                        if sig in df_artifact.columns and dark in df_artifact.columns:
                            s = pd.to_numeric(df_artifact[sig], errors='coerce')
                            d = pd.to_numeric(df_artifact[dark], errors='coerce')
                            vals.append((np.nanmean(s) - np.nanmean(d)) / (np.nanmean(d) + 1e-12))
                    temp_after[group_name] = float(np.mean(vals)) if vals else 0.0
                snr_after = temp_after

            # Build metrics_summary including before + after SNR
            metrics_summary = {
                "Total_Time_sec": float(total_time),
                "Movement_Time_samples": int(movement_time),
                "Movement_Percentage": float(movement_pct)
            }
            for k, v in snr_before.items():
                metrics_summary[f"SNR_Before_{k}"] = float(v)
            for k, v in snr_after.items():
                metrics_summary[f"SNR_After_{k}"] = float(v)

            # Save CSV and JSON
            save_path_metrics = os.path.join(ARTIFACT_FOLDER, f"artifact_removed_metrics_{ts}.csv")
            pd.DataFrame([metrics_summary]).to_csv(save_path_metrics, index=False)
            latest_metrics_path = os.path.join(ARTIFACT_FOLDER, "latest_movement_metrics.json")
            with open(latest_metrics_path, "w") as fh:
                json.dump(metrics_summary, fh, indent=2)
            print(f"Saved artifact metrics CSV: {save_path_metrics}")
            print(f"Saved latest movement metrics JSON: {latest_metrics_path}")

            # build artifact plot content
            fig_artifact = go.Figure()
            for col in valid_columns:
                if col in df_artifact.columns:
                    fig_artifact.add_trace(go.Scatter(x=df_artifact['Time'], y=df_artifact[col], mode='lines', name=col))
            fig_artifact.update_layout(title="GroupA_Detector1 After Artifact Removal", height=600, width=2500, font=dict(size=18))
            artifact_content = [dcc.Graph(figure=fig_artifact)]
        else:
            # For "view metrics" or when no movement episodes exist we still create a metrics_summary (without SNR_After)
            metrics_summary = {
                "Total_Time_sec": float(total_time),
                "Movement_Time_samples": int(movement_time),
                "Movement_Percentage": float(movement_pct)
            }
            for k, v in snr_before.items():
                metrics_summary[f"SNR_Before_{k}"] = float(v)

            # Also save the latest metrics JSON (so concentrations exporter can read it)
            latest_metrics_path = os.path.join(ARTIFACT_FOLDER, "latest_movement_metrics.json")
            with open(latest_metrics_path, "w") as fh:
                json.dump(metrics_summary, fh, indent=2)
            # Save a timestamped CSV for traceability
            ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
            save_path_metrics = os.path.join(ARTIFACT_FOLDER, f"movement_metrics_{ts}.csv")
            pd.DataFrame([metrics_summary]).to_csv(save_path_metrics, index=False)
            print(f"Saved view-metrics CSV: {save_path_metrics}")
            print(f"Saved latest movement metrics JSON: {latest_metrics_path}")

        # Build SNR before/after plot
        snr_fig = go.Figure()
        keys = [k for k in snr_before.keys()]
        snr_fig.add_trace(go.Bar(x=keys, y=[snr_before[k] for k in keys], name="Before", marker_color="blue",
                                text=[f"{snr_before[k]:.2f}" for k in keys], textposition="outside"))
        if snr_after:
            snr_fig.add_trace(go.Bar(x=keys, y=[snr_after.get(k, 0) for k in keys], name="After", marker_color="red",
                                    text=[f"{snr_after.get(k, 0):.2f}" for k in keys], textposition="outside"))
        snr_fig.update_layout(barmode="group", title="SNR Before vs After", height=600, font=dict(size=22))

        # Prepare metrics content for display
        metrics_content = [dcc.Graph(figure=pie_fig), dcc.Graph(figure=stack_fig), dcc.Graph(figure=snr_fig)]

    # Final body and threshold display
    body = [dcc.Graph(figure=normal_fig)]
    if metrics_content:
        body.extend(metrics_content)
    if artifact_content:
        body.extend(artifact_content)

    threshold_display = f"Movement threshold: {movement_threshold:.4f} m/s²" if movement_threshold is not None else "No threshold"
    return html.Div(body), threshold_display

import os
import pandas as pd
import numpy as np
import plotly.express as px
from dash import dcc, html
from dash.dependencies import Input, Output, State
import dash

# Dark subtraction mapping
signal_dark_dictionary = {
    'LED_A_782_DET1': 'LED_A_DARK_DET1', 'LED_A_801_DET1': 'LED_A_DARK_DET1', 'LED_A_808_DET1': 'LED_A_DARK_DET1',
    'LED_A_828_DET1': 'LED_A_DARK_DET1', 'LED_A_848_DET1': 'LED_A_DARK_DET1', 'LED_A_887_DET1': 'LED_A_DARK_DET1',
    'LED_A_782_DET2': 'LED_A_DARK_DET2', 'LED_A_801_DET2': 'LED_A_DARK_DET2', 'LED_A_808_DET2': 'LED_A_DARK_DET2',
    'LED_A_828_DET2': 'LED_A_DARK_DET2', 'LED_A_848_DET2': 'LED_A_DARK_DET2', 'LED_A_887_DET2': 'LED_A_DARK_DET2',
    'LED_A_782_DET3': 'LED_A_DARK_DET3', 'LED_A_801_DET3': 'LED_A_DARK_DET3', 'LED_A_808_DET3': 'LED_A_DARK_DET3',
    'LED_A_828_DET3': 'LED_A_DARK_DET3', 'LED_A_848_DET3': 'LED_A_DARK_DET3', 'LED_A_887_DET3': 'LED_A_DARK_DET3',
    'LED_B_782_DET1': 'LED_B_DARK_DET1', 'LED_B_801_DET1': 'LED_B_DARK_DET1', 'LED_B_808_DET1': 'LED_B_DARK_DET1',
    'LED_B_828_DET1': 'LED_B_DARK_DET1', 'LED_B_848_DET1': 'LED_B_DARK_DET1', 'LED_B_887_DET1': 'LED_B_DARK_DET1',
    'LED_B_782_DET2': 'LED_B_DARK_DET2', 'LED_B_801_DET2': 'LED_B_DARK_DET2', 'LED_B_808_DET2': 'LED_B_DARK_DET2',
    'LED_B_828_DET2': 'LED_B_DARK_DET2', 'LED_B_848_DET2': 'LED_B_DARK_DET2', 'LED_B_887_DET2': 'LED_B_DARK_DET2',
    'LED_B_782_DET3': 'LED_B_DARK_DET3', 'LED_B_801_DET3': 'LED_B_DARK_DET3', 'LED_B_808_DET3': 'LED_B_DARK_DET3',
    'LED_B_828_DET3': 'LED_B_DARK_DET3', 'LED_B_848_DET3': 'LED_B_DARK_DET3', 'LED_B_887_DET3': 'LED_B_DARK_DET3'
}

@app.callback(
    Output('concentrations-plot', 'children'),
    Output('concentrations', 'data'),
    Input("study_date", "data"),
    Input('calculate-concentrations-btn', 'n_clicks'),
    State('cleaned-data', 'data'),
    State('resampled-data', 'data'),
    State('uploaded-data', 'data'),
    State('resampling-method', 'data'),
    State('upload-data', 'filename'),
    prevent_initial_call=True
)
def on_calculate_concentrations(date, n_clicks, cleaned_json, resampled_json, uploaded_json, resampling_method, filename):
    if not n_clicks:
        return dash.no_update, dash.no_update

    # Priority: Cleaned > Resampled > Raw
    df = None
    resample_note = resampling_method or "No resampling"

    if cleaned_json:
        df = pd.read_json(cleaned_json, orient='split')
        print('✅ Using cleaned data')
    elif resampled_json:
        df = pd.read_json(resampled_json, orient='split')
        print('✅ Using resampled data')
    elif uploaded_json:
        df = pd.read_json(uploaded_json, orient='split')
        print('✅ Using raw uploaded data')

    if df is None or df.empty:
        return html.Div("❌ No valid data to calculate concentrations."), dash.no_update

    # Subtract dark signals from respective columns
    df_corrected = df.copy()
    for signal_col, dark_col in signal_dark_dictionary.items():
        if signal_col in df.columns and dark_col in df.columns:
            df_corrected[signal_col] = df[signal_col] - df[dark_col]

    # Extract relevant columns
    selected_cols = [col for col in df_corrected.columns if col.startswith("LED_") or col == "Time"]
    df_selected = df_corrected[selected_cols]

    # Run calculations
    conc_a_1_df, conc_a_2_df, conc_a_3_df, \
    conc_b_1_df, conc_b_2_df, conc_b_3_df, \
    atten_a_1, atten_a_2, atten_a_3, \
    atten_b_1, atten_b_2, atten_b_3, wavelengths = UCLN(df_selected)

    sto2_result = SRS(df_selected)
    df_sto2_A = pd.DataFrame({"Sto2_A": sto2_result["StO2_A"]})
    df_sto2_B = pd.DataFrame({"Sto2_B": sto2_result["StO2_B"]})

    ds_sto2_result = dual_slope_wavelength(df_selected)
    df_sto2_dual = pd.DataFrame({"dual_slope_sto2": ds_sto2_result["ds_sto2_AB"]})

    # Group all results (same as before)
    sheet_data = {
        "Concentration LED A-DET 1": conc_a_1_df,
        "Concentration LED A-DET 2": conc_a_2_df,
        "Concentration LED A-DET 3": conc_a_3_df,
        "Concentration LED B-DET 1": conc_b_1_df,
        "Concentration LED B-DET 2": conc_b_2_df,
        "Concentration LED B-DET 3": conc_b_3_df,
        "Tissue oxygen saturation(StO2) LED A": df_sto2_A,
        "Tissue oxygen saturation(StO2) LED B": df_sto2_B,
        "Tissue oxygen saturation(StO2) Dual Slope": df_sto2_dual
    }

    # Read latest movement metrics (if any) saved by the movement callback
    movement_metrics = None
    try:
        latest_metrics_path = os.path.join(ARTIFACT_FOLDER, "latest_movement_metrics.json")
        if os.path.exists(latest_metrics_path):
            with open(latest_metrics_path, "r") as fh:
                movement_metrics = json.load(fh)
            print(f"Loaded movement metrics from {latest_metrics_path}")
    except Exception as e:
        print("Could not load latest movement metrics:", e)
        movement_metrics = None

    # Generate Excel (pass movement_metrics through)
    output_dir = os.path.join(os.path.dirname(__file__), "src", "concentrations_ucln_srs", "concentration_data")
    os.makedirs(output_dir, exist_ok=True)
    for file in os.listdir(output_dir):
        try:
            file_path = os.path.join(output_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
                print(f"🗑️ Deleted existing file: {file_path}")
        except Exception as e:
            print(f"❌ Error deleting file {file_path}: {e}")

    excel_path = generate_concentration_excel(
        filename=filename,
        resample_note=resample_note,
        df=df_corrected,
        conc_a_1_df=conc_a_1_df,
        conc_a_2_df=conc_a_2_df,
        conc_a_3_df=conc_a_3_df,
        conc_b_1_df=conc_b_1_df,
        conc_b_2_df=conc_b_2_df,
        conc_b_3_df=conc_b_3_df,
        df_sto2_A=df_sto2_A,
        df_sto2_B=df_sto2_B,
        df_sto2_dual=df_sto2_dual,
        output_dir=output_dir,
        date=date,
        movement_metrics=movement_metrics  # <-- pass it here
    )

    # (rest of function building tabs remains unchanged)
    tabs = []
    for name, df_plot in sheet_data.items():
        if not df_plot.empty:
            fig = px.line(df_plot, title=name)
            fig.update_layout(
                xaxis_title="Time",
                yaxis_title="ΔC (mM)" if "Concentration" in name else "StO2 (%)"
            )
            if "Tissue oxygen saturation" in name:
                if "LED A" in name:
                    tab_label = "StO₂ - LED A"
                elif "LED B" in name:
                    tab_label = "StO₂ - LED B"
                elif "Dual Slope" in name:
                    tab_label = "StO₂ - Dual"
                else:
                    tab_label = "StO₂"
            else:
                tab_label = name[:31]

            tabs.append(dcc.Tab(label=tab_label, children=[
                html.Div([
                    html.H5(name),
                    dcc.Graph(figure=fig, style={'height': '70vh'})
                ])
            ]))

    return dcc.Tabs(children=tabs), {
        "preview": {name: df.head().to_dict('records') for name, df in sheet_data.items()},
        "excel_path": excel_path
    }


# ----------------------- generate_concentration_excel (corrected full function) -----------------------
import os
import numpy as np
import pandas as pd

def generate_concentration_excel(
    filename, resample_note, df,
    conc_a_1_df, conc_a_2_df, conc_a_3_df,
    conc_b_1_df, conc_b_2_df, conc_b_3_df,
    df_sto2_A, df_sto2_B, df_sto2_dual,
    output_dir, date,
    movement_metrics=None
):
    # Prepare output path
    base_filename = filename.split('.')[0] if filename else "output"
    output_path = os.path.join(output_dir, f"{base_filename}_concentrations.xlsx")

    # Mapping for SNR
    signal_dark_dictionary = {
        f'LED_{side}_{wl}_DET{d}': f'LED_{side}_DARK_DET{d}'
        for side in ['A', 'B'] for wl in ['782', '801', '808', '828', '848', '887'] for d in [1, 2, 3]
    }

    # --- Helper functions ---
    def calculate_snr(signal_data, dark_data):
        signal = np.mean(signal_data)
        dark_mean = np.mean(dark_data)
        return (signal - dark_mean) / dark_mean if dark_mean != 0 else 0

    def calculate_group_snr(group):
        values = []
        for signal_col in group:
            dark_col = signal_dark_dictionary.get(signal_col)
            if signal_col in df.columns and dark_col in df.columns:
                values.append(calculate_snr(df[signal_col], df[dark_col]))
        return np.mean(values) if values else 0

    def calculate_nep(dark_cols):
        data = [df[col].dropna().values for col in dark_cols if col in df.columns]
        if not data:
            return 0
        return np.std(np.concatenate(data))

    # --- Compute NEP and SNR ---
    snr_short = calculate_group_snr([
        'LED_A_782_DET1', 'LED_A_801_DET1', 'LED_A_808_DET1',
        'LED_B_887_DET3', 'LED_B_848_DET3', 'LED_B_828_DET3'
    ])
    snr_mid = calculate_group_snr([
        'LED_A_782_DET2', 'LED_A_801_DET2', 'LED_A_808_DET2',
        'LED_B_887_DET2', 'LED_B_848_DET2', 'LED_B_828_DET2'
    ])
    snr_long = calculate_group_snr([
        'LED_A_782_DET3', 'LED_A_801_DET3', 'LED_A_808_DET3',
        'LED_B_887_DET1', 'LED_B_848_DET1', 'LED_B_828_DET1'
    ])
    nep_1 = calculate_nep(['LED_A_DARK_DET1', 'LED_B_DARK_DET1'])
    nep_2 = calculate_nep(['LED_A_DARK_DET2', 'LED_B_DARK_DET2'])
    nep_3 = calculate_nep(['LED_A_DARK_DET3', 'LED_B_DARK_DET3'])

    # --- SNR / NEP summary DataFrame ---
    summary_df = pd.DataFrame([
        ["Resampling", resample_note],
        ["NEP Detector 1 (mV)", round(nep_1, 4)],
        ["NEP Detector 2 (mV)", round(nep_2, 4)],
        ["NEP Detector 3 (mV)", round(nep_3, 4)],
        ["SNR Short Channel Average", round(snr_short, 4)],
        ["SNR Mid Channel Average", round(snr_mid, 4)],
        ["SNR Long Channel Average", round(snr_long, 4)],
    ], columns=["Metric", "Value"])

    # --- Filter & rename movement metrics ---
    movement_rows = []
    if movement_metrics and isinstance(movement_metrics, dict):
        rename_map = {
            "Total_Time_sec": "Total time of study",
            "Movement_Time_samples": "Total movement time",
            "Movement_Percentage": "Percentage of movement",
            "SNR_After_LED_A_Detector_1 + LED_B_Detector_3": "SNR after artifact removal short channel",
            "SNR_After_LED_A_Detector_2 + LED_B_Detector_2": "SNR after artifact removal mid channel",
            "SNR_After_LED_A_Detector_3 + LED_B_Detector_1": "SNR after artifact removal long channel"
        }
        for key, new_name in rename_map.items():
            if key in movement_metrics:
                movement_rows.append([new_name, movement_metrics[key]])
    if movement_rows:
        movement_df = pd.DataFrame(movement_rows, columns=["Metric", "Value"])
        # Append to summary
        summary_df = pd.concat([summary_df, movement_df], ignore_index=True)

    # --- Rename concentration columns ---
    conc_a_1_df.columns = ["LED-A_DET-1_HHb", "LED-A_DET-1_HbO2", "LED-A_DET-1_oxCCO"]
    conc_a_2_df.columns = ["LED-A_DET-2_HHb", "LED-A_DET-2_HbO2", "LED-A_DET-2_oxCCO"]
    conc_a_3_df.columns = ["LED-A_DET-3_HHb", "LED-A_DET-3_HbO2", "LED-A_DET-3_oxCCO"]
    conc_b_1_df.columns = ["LED-B_DET-1_HHb", "LED-B_DET-1_HbO2", "LED-B_DET-1_oxCCO"]
    conc_b_2_df.columns = ["LED-B_DET-2_HHb", "LED-B_DET-2_HbO2", "LED-B_DET-2_oxCCO"]
    conc_b_3_df.columns = ["LED-B_DET-3_HHb", "LED-B_DET-3_HbO2", "LED-B_DET-3_oxCCO"]
    df_sto2_A.columns = ["STO2_A"]
    df_sto2_B.columns = ["STO2_B"]
    df_sto2_dual.columns = ["STO2_AB"]

    # --- Combine all concentration and StO2 results ---
    result_df = pd.concat([
        conc_a_1_df, conc_a_2_df, conc_a_3_df,
        conc_b_1_df, conc_b_2_df, conc_b_3_df,
        df_sto2_A, df_sto2_B, df_sto2_dual
    ], axis=1)
    result_df.insert(0, "Date", date)
    result_df.insert(1, "Time", df["Time"])

    # --- Write to Excel ---
    with pd.ExcelWriter(output_path, engine='xlsxwriter') as writer:
        # Write summary with header
        summary_df.to_excel(writer, index=False, sheet_name='concentration', startrow=0, header=True)
        # Correct offset: len(summary_df) + 1 for header row
        offset = len(summary_df) + 1
        result_df.to_excel(writer, index=False, sheet_name='concentration', startrow=offset)

    return output_path

@app.callback(
    Output("download-conc-xlsx", "data"),
    Input("download_concentrations_excel_btn", "n_clicks"),
    State("concentrations", "data"),  # Use saved data
    prevent_initial_call=True
)
def download_concentration_excel(n_clicks, conc_data):
    if not n_clicks or not conc_data or "excel_path" not in conc_data:
        raise PreventUpdate

    excel_path = conc_data["excel_path"]

    if not os.path.exists(excel_path):
        return html.Div("❌ Excel file not found for download.")

    return dcc.send_file(excel_path)

@app.callback(
    Output("download-resampled-conc-xlsx", "data"),
    Input("download_resampled_concentrations_btn", "n_clicks"),
    State("concentrations", "data"),  # Use saved data
    prevent_initial_call=True
)
def download_resampled_concentration_excel(n_clicks, conc_data):
    if not n_clicks or not conc_data or "excel_path" not in conc_data:
        raise PreventUpdate
    
    excel_path = conc_data["excel_path"]
    if not os.path.exists(excel_path):
        return html.Div("❌ Excel file not found for download.")
    
    try:
        # Read header rows (0–13)
        header_part = pd.read_excel(excel_path, header=None, nrows=14)
        
        # Update the resampling status in row 2, column 2 (index [1, 1])
        header_part.iloc[1, 1] = "Resampled 1Hz"
        
        # Read data starting from row 15 (header row index = 14)
        df = pd.read_excel(excel_path, header=14)
        
        # Identify Date and Time columns
        date_col, time_col = None, None
        for col in df.columns:
            name = str(col).lower()
            if "date" in name:
                date_col = col
            elif "time" in name:
                time_col = col
        
        if date_col is None or time_col is None:
            return html.Div("❌ Missing 'Date' or 'Time' column in Excel file.")
        
        # Combine Date and Time into a single datetime column
        df["DateTime"] = pd.to_datetime(
            df[date_col].astype(str) + " " + df[time_col].astype(str),
            errors="coerce"
        )
        df = df.dropna(subset=["DateTime"])
        
        if df.empty:
            return html.Div("❌ No valid datetime data in Excel file.")
        
        # Group by second (ignore milliseconds)
        df["Time_Second"] = df["DateTime"].dt.floor("S")
        df_grouped = df.groupby("Time_Second").mean(numeric_only=True).reset_index()
        
        # Split DateTime back into separate Date and Time columns
        df_grouped["Date"] = df_grouped["Time_Second"].dt.date
        df_grouped["Time"] = df_grouped["Time_Second"].dt.time
        df_grouped = df_grouped.drop(columns=["Time_Second"])
        
        # Reorder columns to match original order (Date, Time first)
        cols = ["Date", "Time"] + [col for col in df_grouped.columns if col not in ["Date", "Time"]]
        df_grouped = df_grouped[cols]
        
        # Create temporary resampled file
        resampled_path = excel_path.replace(".xlsx", "_resampled.xlsx")
        
        with pd.ExcelWriter(resampled_path, engine="openpyxl") as writer:
            # Write header rows first
            header_part.to_excel(writer, index=False, header=False)
            # Then write resampled data immediately after
            df_grouped.to_excel(writer, index=False, startrow=14)
        
        return dcc.send_file(resampled_path)
    
    except Exception as e:
        return html.Div(f"❌ Error resampling file: {str(e)}")

#=======================Upload to cloud========================================
# AWS S3 client setup

# ======================= Bucket Mapping =========================
bucket_map = {
    'upload-raw': '***',
    'upload-concentration': '***',
    'upload-ctg': '***',
}

# ======================= Modal Visibility Toggle =========================
@callback(
    Output('upload-modal', 'style'),
    Input('upload-cloud-button', 'n_clicks'),
    Input('close-modal', 'n_clicks'),
    State('upload-modal', 'style'),
    prevent_initial_call=True
)
def toggle_modal(open_clicks, close_clicks, current_style):
    if ctx.triggered_id == 'upload-cloud-button':
        return {**current_style, 'display': 'flex'}
    elif ctx.triggered_id == 'close-modal':
        return {**current_style, 'display': 'none'}
    return current_style

# ======================= Show Selected File Names =========================
@callback(Output('filename-raw', 'children'), Input('upload-raw', 'filename'))
def show_raw_filename(filename):
    return f"File selected: {filename}" if filename else ""

@callback(Output('filename-concentration', 'children'), Input('upload-concentration', 'filename'))
def show_conc_filename(filename):
    return f"File selected: {filename}" if filename else ""

@callback(Output('filename-ctg', 'children'), Input('upload-ctg', 'filename'))
def show_ctg_filename(filename):
    return f"File selected: {filename}" if filename else ""

if __name__ == '__main__':
    app.run(debug=False, port=8052)