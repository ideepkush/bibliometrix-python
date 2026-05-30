from .utils import *
import pandas as pd


def metaTagExtraction(df, Field="AU_CO", sep=";", aff_disamb=False):
    """
    Extract metadata tags from a DataFrame based on the specified field.
    
    Args:
        df: A DataFrame object containing the data.
        Field: The field to extract metadata tags from.
        sep: The separator used to split the metadata tags.
        aff_disamb: A boolean value indicating whether to disambiguate the affiliations.
    
    Returns:
        A DataFrame with the extracted metadata tags.
    """
    M = df if isinstance(df, pd.DataFrame) else df.get()
    if Field == "SR":
        M = SR(M)

    if Field == "CR_AU":
        M = CR_AU(M)

    if Field == "CR_SO":
        M = CR_SO(M)

    if Field == "AU_CO":
        M = AU_CO(M)

    if Field == "AU1_CO":
        M = AU1_CO(M)

    if Field == "AU_UN":
        if aff_disamb:
            M = AU_UN(M, sep)
        else:
            M["AU_UN"] = M["C1"].str.replace(r"\[.*?\] ", "", regex=True)
            M["AU1_UN"] = M["RP"].str.split(sep).apply(lambda l: l[0] if isinstance(l, list) else l)
            ind = M["AU1_UN"].str.find("),")
            a = ind[ind > -1].index
            M.loc[a, "AU1_UN"] = M.loc[a, "AU1_UN"].str[ind[a] + 2:]

    if not isinstance(df, pd.DataFrame):
        df.set(M)
        return df
    return M


def SR(M):
    # AU may be a real list (from convert2df) or a ";"-delimited string (when
    # the data was reloaded from a flat CSV/XLSX, e.g. the sample file), or a
    # NaN float when missing. Normalise to a list of author names so the short
    # reference is built from authors — not from individual characters — and
    # never crashes with "'float' object is not iterable".
    def _au_list(l):
        if isinstance(l, list):
            return [str(x).strip() for x in l]
        if isinstance(l, str):
            return [a.strip() for a in l.split(";") if a.strip()]
        return []
    listAU = M["AU"].apply(_au_list)
    if M["DB"].iloc[0].lower() == "scopus":
        listAU = listAU.apply(lambda l: [x.replace(" ", ",").replace(",,", ",").replace(" ", "") for x in l])
    FirstAuthors = listAU.apply(lambda l: l[0] if len(l) > 0 else "NA").str.replace(",", " ")

    no_art = M["JI"] == ""
    M.loc[no_art, "JI"] = M.loc[no_art, "SO"]
    J9 = M["JI"].str.replace(".", " ", regex=False).str.strip()
    # The journal abbreviation can still be missing for some records (e.g.
    # Lens rows lacking both JI and SO). Fill it so the short reference never
    # becomes NaN: a NaN SR cannot be made unique by the de-duplication below
    # (NaN + "-a" stays NaN), which would loop until chr(96 + i) overflows and
    # raised "chr() arg not in range(0x110000)".
    J9 = J9.fillna("NA")
    SR = FirstAuthors + ", " + M["PY"].astype(str) + ", " + J9
    SR = SR.fillna("NA")

    M["SR_FULL"] = SR.str.replace(r"\s+", " ", regex=True)

    # Disambiguate duplicate short references deterministically in a single
    # vectorized pass. The first occurrence keeps the base SR; later duplicates
    # receive a "-a", "-b", ... "-z", "-aa", ... suffix. This replaces an older
    # incremental loop ( SR[dup] += "-" + chr(96 + i) ) that never terminated
    # on NaN/empty values and eventually overflowed chr().
    def _dup_suffix(n: int) -> str:
        if n <= 0:
            return ""
        s = ""
        while n > 0:
            n -= 1
            s = chr(97 + (n % 26)) + s
            n //= 26
        return "-" + s

    dup_rank = SR.groupby(SR).cumcount()
    SR = SR + dup_rank.map(_dup_suffix)
    M["SR"] = SR.str.replace(r"\s+", " ", regex=True)

    return M


# TO BE DONE
def CR_AU(M):
    listCAU = M["CR"].apply(lambda x: x if isinstance(x, list) else []).apply(lambda l: [x for x in l if len(x) > 10])
    FCAU = listCAU.apply(lambda l: [x.split(",")[0].strip() for x in l])
    M["CR_AU"] = FCAU.apply(lambda l: ";".join(l))
    
    return M


