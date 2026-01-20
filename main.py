import logging
import polars as pl

from src.brostar_api_requests.brostar_api_requests import (
    delete_invalid_upload_tasks,
    bulk_gmw_construction_request_xml_extract,
    bulk_gmw_construction_request
)

OMHUIZING_MAPPING = {
    "Gele straatpot": "potWaterdicht", # IMBRO
    "koker-kunststof": "KokerNietMetaal", # IMBRO
    "straatpot": "potWaterdicht", # IMBRO
    "Schutkoker": "koker", # IMBRO/A
    "Blauwe straatpot": "potWaterdicht", # IMBRO
    "koker-staal": "KokerMetaal", # IMBRO
    "anders": "onbekend", # IMBRO/A
    None: "onbekend", # IMBRO/A
}

def convert_excel(input_path):
    # set excel output path
    output_path = input_path[:-5] + "_out.xlsx"

    df = pl.read_excel(
        input_path,
        read_options={
            "header_row":2,
        })
    
    print(df.head(10))

    # print(df["MP-omhuizing"].unique())
    kolomnamen = [
        "Putnaam",
        "Filternummer",
        "X-coordinaat(RD)",
        "Y-coordinaat(RD)",
        "Coordinatenstelsel",
        "Method Coordinatenbepaling",
        "Maaiveldpositie (m+NAP)",
        "Method Maaiveldpositiebepaling",
        "Inrichtingsdatum",
        "OnvolledigeDatum",
        "Kwaliteitsnorminrichting",
        "Kaartblad",
        "NITG-code",
        "Beschermconstructie",
        "Kader aanlevering",
        "Initiële functie",
        "Maaiveld stabiel",
        "Putstabiliteit",
        "BuisType",
        "Buis status",
        "Buis in gebruik",
        "Drukdop",
        "Voorzien van zandvang",
        "Zandvanglengte (meters)",
        "Buisdeel ingeplaatst",
        "Diameter bovenkantbuis (mm)",
        "Variabele diameter",
        "MethodePositiebepalingBovenkantbuis",
        "Positie bovenkantbuis (m+NAP)",
        "Lengte stijgbuisdeel (meters)",
        "Filterlengte (meters)",
        "Materiaal peilbuis",
        "Kousmateriaal",
        "Aanvulmaterial buis",
        "Lijm"
    ]

    df_out = df.with_columns([
        # naam en filternummer misschien splitsen,
        # maar wat dan te doen met de coordinaten aangezien die bij elke buis uniek zijn.
        # Verder was 27-10 bepaald dat Jeroen misschien nieuwe naamgeving zou leveren
        # pl.when(pl.col("Naam").is_null())
        # .then(pl.col("MP-code"))
        # .otherwise(
        #     pl.col("Naam")
        # ).alias("Putnaam"),
        pl.col("MP-code").alias("Putnaam"),
        pl.lit(1).alias("Filternummer"),
        # _____________ navragen of losse putten zijn of losse peilbuizen in put
        # zijn losse potten

        pl.col("MP-Xwaarde").alias("X-coordinaat(RD)"),
        pl.col("MP-Ywaarde").alias("Y-coordinaat(RD)"),
        pl.lit("RD").alias("Coordinatenstelsel"),

        # uit mail:
        # RTKGPS0tot2cm, ik merk hierbij op dat de aanwezigheid van gebouwen maar ook bomen invloed hebben op de betrouwbaarheid
        # van de meting. Bij een meting vlakbij een gebouw of vlakbij bomen zijn er minder verbindingen met satellieten waardoor
        # de nauwkeurigheid afneemt.
        pl.lit("RTKGPS0tot2cm").alias("Method Coordinatenbepaling"),

        pl.col("PB-Mv").alias("Maaiveldpositie (m+NAP)"),

        # aanname op basis van Methode Coordinatenbepaling
        pl.lit("RKTGPS0tot4cm").alias("Method Maaiveldpositiebepaling"),

        # als 'MP-start' aanwezig is de tijd formatten naar yyyy-mm-dd
        # Als null, dan leeg laten
        pl.when(pl.col("MP-start").is_null())
        .then(pl.lit(""))
        .otherwise(
            pl.col("MP-start")
        )
        .alias("Inrichtingsdatum"),

        pl.lit("").alias("OnvolledigeDatum"),
        pl.lit("geen").alias("Kwaliteitsnorminrichting"), # aanname 
        pl.lit("").alias("Kaartblad"),
        pl.lit("").alias("NITG-code"),

        # mapping omhuizing types gedaan
        pl.col("MP-omhuizing")
        .replace_strict(OMHUIZING_MAPPING, default="onbekend")
        .alias("Beschermconstructie"),

        pl.lit("publiekeTaak").alias("Kader aanlevering"), # aanname
        pl.lit("stand").alias("Initiële functie"), # aanname
        pl.lit("ja").alias("Maaiveld stabiel"), # aanname
        pl.lit("stabielNAP").alias("Putstabiliteit"), # aanname, overgenomen van Scheldestromen
        pl.lit("standaardbuis").alias("BuisType"), # aanname
        pl.lit("gebruiksklaar").alias("Buis status"), # aanname
        pl.lit("ja").alias("Buis in gebruik"), # aanname, meetnetten zijn actief op één na
        pl.lit("nee").alias("Drukdop"), # aanname

        pl.lit("nee").alias("Voorzien van zandvang"), # uit overleg 27-10
        pl.lit("").alias("Zandvanglengte (meters)"), # leeg want overal geen zandvang
        pl.lit("").alias("Buisdeel ingeplaatst"), # aanname
        pl.when(pl.col("diameter peilbuis").is_null())
        .then(32) # uit mail 27-10
        .otherwise(
            pl.col("diameter peilbuis")
        ).alias("Diameter bovenkantbuis (mm)"), # 2024 buizen uit geleverde document proefboringen gehaald
        pl.lit("nee").alias("Variable diameter"), # aanname
        pl.lit("RTKGPS0tot4cm").alias("MethodePositiebepalingBovenkantbuis"), # aanname
        pl.col("PB-Bkpb").cast(pl.Float64, strict=False).alias("Positie bovenkantbuis (m+NAP)"),

        # zitten rare getallen tussen, ook ~ -3 meter, kan zijn dat het soms in mNAP gegeven is, staat volgende bij:
        # Bkf = Bovenkant filter
        # Afstand bovenkant peilbuis - bovenkant filter in m.
        # kan niet negatief zijn ----------> vragen aan Jeroen
        (pl.col("PB-Bkpb") - pl.col("PB-Bkf")).alias("Lengte stijgbuisdeel (meters)"),
        pl.col("PB-Fl").alias("Filterlengte (meters)"),

        pl.lit("pvc").alias("Materiaal peilbuis"), # uit mail 27-10
        pl.lit("onbekend").alias("Kousmateriaal"), # aanname
        pl.lit("boorgatmateriaal").alias("Aanvulmaterial buis"),
        pl.lit("geen").alias("Lijm"),
    ])

    df_out = df_out.select(kolomnamen)

    df_out.write_excel(output_path)
    return output_path


def main():
    # file_path = r"C:\Users\steven.hosper\Downloads\duplicates_ids.xlsx"
    # correct_bulk_ld(file_path)

    # delete_invalid_upload_tasks()

    input_path = r"C:\Users\sven.vanos\Documents\20250222 BRO Tynaarlo\Grondwatermeetnetoverzicht 19-11-2025\test.xlsx"
    output_path = convert_excel(input_path)
    bulk_gmw_construction_request(excel_file=output_path, kvk="01169292")
    # project nummer productie: 7293

    # BrabantWater corrections
    # file_path = r"C:\Users\steven.hosper\Downloads\BROLab_ImportExcel.xlsx"
    # bulk_gmw_construction_request(file_path, "17278718")

    # Gelderland Corrections
    # file_path = r"C:\Users\steven.hosper\Downloads\freatische_filter_gmw_ids.xlsx"
    # bulk_gmw_tubenumber_correction_request(file_path, "51468751")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
