from www.services import *
import pandas as pd


def get_data(input, database, df, reset_callback=None):
    """
    Handle the data upload and display process.
    
    Args:
        input: An object that provides user input methods.
        database: The name of the database.
        df: A DataFrame object to store the data.
        reset_callback: Function to call to reset analysis results (optional)
        
    Returns:
        A message indicating the status of the data upload.
    """
    file: list[FileInfo] | None = input.Dataset()
    
    if file is None:
        text = ui.h5("Please select a file to begin importing your data.")

    elif input.select() == "1A":
        ui.update_action_button("action_button_save", disabled=False)
        
        source = input.database()
        author = input.author()
        
        try:
            # Check if multiple files are selected
            if len(file) > 1:
                # Process multiple files
                json = process_multiple_files(file, source, author)
                df.set(pd.read_json(StringIO(json)))
                # Reset all analysis results when new dataset is loaded
                if reset_callback:
                    reset_callback()
                text = ui.p(
                    f"{database}'s files uploaded and processed successfully! "
                    f"{len(file)} files have been processed and combined. "
                    f"The dataset contains {df.get().shape[0]} rows and {df.get().shape[1]} columns."
                )
            else:
                # Process single file
                type = file[0]["name"]
                datapath = file[0]["datapath"]

                # Route the ETL-supported sources through the source-agnostic
                # pipeline (convert2df) so importing raw non-WoS data in the
                # dashboard actually exercises the ETL and standardizes it into
                # the 24-column WoS schema. Fall back to the legacy parser for
                # WoS, .bib, .zip, or any format the ETL extractor cannot read.
                ETL_SOURCES = {
                    "scopus": "SCOPUS",
                    "dimensions": "DIMENSIONS",
                    "pubmed": "PUBMED_FILE",
                    "lens": "LENS",
                    "cochrane": "COCHRANE",
                }
                used_etl = False
                if source in ETL_SOURCES and not type.lower().endswith((".zip", ".bib")):
                    try:
                        from www.services.etl import convert2df
                        df.set(convert2df(ETL_SOURCES[source], input_path=datapath))
                        used_etl = True
                    except Exception:
                        used_etl = False  # fall back to the legacy parser below

                if not used_etl:
                    json = biblio_json(datapath, source, type, author)
                    df.set(pd.read_json(StringIO(json)))

                # Reset all analysis results when new dataset is loaded
                if reset_callback:
                    reset_callback()

                if type.endswith(".zip"):
                    text = ui.p(
                        f"{database}'s ZIP archive uploaded and extracted successfully! "
                        f"Multiple files have been processed and combined. "
                        f"The dataset contains {df.get().shape[0]} rows and {df.get().shape[1]} columns."
                    )
                else:
                    via_etl = " via the source-agnostic ETL pipeline" if used_etl else ""
                    text = ui.p(
                        f"{database}'s file uploaded successfully{via_etl}! "
                        f"You can now proceed to analyze your data. "
                        f"The dataset contains {df.get().shape[0]} rows and {df.get().shape[1]} columns."
                    )
        except Exception as e:
            text = ui.div(
                ui.h5("Error processing file(s):", style="color: red;"),
                ui.p(str(e), style="color: red;"),
                ui.p("Please check that your files are in the correct format and try again.", style="color: gray;")
            )

    elif input.select() == "1B":
        df.set(pd.read_excel(file[0]["datapath"]))
        # Reset all analysis results when new dataset is loaded
        if reset_callback:
            reset_callback()
        text = ui.p(
            f"{database}'s file uploaded successfully! You can now proceed to analyze your data. "
            f"The dataset contains {df.get().shape[0]} rows and {df.get().shape[1]} columns."
        )

    else:
        text = ""

    return text