def CR_SO(M):
    listCAU = M["CR"].apply(lambda x: x if isinstance(x, list) else [])
    if M["DB"].iloc[0].upper() != "SCOPUS":
        FCAU = listCAU.apply(lambda l: [x.split(",")[2].strip() for x in l if len(x.split(",")) > 2])
    else:
        FCAU = listCAU.apply(lambda l: [x.split(",")[0].strip() for x in l if len(x.split(",")) > 2])        
    
    M["CR_SO"] = FCAU.apply(lambda l: ";".join(l) if l else None) # da checkare
    
    return M


def AU_CO(M, log=False):
    # Read the list of countries
    with open("www/static/countries.txt", "r") as file:
        countries = file.read().splitlines()

    # Extract the countries from the affiliations
    M["AU_CO"] = None
    C1 = M["C1"]
    
    # Convert empty lists in C1 using the values from RP
    C1 = M["C1"].fillna(M["RP"])
    
    for i in range(len(C1)):
        # Check if the element is an empty list
        if isinstance(C1.iloc[i], list) and not C1.iloc[i]:
            if pd.notna(M["RP"].iloc[i]):  # Check if "RP" is valid
                C1.at[i] = [M["RP"].iloc[i]]  # Use at to assign directly
            else:  # If "RP" is also empty, assign an empty list
                C1.at[i] = []

    # Extract the countries from the affiliations
    results = []
    for i in range(len(M)):
        countries_found = []
        # Affiliations may be missing (a NaN float) rather than a list, e.g.
        # on records without a C1/RP address. Treat anything that is not a
        # list/tuple as "no affiliations" instead of crashing with
        # "'float' object is not iterable".
        c1_value = C1.iloc[i]
        if not isinstance(c1_value, (list, tuple)):
            c1_value = []
        for c1 in c1_value:
            if isinstance(c1, str) and pd.notna(c1):
                ind = [c.upper() for c in countries if re.search(r'\b' + re.escape(c.upper()) + r'\b', c1.split(",")[-1].strip().upper())]
                countries_found.extend(ind)
        results.append(countries_found)

    # Assign results to the AU_CO column
    M["AU_CO"] = results
    
    # Replace country names with standardized names
    M["AU_CO"] = M["AU_CO"].apply(lambda countries: [country.replace("UNITED STATES", "USA")
                                                     .replace("RUSSIAN FEDERATION", "RUSSIA")
                                                     .replace("TAIWAN", "CHINA")
                                                     .replace("ENGLAND", "UNITED KINGDOM")
                                                     .replace("SCOTLAND", "UNITED KINGDOM")
                                                     .replace("WALES", "UNITED KINGDOM")
                                                     .replace("NORTH IRELAND", "UNITED KINGDOM")
                                                     for country in countries])
    
    if log:
        with open("affiliations.txt", "w", encoding="utf-8") as file:
            for affiliation in M["AU_CO"]:
                file.write(f"{affiliation}\n")

    return M


def AU1_CO(M, log=False):
    # Read the list of countries
    with open("www/static/countries.txt", "r") as file:
        countries = file.read().splitlines()

    # Initialize the AU1_CO column
    M["AU1_CO"] = None
    C1 = M["C1"]

    # Convert empty lists in C1 using the values from RP
    C1 = M["C1"].fillna(M["RP"])

    for i in range(len(C1)):
        # Check if the element is an empty list
        if isinstance(C1.iloc[i], list) and not C1.iloc[i]:
            if pd.notna(M["RP"].iloc[i]):  # Check if "RP" is valid
                C1.at[i] = [M["RP"].iloc[i]]  # Use at to assign directly
            else:  # If "RP" is also empty, assign an empty list
                C1.at[i] = []

    # Extract the first country found in the affiliations
    results = []
    for i in range(len(M)):
        first_country = None
        for c1 in C1.iloc[i]:
            if pd.notna(c1):
                # Extract the last part of the affiliation string (typically the country)
                last_part = c1.split(",")[-1].strip().upper()
                # Search for the first matching country
                for country in countries:
                    if re.search(r'\b' + re.escape(country.upper()) + r'\b', last_part):
                        first_country = country.upper()
                        break
            if first_country:
                break  # Stop after finding the first country
        results.append(first_country)

    # Assign results to the AU1_CO column
    M["AU1_CO"] = results

    # Replace country names with standardized names
    M["AU1_CO"] = M["AU1_CO"].apply(lambda country: country.replace("UNITED STATES", "USA")
                                                 .replace("RUSSIAN FEDERATION", "RUSSIA")
                                                 .replace("TAIWAN", "CHINA")
                                                 .replace("ENGLAND", "UNITED KINGDOM")
                                                 .replace("SCOTLAND", "UNITED KINGDOM")
                                                 .replace("WALES", "UNITED KINGDOM")
                                                 .replace("NORTH IRELAND", "UNITED KINGDOM")
                                                 if pd.notna(country) else None)
    
    if log:
        with open("first_author_countries.txt", "w", encoding="utf-8") as file:
            for affiliation in M["AU1_CO"]:
                file.write(f"{affiliation}\n")

    return M


