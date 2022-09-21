# Run this app with `python simple_app.py` and
# visit http://127.0.0.1:8050/ in your web browser.

from turtle import color
from dash import Dash, html, dcc, Output, Input
import dash_bootstrap_components as dbc
import dash_daq as daq
import plotly.express as px
import pandas as pd
import numpy as np
import docenten as d
import warnings

warnings.filterwarnings("ignore")


# Run this app with `python simple_app.py` and
# visit http://127.0.0.1:8051/ in your web browser.

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
)
# server = app.server()

# Data stuff first, app stuff below.
# assume you have a "long-form" data frame
# Data is read in after preprocessing and hashing.
df = pd.read_csv("data/Docenten_2020-2022_hashed.csv")

# Mapping voor promoties
prom_map = {
    "Docent 4": "Docent 3",
    "Docent 3": "Docent 2",
    "Docent 2": "Docent 1",
    "Docent 1": "Docent 1",
}

# Function to filter on years, while date is in quarters.
def filterdatum(plot_df, jaren):
    Qjaren = [f"{jaren[0]} Q1", f"{jaren[1]} Q4"]
    plot_df = plot_df[((plot_df.Datum >= Qjaren[0]) & (plot_df.Datum <= Qjaren[1]))]
    return plot_df


# set some parameters
navbar_height = "8rem"
sidebar_width = "24rem"


# see https://plotly.com/python/px-arguments/ for more options
# NAVBAR STYLE
NAVBAR_STYLE = {
    "position": "fixed",
    "top": 0,
    "left": 0,
    "right": 0,
    "height": navbar_height,
    "padding": "2rem 1rem",
    "background-color": "#001324",
}

# the style arguments for the sidebar. We use position:fixed and a fixed width
SIDEBAR_STYLE = {
    "position": "fixed",
    "top": navbar_height,
    "left": 0,
    "bottom": 0,
    "width": sidebar_width,
    "background-color": "#f8f9fa",
    "padding": "4rem 1rem 2rem",
}

# the styles for the main content position it to the right of the sidebar and
# add some padding.
CONTENT_STYLE = {
    "margin-right": "2rem",
    "padding": "2rem 1rem",
    "margin-top": navbar_height,
    "margin-left": sidebar_width,
}


# Create content

sidebar = html.Div(
    [
        html.H1("UvA Docentenbeleid"),
        html.Hr(),
        html.H5("Kies hier de populatie!"),
        dcc.Dropdown(
            id="Functie",
            value="Docent 4",
            options=[{"label": x, "value": x} for x in df.Functie.unique()],
            multi=False,
            optionHeight=75,
            style={"margin-bottom": "50px"},
        ),
        html.H5("Welk tijdvak wil je zien?"),
        dcc.RangeSlider(
            df.Kalenderjaar.min(),
            df.Kalenderjaar.max(),
            1,
            marks={
                i: f"{i}"
                for i in range(df.Kalenderjaar.min(), df.Kalenderjaar.max() + 1)
            },
            value=[2021, 2022],
            id="Jaarslider",
        ),
        html.Hr(),
        html.Div(
            "Dit dashboard bevat visualisaties ter monitoring van het docentenbeleid."
        ),
        html.Div(
            "Elk panel is interactief, klikken op items in de legenda geeft de mogelijkheid slechts een deel van de data weer te geven."
        ),
        html.Div(
            "De groep docenten waar het om gaat, zowel als de jaren die je wilt zien kies je hierboven."
        ),
        html.Div("De data is up-to-date t/m augustus 2022."),
        html.Div(
            "De bovenste panels gaan over de aard van het dienstverband en laten het percentage vaste dienstverbanden zien (links; met de switch kies je of je dit op basis van head count of FTE wil zien) en de omzetting van tijdelijk naar vast binnen de gekozen populatie (rechts)."
        ),
        html.Div(
            "De middelste panels gaan over omzettingen van een docentniveau naar het niveau erboven. Het linker panel is statisch, het rechter laat omzettingen zien van de gekozen populatie naar de populatie een niveau hoger."
        ),
        html.Div(
            "Het onderste panel laat de omvang van dienstverbanden zien in een boxplot. De balkjes geven aan waar de bulk van de docenten zit en het horizontale streepje daarin is de mediaan. Een vergroting van de contractomvang bij veel docenten uit zich dus als een verschuiving van de balkjes en horizontale lijntjes omhoog."
        ),
    ],
    style=SIDEBAR_STYLE,
    id="sidebar",
)

content = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(dcc.Graph(id="graph_vast")),
                        daq.BooleanSwitch(id="fte-hc-switch", label="Head count - FTE"),
                    ],
                    width=6,
                ),
                dbc.Col(html.Div(dcc.Graph(id="graph_tijdelijkvast")), width=6),
            ]
        ),
        html.Hr(),
        dbc.Row(
            [
                dbc.Col(html.Div(dcc.Graph(id="graph_alle_docenten")), width=6),
                dbc.Col(html.Div(dcc.Graph(id="graph_promotie")), width=6),
            ]
        ),
        html.Hr(),
        dbc.Row(
            dbc.Col(html.Div(dcc.Graph(id="graph_fte_dist")), width=12),
        ),
    ],
    style=CONTENT_STYLE,
    id="content",
)


# NAVBAR

UVA_LOGO = "https://bynder-public-eu-central-1.s3.amazonaws.com/media/9E3E0032-62BD-4694-A3CCB1BC17CA3CAF/FF64C5B0-5467-410C-A0F6132F87CC1FB1/webimage-AFB47F53-1DB5-4BB7-969667942DEA32B4.png"
# make a reuseable navitem for the different examples
nav_item = dbc.NavItem(dbc.NavLink("Link", href="#"))

NAVBAR = dbc.Navbar(
    [
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        [
                            html.A(
                                href="https://uva.nl",
                                children=[
                                    html.Img(
                                        src=UVA_LOGO, alt="UvA website", height="80px"
                                    )
                                ],
                            ),
                        ]
                    ),
                    width=3,
                ),
                dbc.Col(
                    html.H2("Advanced Analytics", style={"color": "#f8f9fa"}),
                    align="center",
                    width=8,
                ),
            ],
        ),
    ],
    color="dark",
    dark=True,
    # className="mb-5",
    style=NAVBAR_STYLE,
)


# HERE WE BUILT THE APP LAYOUT
app.layout = html.Div([sidebar, content, NAVBAR])  #


# any change to the input Fuel will call the update_figure function and return a figure with updated data
@app.callback(
    Output("graph_vast", "figure"),
    Output("graph_alle_docenten", "figure"),
    Output("graph_tijdelijkvast", "figure"),
    Output("graph_promotie", "figure"),
    Output("graph_fte_dist", "figure"),
    Input("Functie", "value"),
    Input("Jaarslider", "value"),
    Input("fte-hc-switch", "on"),
)
def update_figure_table(Functie, jaren, ftehc):
    # If no function selected, make it Docent 4
    if not Functie:
        Functie = "Docent 4"

    # Jaren pas filteren voor de plot, niet voor analyse!
    filtered_df = df[df.Functie == Functie]
    two_func_df = df[df.Functie.isin([Functie, prom_map[Functie]])]

    if ftehc:
        plot_df = d.perc_vast_FTE(filtered_df, functie=Functie, plot=False).pipe(
            filterdatum, jaren
        )
        fig_vast = d.plot_pvast(plot_df, functie=Functie)
    else:
        plot_df = d.perc_vast_HC(filtered_df, functie=Functie, plot=False).pipe(
            filterdatum, jaren
        )
        fig_vast = d.plot_pvast_hc(plot_df, functie=Functie)

    plot_df = d.percentages_docenten(df, plot=False).pipe(filterdatum, jaren)
    fig_alledocenten = d.plot_percentages_docenten(plot_df)

    plot_df = d.tijdelijk_vast(filtered_df, functie=Functie, plot=False).pipe(
        filterdatum, jaren
    )
    fig_tijdelijkvast = d.plot_vasttijdelijk(plot_df, functie=Functie)

    plot_df = d.promotie(
        two_func_df, van=Functie, naar=prom_map[Functie], plot=False
    ).pipe(filterdatum, jaren)
    fig_promotie = d.plot_promoties(plot_df, van=Functie, naar=prom_map[Functie])

    plot_df = d.fte_dist(df, functie=Functie, plot=False).pipe(filterdatum, jaren)
    fig_fte_dist = d.plot_fte_dist(plot_df, functie=Functie)

    return (
        fig_vast,
        fig_alledocenten,
        fig_tijdelijkvast,
        fig_promotie,
        fig_fte_dist,
    )


if __name__ == "__main__":
    app.run(debug=True, port=8051)
