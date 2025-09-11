import logging
import polars as pl

from src.brostar_api_requests.brostar_api_requests import (
    delete_invalid_upload_tasks,
    bulk_gmw_construction_request_xml_extract
)

def convert_excel(input_path):
    # set excel output path
    output_path = input_path[:-5] + "_out.xlsx"

    df = pl.read_excel(input_path, sheet_id=1)
    print(df.head(10))
    kolomnamen = [
        "Putnaam",
        "Filternummer",
        "X-coordinaat(RD)",
        "Y-coordinaat(RD)",
        "Coordinatenstelsel",
        "Methode Coordinatenbepaling",
        "Maaiveldpositie (m+NAP)",
        "Methode Maaiveldpositiebepaling",
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
        pl.col("name_by_ref_well").fill_null(strategy="forward").alias("Putnaam"),
        pl.col("tubeNumber").alias("Filternummer"),
        pl.col("x").alias("X-coordinaat(RD)"),
        pl.col("y").alias("Y-coordinaat(RD)"),
        pl.lit("RD").alias("Coordinatenstelsel"),
        pl.lit("onbekend").alias("Methode Coordinatenbepaling"),
        pl.col("MV").alias("Maaiveldpositie (m+NAP)"),
        pl.lit("onbekend").alias("Methode Maaiveldpositiebepaling"),

        # als 'datum_naar_bro' aanwezig is de tijd droppen om formaat van {YYYY-MM-DD 00:00:00} naar {yyyy-mm-dd} te krijgen
        # als alleen jaar of jaar maand is opgegeven, dan blijft die staan,
        # Als null, dan leeg laten
        pl.when(pl.col("datum_naar_bro").is_null())
        .then(pl.lit(""))
        .otherwise(
            pl.col("datum_naar_bro")
            .str.replace(" 00:00:00", "")
        )
        .alias("Inrichtingsdatum"),
                
        pl.lit("").alias("OnvolledigeDatum"),
        pl.lit("onbekend").alias("Kwaliteitsnorminrichting"),
        pl.lit("").alias("Kaartblad"),
        pl.lit("").alias("NITG-code"),
        pl.lit("onbekend").alias("Beschermconstructie"),
        pl.lit("publiekeTaak").alias("Kader aanlevering"),
        pl.lit("stand").alias("Initiële functie"),
        pl.lit("ja").alias("Maaiveld stabiel"),
        pl.lit("stabielNAP").alias("Putstabiliteit"),
        pl.lit("standaardbuis").alias("BuisType"),
        pl.lit("gebruiksklaar").alias("Buis status"),
        pl.lit("").alias("Buis in gebruik"),
        pl.lit("ja").alias("Drukdop"),

        # Voorzien van zandvang: ja als Lzvang niet null, anders nee
        pl.when(pl.col("Lzvang").is_not_null())
        .then(pl.lit("ja"))
        .otherwise(pl.lit("nee"))
        .alias("Voorzien van zandvang"),

        pl.col("Lzvang").alias("Zandvanglengte (meters)"),
        pl.lit("").alias("Buisdeel ingeplaatst"),
        pl.lit(25).alias("Diameter bovenkantbuis (mm)"),
        pl.lit("nee").alias("Variabele diameter"),
        pl.lit("onbekend").alias("MethodePositiebepalingBovenkantbuis"),
        pl.col("BKB").cast(pl.Float64, strict=False).alias("Positie bovenkantbuis (m+NAP)"),

        # Lengte stijgbuisdeel: Lbuis - Lzvang - 1
        (
            pl.when(pl.col("Lbuis").is_null())
            .then(None)
            .otherwise(
                pl.col("Lbuis").cast(pl.Float64)
                -
                pl.when(pl.col("Lzvang").is_null())
                .then(0.0)  # vervang null bij Lzvang door 0
                .otherwise(pl.col("Lzvang").cast(pl.Float64))
                - 1
            )
        ).alias("Lengte stijgbuisdeel (meters)"),

        pl.lit(1).alias("Filterlengte (meters)"),
        pl.lit("onbekend").alias("Materiaal peilbuis"),
        pl.lit("onbekend").alias("Kousmateriaal"),
        pl.lit("onbekend").alias("Aanvulmaterial buis"),
        pl.lit("onbekend").alias("Lijm"),
    ]).select(kolomnamen)

    df_out.write_excel(output_path)
    return output_path


def main():
    # file_path = r"C:\Users\steven.hosper\Downloads\duplicates_ids.xlsx"
    # correct_bulk_gld(file_path)

    # delete_invalid_upload_tasks()

    # file_path = r"C:\Users\steven.hosper\Desktop\PythonPackages\BrostarAPI\20250425_move_wells.xlsx"
    input_path = r"C:\Users\sven.vanos\Documents\20250162 Scheldestromen BRO levering\result_locs_to_create_gmw_snapshot.xlsx"
    converted_path = convert_excel(input_path)
    bulk_gmw_construction_request_xml_extract(excel_file=converted_path, kvk="51640813")

    # BrabantWater corrections
    # file_path = r"C:\Users\steven.hosper\Downloads\BROLab_ImportExcel.xlsx"
    # bulk_gmw_construction_request(file_path, "17278718")

    # Gelderland Corrections
    # file_path = r"C:\Users\steven.hosper\Downloads\freatische_filter_gmw_ids.xlsx"
    # bulk_gmw_tubenumber_correction_request(file_path, "51468751")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