# TO BE DONE
def AU_UN(M, sep):
    C1 = M["C1"].fillna(M["RP"])
    AFF = C1.str.replace(r"\[.*?\] ", "", regex=True)
    indna = AFF.isna()
    AFF[indna] = M["RP"][indna]
    AFF = AFF.str.strip()
    listAFF = AFF.str.split(sep)

    uTags = ["UNIV", "COLL", "SCH", "INST", "ACAD", "ECOLE", "CTR", "SCI", "CENTRE", "CENTER", "CENTRO", "HOSP", "ASSOC", "COUNCIL",
             "FONDAZ", "FOUNDAT", "ISTIT", "LAB", "TECH", "RES", "CNR", "ARCH", "SCUOLA", "PATENT OFF", "CENT LIB", "HEALTH", "NATL",
             "LIBRAR", "CLIN", "FDN", "OECD", "FAC", "WORLD BANK", "POLITECN", "INT MONETARY FUND", "CLIMA", "METEOR", "OFFICE", "ENVIR",
             "CONSORTIUM", "OBSERVAT", "AGRI", "MIT ", "INFN", "SUNY "]

    def extract_affiliations(l):
        index = []
        for item in l:
            item = item.replace("(REPRINT AUTHOR)", "")
            affL = item.split(",")
            indd = [i for i, aff in enumerate(affL) if any(tag in aff for tag in uTags)]
            if not indd:
                index.append("NOTREPORTED")
            elif any(char.isdigit() for char in affL[indd[0]]):
                index.append("NOTDECLARED")
            else:
                index.append(affL[indd[0]])
        return ";".join(index)

    M["AU_UN"] = listAFF.apply(extract_affiliations)
    if M["DB"].iloc[0] in ["ISI", "OPENALEX"] and "C3" in M.columns:
        M["AU_UN"].loc[M["C3"].notna() & (M["C3"] != "")] = M["C3"]
        M["AU_UN"] = M["AU_UN"].str.split(sep).apply(lambda l: sep.join([x.strip() for x in l]))

    M["AU_UN"] = M["AU_UN"].str.replace(r"\\&", "AND", regex=True).str.replace("&", "AND", regex=False)

    RP = M["RP"].fillna(M["C1"])
    AFF = RP.str.replace(r"\[.*?\] ", "", regex=True)
    indna = AFF.isna()
    AFF[indna] = M["RP"][indna]
    AFF = AFF.str.strip()
    listAFF = AFF.str.split(sep)

    M["AU1_UN"] = listAFF.apply(extract_affiliations)
    M["AU1_UN"] = M["AU1_UN"].str.replace(r"\\&", "AND", regex=True).str.replace("&", "AND", regex=False)

    M["AU_UN_NR"] = None
    listAFF2 = M["AU_UN"].str.split(sep)
    cont = listAFF2.apply(lambda l: [i for i, x in enumerate(l) if x == "NR"])

    for i, indices in enumerate(cont):
        if indices:
            M.at[i, "AU_UN_NR"] = ";".join([listAFF.iloc[i][j] for j in indices])

    M["AU_UN"] = M["AU_UN"].replace({"NOTDECLARED": None, "NOTREPORTED": None})
    M["AU_UN"] = M["AU_UN"].str.replace("NOTREPORTED;", "", regex=False).str.replace(";NOTREPORTED", "", regex=False)
    M["AU_UN"] = M["AU_UN"].str.replace("NOTDECLARED;", "", regex=False).str.replace("NOTDECLARED", "", regex=False)
    
    return M
