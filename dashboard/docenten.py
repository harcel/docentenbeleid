import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# Code for processing the docentendata such that plots below can be easily made.
# Functions appear here i the same order as in the notebook


def hash_nr(df, columns):
    """Hash a column using md5.
    If columns is a list, they're all done,
    if it's a string, taht column is hashed.

    The column will be converted to strings first, otherwise the hash is identical.

    The same DataFrame will be returned with hashed columns
    """

    if type(columns) == str:
        df[columns] = df[columns].apply(str).apply(hash)
    elif type(columns) == list:
        for col in columns:
            df[col] = df[col].apply(str).apply(hash)
    else:
        print("Don't recognize the type of columns, nothing is hashed")

    return df


def preprocess(df, faculteiten=["FGw", "FMG", "FdR", "FNWI", "FEB"]):
    # General preprocessing that always happens.
    df = df.rename(columns={"UvA personeelsnummer": "persnr"})

    ### Voor Rechten: PPLE eruit ###############
    # De data heeft 3 niveaus voor de orgnaisatie:
    # faculteit, WP faculteit en dan de afdelingen.
    # Mensen komen voor in alle lagen. Veredrop filteren
    # we alleen op faculteitsniveau zodat iedereen 1x voorkomt.
    # Voor rechten gebruiken we de lagere lagen om PPLE eruit te kunnen gooien:
    # - Verwijder hoge niveau rechten en de lage-niveau regels met PPLE
    # - Hernoem alle andere lage niveaus naar topniveau,
    #   zodat later bij de selectie al deze mensen blijven.

    if "PPLE" in faculteiten:
        # Voor PPLE apart in de output
        df.replace("Afd. PPLE", "PPLE", inplace=True)

    if "FdR" in faculteiten:
        # Rechten is een geval apart: PPLE moet eruit
        rechten = [
            "Afd. Privaatrecht",
            "Afd.Int./Eur.Recht",
            "wp afd. Alg. Recht",
            "wp afd. Publiekrecht",
        ]

        # Deze regels eruit, zodat de lager-niveau regels zonder PPLE hernoemd kan worden
        df = df[df.Organisatie != "FdR"]
        df.replace(rechten, "FdR", inplace=True)

    df = df[df["Organisatie"].isin(faculteiten)]

    # Hernoem Bezoldigd en UItbreiding naar Tijdelijk en Vast.
    df = df.replace(["Bezoldigd", "Uitbreiding"], ["Tijdelijk", "Vast"])
    # Tel FTEs per "omvang dienstverband" bij elkaar op,
    # nansum, want anders wordt x+NaN = NaN, nu x+NaN = x
    df = df.groupby(
        [
            "Organisatie",
            "Kalenderjaar",
            "Onderwijskwalificatie",
            "Dienstverband",
            "Functie",
            "persnr",
        ],
        as_index=False,
    ).agg(np.nansum)

    # Naar long format waarin alle maanden voorkomen,
    # maak daar integers van en construeer kwartalen
    df_long = pd.melt(
        df,
        id_vars=[
            "Organisatie",
            "Kalenderjaar",
            "Onderwijskwalificatie",
            "Dienstverband",
            "Functie",
            "persnr",
        ],
        value_vars=[
            "01",
            "02",
            "03",
            "04",
            "05",
            "06",
            "07",
            "08",
            "09",
            "10",
            "11",
            "12",
        ],
        var_name="maand",
        value_name="fte",
    )
    df_long["maand"] = df_long["maand"].astype(int)

    # Onderwijskwalificatie aggregeren naar hoogste niveau,
    # FTEs optellen over de kwalificaties
    df_long.replace("Geen", "AAGeen", inplace=True)  # (voor aggregatie, zie onder)
    df_long = df_long.groupby(
        ["Organisatie", "Functie", "persnr", "Kalenderjaar", "maand", "Dienstverband"],
        as_index=False,
    ).agg({"Onderwijskwalificatie": "max", "fte": "sum"})
    df_long.replace("AAGeen", "Geen", inplace=True)

    kwartaal = {
        1: "Q1",
        2: "Q1",
        3: "Q1",
        4: "Q2",
        5: "Q2",
        6: "Q2",
        7: "Q3",
        8: "Q3",
        9: "Q3",
        10: "Q4",
        11: "Q4",
        12: "Q4",
    }
    df_long["kwartaal"] = df_long.maand.map(kwartaal)
    df_long = df_long.dropna()  # Many NaN FTE, meaning 0.
    # Onbekende dienstverbanden, en maanden zonder dienstbetrekking eruit
    # Alleen precies 0 eruit, soms negatief = correctie op ander dienstverband?
    df_long = df_long[((df_long.fte != 0) & (df_long.Dienstverband != "Onbekend"))]

    df_long["Datum"] = (
        df_long["Kalenderjaar"].astype(str) + " " + df_long["kwartaal"].astype(str)
    )

    df = df_long.sort_values(
        ["Organisatie", "persnr", "Functie", "Kalenderjaar", "maand"]
    )

    return df


def perc_vast_FTE(df, functie="Docent 4", plot=True, mindate="2021 Q1"):
    """Prepare data for a specific plot:
    Percentage "vast" of "functie", over time in 2021-22
    Based on FTEs
    Set plot=False als je alleen data wilt, geen plot.
    mindate is de minimale datum in de resultaten en plot
    """

    # tel het aantal docenten 4 per type dienstverband per kwartaal (en per jaar en per faculteit)
    df = df[df.Functie == functie]
    # FTEs optellen voor verschillende mensen, maar middelen over de drie maanden.
    df_kwart_mean_person = df.groupby(
        ["Organisatie", "Datum", "Dienstverband", "persnr"], as_index=False
    )["fte"].mean()
    df_kwart_sum = (
        df_kwart_mean_person.groupby(
            ["Organisatie", "Datum", "Dienstverband"], as_index=False
        )["fte"]
        .sum()
        .reset_index()
    )

    ## Per organisatie, per kwartaal, per Dienstverband ...
    # tellen we nu FTEs op per dienstverband.
    df_pivot = df_kwart_sum.pivot(
        index=["Organisatie", "Datum"], columns="Dienstverband", values="fte"
    )
    # Als het kwartaal niet voorkomt zijn er kennelijk 0 mensen:
    df_pivot["Tijdelijk"].replace(np.nan, 0, inplace=True)
    df_pivot["Vast"].replace(np.nan, 0, inplace=True)
    # Totaal is som vast en tijdelijk (let op caveats boven)
    df_pivot["Totaal"] = df_pivot["Tijdelijk"] + df_pivot["Vast"]

    # Fracties tijdelijk en vast
    df_pivot["fractie vast contract"] = df_pivot["Vast"] / (df_pivot["Totaal"])
    df_pivot["fractie tijdelijk contract"] = df_pivot["Tijdelijk"] / (
        df_pivot["Totaal"]
    )
    df_sorted = df_pivot.sort_values(["Organisatie", "Datum"]).reset_index()

    # Maak een zinnig datumkolom en percentages
    df_sorted["Percentage met Vast contract"] = df_sorted["fractie vast contract"] * 100
    df_sorted["Percentage met Tijdelijk contract"] = (
        df_sorted["fractie tijdelijk contract"] * 100
    )

    # Alleen relevante tijdspanne
    # df_sorted = df_sorted[df_sorted.Datum >= mindate]

    if plot:
        plot_pvast(df_sorted, functie=functie)

    return df_sorted


def perc_vast_HC(df, functie="Docent 4", plot=True, mindate="2021 Q1"):
    """Prepare data for a specific plot:
    Percentage "vast" of "functie", over time in 2021-22
    Based on headcount.
    Set plot=False als je alleen de df wilt, zonder plot.
    mindate is de minimale datum in de resultaten en plot
    """
    df = df[df.Functie == functie]
    df_kwart_count = df.groupby(
        ["Organisatie", "Datum", "Dienstverband"], as_index=False
    )["persnr"].nunique()

    ## Per organisatie, per kwartaal, per Dienstverband ...
    # tellen we nu FTEs op per dienstverband.
    df_pivot = df_kwart_count.pivot(
        index=["Organisatie", "Datum"], columns="Dienstverband", values="persnr"
    )
    # Als het kwartaal niet voorkomt zijn er kennelijk 0 mensen:
    df_pivot["Tijdelijk"].replace(np.nan, 0, inplace=True)
    df_pivot["Vast"].replace(np.nan, 0, inplace=True)
    # Totaal is som vast en tijdelijk (let op caveats boven)
    df_pivot["Totaal"] = df_pivot["Tijdelijk"] + df_pivot["Vast"]

    # Fracties tijdelijk en vast
    df_pivot["fractie vast contract"] = df_pivot["Vast"] / (df_pivot["Totaal"])
    df_pivot["fractie tijdelijk contract"] = df_pivot["Tijdelijk"] / (
        df_pivot["Totaal"]
    )
    df_sorted = df_pivot.sort_values(["Organisatie", "Datum"]).reset_index()

    # Maak percentages
    df_sorted["Percentage met Vast contract"] = df_sorted["fractie vast contract"] * 100
    df_sorted["Percentage met Tijdelijk contract"] = (
        df_sorted["fractie tijdelijk contract"] * 100
    )

    # df_sorted = df_sorted[df_sorted.Datum >= mindate]

    if plot:
        plot_pvast_hc(df_sorted, functie=functie)

    return df_sorted


def tijdelijk_vast(df, functie="Docent 4", plot=True):
    """Prepare data for a specific plot:
    Aantal mensen in "functie" die van tijdelijk naar vast is gegaan is
    Based on headcount.
    Set plot=False als je alleen de df wilt, zonder plot.
    mindate is de minimale datum in de resultaten en plot
    """
    df = df[df.Functie == functie]

    # Laatste tijdelijk en eerste vast
    df_tijdelijk = (
        df[df.Dienstverband == "Tijdelijk"]
        .groupby(["Organisatie", "persnr"], as_index=False)
        .Datum.max()
    )
    df_vast = (
        df[df.Dienstverband == "Vast"]
        .groupby(["Organisatie", "persnr"], as_index=False)
        .Datum.min()
    )

    # df_tijdelijk.rename(columns={'Datum':'Laatste kwartaal tijdelijk'}, inplace=True)
    df_vast.rename(columns={"Datum": "Eerste kwartaal vast"}, inplace=True)

    df_tv = pd.merge(df_tijdelijk, df_vast, how="inner")

    df_tv = df_tv.groupby(["Organisatie", "Datum"], as_index=False).persnr.nunique()
    df_tv.rename(columns={"persnr": "# naar vast"}, inplace=True)

    # Voeg ook totaal aantal docenten toe ter vergelijking
    tot = (
        df[df.Dienstverband == "Tijdelijk"]
        .groupby(["Organisatie", "Datum"], as_index=False)
        .persnr.nunique()
    )
    tot.rename(columns={"persnr": f"{functie}, Tijdelijk"}, inplace=True)
    df_tv = tot.merge(df_tv, how="left")
    df_tv.replace(np.nan, 0, inplace=True)

    if plot:
        plot_vasttijdelijk(df_tv, functie=functie)

    return df_tv


def promotie(df, van="Docent 4", naar="Docent 3", plot=True, mindate="2020 Q1"):
    """Script die aantallen en percentages uit de Functie='van' groep, naar de Functie='naar' groep bepaalt.
    Van en naar geldt alleen binnen dezelfde Organisatie.
    Set plot=False als je alleen data en geen plot wilt.
    mindate is de minimale datum die in de resulterende data en plot voorkomt.
    """
    df_van = df[df.Functie == van]
    df_naar = df[df.Functie == naar]

    # Laatste kwartaal in 'van' en eerste in 'naar'
    df_goodbye = df_van.groupby(["Organisatie", "persnr"], as_index=False).Datum.max()
    df_hello = df_naar.groupby(["Organisatie", "persnr"], as_index=False).Datum.min()

    df_goodbye.rename(columns={"Datum": f"Laatste kwartaal {van}"}, inplace=True)
    df_hello.rename(columns={"Datum": f"Eerste kwartaal {naar}"}, inplace=True)

    df_promotie = pd.merge(
        df_goodbye, df_hello, how="inner", on=["Organisatie", "persnr"]
    )

    # Aantallen van/naar per kwartaal en aantallen promoties per kwartaal
    df_tot = df_van.groupby(["Organisatie", "Datum"], as_index=False).persnr.nunique()
    df_proms = df_promotie.groupby(
        ["Organisatie", f"Laatste kwartaal {van}"], as_index=False
    ).persnr.nunique()

    df_tot.rename(columns={"persnr": f"{van}"}, inplace=True)
    df_proms.rename(
        columns={"persnr": "Omzettingen", f"Laatste kwartaal {van}": "Datum"},
        inplace=True,
    )
    df_promoties = pd.merge(df_tot, df_proms, how="left", on=["Organisatie", "Datum"])
    df_promoties.replace(np.nan, 0, inplace=True)
    df_promoties["Aantal geen promotie"] = (
        df_promoties[f"{van}"] - df_promoties["Omzettingen"]
    )
    df_promoties["Percentage Omzettingen"] = (
        df_promoties["Omzettingen"] / df_promoties[f"{van}"] * 100
    )

    # df_promoties = df_promoties[df_promoties.Datum >= mindate]

    if plot:
        plot_promoties(df_promoties, van=van, naar=naar)

    return df_promoties


def fte_pp(df, functie="Docent 4", plot=True, mindate="2020 Q1"):
    """FTE per persoon, voor functie
    Gebruikt de FTEs en de HCs van de functies hierboven. Let op: deze worden opnieuw berekend!
    """
    headcount = perc_vast_HC(df, functie=functie, plot=False)
    fte = perc_vast_FTE(df, functie=functie, plot=False)

    headcount.rename(
        columns={"Vast": "vast_hc", "Tijdelijk": "tijdelijk_hc", "Totaal": "totaal_hc"},
        inplace=True,
    )
    headcount = headcount[
        ["Organisatie", "Datum", "vast_hc", "tijdelijk_hc", "totaal_hc"]
    ]
    fte = fte.merge(headcount, on=["Organisatie", "Datum"])

    fte["FTE_pp_vast"] = fte.Vast / fte.vast_hc
    fte["FTE_pp_tijdelijk"] = fte.Tijdelijk / fte.tijdelijk_hc

    # fte = fte[fte.Datum >= mindate]

    if plot:
        plot_fte_pp(fte, functie=functie)

    return fte


def fte_dist(df, functie="Docent 4", plot=True, mindate="2020 Q1"):
    """De verdeling van de FTEs per persoon, dus zonder aggregatie"""
    fte_pp = (
        df[df.Functie == functie]
        .groupby(["Organisatie", "persnr", "Datum", "Dienstverband"], as_index=False)
        .fte.mean()
    )

    # fte_pp = fte_pp[fte_pp.Datum >= mindate]

    if plot:
        plot_fte_dist(fte_pp, functie=functie)

    return fte_pp


def percentages_docenten(
    df,
    functies=["Docent 1", "Docent 2", "Docent 3", "Docent 4"],
    plot=True,
    mindate="2020 Q1",
):
    """Percentages van Docenten 4, 3, 2, 1 over de tijd
    voor alle faculteiten in df"""

    # Gebruik voorgaande functionaliteit, ook al duurt dat wat langer
    all_functies = pd.DataFrame()
    for functie in functies:
        df_functie = perc_vast_HC(df, functie=functie, plot=False, mindate=mindate)
        df_functie["Functie"] = functie
        all_functies = all_functies.append(df_functie)

    aantallen = all_functies.groupby(["Organisatie", "Datum"], as_index=False)[
        ["Tijdelijk", "Vast", "Totaal"]
    ].sum()
    aantallen.rename(
        columns={
            "Tijdelijk": "Totaal tijdelijk",
            "Vast": "Totaal vast",
            "Totaal": "Totaal allen",
        },
        inplace=True,
    )

    all_functies = all_functies[
        ["Organisatie", "Datum", "Functie", "Tijdelijk", "Vast", "Totaal"]
    ].merge(aantallen, how="left", on=["Organisatie", "Datum"])

    all_functies["Percentage tijdelijk"] = (
        all_functies["Tijdelijk"] / all_functies["Totaal tijdelijk"] * 100
    )
    all_functies["Percentage vast"] = (
        all_functies["Vast"] / all_functies["Totaal vast"] * 100
    )
    all_functies["Percentage allen"] = (
        all_functies["Totaal"] / all_functies["Totaal allen"] * 100
    )

    if plot:
        plot_percentages_docenten(all_functies, mindate=mindate, subpop=None)

    return all_functies


################################################################

######## CODE FOR PLOTS ########################################

################################################################


def plot_pvast(df, functie="Docent 4"):
    fig = px.line(df, x="Datum", y="Percentage met Vast contract", color="Organisatie")
    fig.update_layout(title=f"Percentage {functie} met vast contract op basis van FTE")
    fig.update_layout(
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=np.sort(np.unique(df["Datum"])),
            title="Datum",
        ),
        # autosize=True,
        # width=600,
    )
    fig.update_yaxes(range=[0, 100])
    # fig.show()
    return fig


def plot_pvast_hc(df, functie="Docent 4"):
    fig = px.line(df, x="Datum", y="Percentage met Vast contract", color="Organisatie")
    fig.update_layout(
        title=f"Percentage {functie} met vast contract op basis van head count"
    )
    fig.update_layout(
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=np.sort(np.unique(df["Datum"])),
            title="Datum",
        ),
        # autosize=True,
        # width=600,
    )
    fig.update_yaxes(range=[0, 100])
    # fig.show()
    return fig


def plot_vasttijdelijk(df, functie="Docent 4"):
    fig = px.bar(
        df,
        x="Datum",
        y=[f"{functie}, Tijdelijk", "# naar vast"],
        facet_col="Organisatie",
        labels={
            "Aantal": "",
            "variable": "",
            "Organisatie=": "",
            "Datum": "",
            "value": "Aantal",
        },
        barmode="overlay",
        opacity=1,
    )
    fig.update_layout(title=f"Aantal omzetting tijdelijk naar vast {functie}")
    fig.update_layout(
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=np.sort(np.unique(df["Datum"])),
        ),
        # autosize=True,
    )
    # fig.update_traces(opacity=1.0)
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    # fig.show()
    return fig


def plot_4vs3(df4, df3):
    # Prep data frames and combine
    df4 = df4.rename(columns={"Totaal": "Aantal Docenten 4"})[
        ["Organisatie", "Datum", "Aantal Docenten 4"]
    ]
    df3 = df3.rename(columns={"Totaal": "Aantal Docenten 3"})[
        ["Organisatie", "Datum", "Aantal Docenten 3"]
    ]
    df = pd.merge(df4, df3)

    fig = px.bar(
        df,
        x="Datum",
        y=[f"Aantal Docenten 4", "Aantal Docenten 3"],
        facet_col="Organisatie",
        labels={"value": "Aantal", "variable": "", "Organisatie=": ""},
    )
    fig.update_layout(title=f"Aantallen Docenten 4 en 3")
    fig.update_layout(
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=np.sort(np.unique(df["Datum"])),
        ),
        # autosize=True,
    )
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    # fig.show()
    return fig


def plot_promoties(df, van="Docent 4", naar="Docent 3"):
    fig = px.bar(
        df,
        x="Datum",
        y=[f"{van}", "Omzettingen"],
        facet_col="Organisatie",
        labels={"value": "Aantal", "variable": "", "Organisatie=": "", "Datum": ""},
        barmode="overlay",
        opacity=1,
    )
    fig.update_layout(title=f"Aantallen Omzettingen van {van} naar {naar}")
    fig.update_layout(
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=np.sort(np.unique(df["Datum"])),
        ),
        # autosize=True,
    )
    # fig.update_traces(opacity=1.0)
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    # fig.show()
    return fig


def plot_fte_pp(df_sorted, functie="Docent 4"):
    fig = px.line(df_sorted, x="Datum", y="FTE_pp_vast", color="Organisatie")
    # fig.update_layout(yaxis_range=[0,100], title='percentage vast contractentage docenten 4 met vast contract')
    fig.update_layout(title=f"Aantal FTE per persoon, {functie} met vast contract")
    fig.update_layout(
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=np.sort(np.unique(df_sorted["Datum"])),
            title="Datum",
        ),
        yaxis=dict(title="FTE per persoon, vast contract"),
        # autosize=True,
    )
    fig.show()

    fig = px.line(df_sorted, x="Datum", y="FTE_pp_tijdelijk", color="Organisatie")
    # fig.update_layout(yaxis_range=[0,100], title='percentage vast contractentage docenten 4 met vast contract')
    fig.update_layout(title=f"Aantal FTE per persoon, {functie} met tijdelijk contract")
    fig.update_layout(
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=np.sort(np.unique(df_sorted["Datum"])),
            title="Datum",
        ),
        yaxis=dict(title="FTE per persoon, tijdelijk contract"),
        # autosize=True,
    )
    # fig.show()
    return fig


def plot_fte_dist(df_sorted, functie="Docent 4"):
    fig = px.box(
        df_sorted,
        x="Organisatie",
        y="fte",
        color="Datum",
        facet_col="Dienstverband",
        labels={"Dienstverband=": "Dienstverband: ", "Organisatie": "", "Datum": ""},
    )
    fig.update_layout(title=f"Aantal FTE per persoon, {functie}")
    fig.update_layout(
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=np.sort(np.unique(df_sorted["Datum"])),
            title=None,
        ),
        yaxis=dict(title="FTE per persoon"),
        # autosize=True,
    )

    return fig


def plot_percentages_docenten(df, subpop=None):
    if subpop:
        if subpop == "Vast":
            yprop = "Percentage vast"
        elif subpop == "Tijdelijk":
            yprop = "Percentage tijdelijk"
        else:
            raise ValueError("subpop should be Vast or Tijdelijk")
    else:
        yprop = "Percentage allen"

    orgs_here = np.unique(df.Organisatie)
    all_orgs = ["FEB", "FGw", "FMG", "FNWI", "FdR", "AUC", "PPLE"]

    fig = px.bar(
        df,
        x="Datum",
        y=yprop,
        color="Functie",
        facet_col="Organisatie",
        category_orders={
            "Functie": ["Docent 4", "Docent 3", "Docent 2", "Docent 1"],
            "Organisatie": [k for k in all_orgs if k in orgs_here],
        },
        labels={"Datum": ""},
    )
    fig.update_layout(title=f"Verdeling docenten, ongeacht dienstverband")
    fig.update_layout(
        xaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=np.sort(np.unique(df["Datum"])),
        ),
        yaxis=dict(title="Percentage"),
        # autosize=True,
    )
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"}, legend={"traceorder": "reversed"}
    )
    # fig.show()
    return fig
