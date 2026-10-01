from datetime import date, datetime, timedelta
import database
import pandas as pd
import streamlit as st
import extra_streamlit_components as stx

database.init_database()

# Pagina configuratie (dit moet altijd als allererste staan)
st.set_page_config(page_title="Tang Soo Do Beheer", layout="wide")

st.markdown(
    """
    <style>
    .stMultiSelect span {
        white-space: normal !important;
    }
    div[data-baseweb="select"] > div {
        max-height: 150px;
        overflow-y: auto;
    }
    .timeline {
        border-left: 3px solid #ff4b4b;
        padding-left: 15px;
        margin-top: 10px;
        margin-bottom: 10px;
    }
    .timeline-item {
        margin-bottom: 8px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

st.title("🥋 Tang Soo Do Leden & Lesuren Beheer")

alle_lesuren = database.haal_lesuren_op()
lesuur_mapping = {f"{l[1]} (Leraar: {l[2]})": l[0] for l in alle_lesuren}
lesuur_opties = list(lesuur_mapping.keys())
alle_leraren = list(
    set([l[2] for l in alle_lesuren if l[2] != "Geen leraar"])
)

DAN_WACHTTIJDEN = {
    "rood/zwart": 1,
    "1ste dan": 2,
    "2e dan": 3,
    "3e dan": 4,
    "4e dan": 5,
    "5e dan": 6,
    "6e dan": 7,
    "7e dan": 8,
    "8e dan": 9,
}


def naar_dd_mm_jjjj(datum_str):
  if not datum_str:
    return ""
  datum_str = str(datum_str).split(" ")[0]
  try:
    dt = datetime.strptime(datum_str, "%Y-%m-%d")
    return dt.strftime("%d-%m-%Y")
  except ValueError:
    return datum_str


def naar_jjjj_mm_dd(datum_str):
  if not datum_str:
    return ""
  datum_str = str(datum_str).strip()
  try:
    dt = datetime.strptime(datum_str, "%d-%m-%Y")
    return dt.strftime("%Y-%m-%d")
  except ValueError:
    try:
      dt = datetime.strptime(datum_str, "%Y-%m-%d")
      return dt.strftime("%Y-%m-%d")
    except ValueError:
      return None


def valideer_en_parse_datum(datum_str):
  ISO_datum = naar_jjjj_mm_dd(datum_str)
  if not ISO_datum:
    return (
        False,
        "Ongeldige datumnotatie. Gebruik DD-MM-JJJJ (bijv. 15-06-1995).",
    )

  try:
    parsed_date = datetime.strptime(ISO_datum, "%Y-%m-%d").date()
    vandaag = date.today()
    if parsed_date > vandaag:
      return False, "Geboortedatum kan niet in de toekomst liggen."
    if parsed_date.year < 1900:
      return False, "Geboortejaar kan niet voor 1900 liggen."
    return True, ISO_datum
  except ValueError:
    return False, "Niet-bestaande datum."


def bereken_leeftijd(geboortedatum_iso):
  try:
    geb_datum = datetime.strptime(
        geboortedatum_iso.split(" ")[0], "%Y-%m-%d"
    ).date()
    vandaag = date.today()
    leeftijd = (
        vandaag.year
        - geb_datum.year
        - ((vandaag.month, vandaag.day) < (geb_datum.month, geb_datum.day))
    )
    return leeftijd
  except ValueError:
    return 0


def bereken_wachttijd(band, examendatum_str):
  band_clean = band.strip().lower()
  if band_clean not in DAN_WACHTTIJDEN:
    return None
  vereiste_jaren = DAN_WACHTTIJDEN[band_clean]
  try:
    examen_datum = datetime.strptime(
        examendatum_str.split(" ")[0], "%Y-%m-%d"
    ).date()
  except ValueError:
    return None
  vandaag = date.today()
  verschil_dagen = (vandaag - examen_datum).days
  verstreken_jaren = round(verschil_dagen / 365.25, 1)
  klaar = verstreken_jaren >= vereiste_jaren
  return {
      "vereist": vereiste_jaren,
      "verstreken": verstreken_jaren,
      "klaar": klaar,
  }


tab_leden, tab_leraren, tab_agenda, tab_excel = st.tabs(
    ["👥 Ledenoverzicht", "🥋 Leraren & Lesuren", "📅 Agenda & Vervangingen", "📂 Excel Import"]
)

# --- TAB 1: LEDEN OVERZICHT ---
with tab_leden:
  st.subheader("Zoeken, Filteren & Sorteren")

  zoekterm = st.text_input(
      "🔍 Zoek in alle gegevens (naam, band, notities, leeftijd, etc.):", ""
  ).lower()

  col_f1, col_f2, col_f3 = st.columns(3)
  with col_f1:
    lesuur_filter_opties = ["Alles"] + [
        f"{l[1]} (Leraar: {l[2]})" for l in alle_lesuren
    ]
    filter_lesuur = st.selectbox("Filter op Lesuur", lesuur_filter_opties)
  with col_f2:
    filter_leraar = st.selectbox("Filter op Leraar", ["Alles"] + alle_leraren)
  with col_f3:
    sorteer_optie = st.selectbox(
        "Sorteer op",
        [
            "Naam (Alfabetisch)",
            "Bandhoogte (Laagste naar Hoogste)",
            "Bandhoogte (Hoogste naar Laagste)",
            "Leeftijd (Jong naar Oud)",
            "Leeftijd (Oud naar Jong)",
            "Laatste Examendatum",
        ],
    )

  selected_lesuur_id = "Alles"
  if filter_lesuur != "Alles":
    for l in alle_lesuren:
      if f"{l[1]} (Leraar: {l[2]})" == filter_lesuur:
        selected_lesuur_id = l[0]

  leden = database.haal_leden_gefilterd(
      filter_lesuur_id=selected_lesuur_id, filter_leraar=filter_leraar
  )

  for lid in leden:
    lid["leeftijd"] = bereken_leeftijd(lid["geboortedatum"])

  if zoekterm:
    gefilterde_leden = []
    for lid in leden:
      lesuren_str = " ".join([f"{lu[1]} {lu[2]}" for lu in lid["lesuren"]])
      totaal_tekst = (
          f"{lid['naam']} {lid['leeftijd']} {lid['band']}"
          f" {lid['examendatum']} {lid['notitie']} {lesuren_str}".lower()
      )
      if zoekterm in totaal_tekst:
        gefilterde_leden.append(lid)
    leden = gefilterde_leden

  # Sortering
  if sorteer_optie == "Naam (Alfabetisch)":
    leden = sorted(leden, key=lambda x: x["naam"].lower())
  elif sorteer_optie == "Bandhoogte (Laagste naar Hoogste)":
    leden = sorted(
        leden,
        key=lambda x: (
            database.GUP_VOLGORDE.index(x["band"].lower())
            if x["band"].lower() in database.GUP_VOLGORDE
            else 99
        ),
    )
  elif sorteer_optie == "Bandhoogte (Hoogste naar Laagste)":
    leden = sorted(
        leden,
        key=lambda x: (
            database.GUP_VOLGORDE.index(x["band"].lower())
            if x["band"].lower() in database.GUP_VOLGORDE
            else -1
        ),
        reverse=True,
    )
  elif sorteer_optie == "Leeftijd (Jong naar Oud)":
    leden = sorted(leden, key=lambda x: x["leeftijd"])
  elif sorteer_optie == "Leeftijd (Oud naar Jong)":
    leden = sorted(leden, key=lambda x: x["leeftijd"], reverse=True)
  elif sorteer_optie == "Laatste Examendatum":
    leden = sorted(leden, key=lambda x: str(x["examendatum"]), reverse=True)

  st.divider()
  st.subheader(f"Leden ({len(leden)})")

  if not leden:
    st.info("Geen leden gevonden die voldoen aan de zoektermen.")

  for lid in leden:
    lid_id = lid["id"]
    naam = lid["naam"]
    geboortedatum_iso = lid["geboortedatum"]
    geboortedatum_nl = naar_dd_mm_jjjj(geboortedatum_iso)
    leeftijd = lid["leeftijd"]
    band = lid["band"]
    examendatum_iso = lid["examendatum"]
    examendatum_nl = naar_dd_mm_jjjj(examendatum_iso)
    notitie = lid["notitie"]
    lid_lesuren = lid["lesuren"]

    col1, col2, col3, col4, col5, col6 = st.columns(
        [1.8, 0.8, 1.5, 2.2, 1, 0.5]
    )
    col1.write(f"**{naam}**")
    col2.write(f"Leeftijd: {leeftijd} jr")
    col3.write(f"Band: {band}")

    wachttijd = bereken_wachttijd(band, examendatum_iso)
    if wachttijd:
      if wachttijd["klaar"]:
        col4.markdown(
            f"⏱️ <span style='color:green; font-weight:bold;'>🟢 Klaar! ({wachttijd['verstreken']}/{wachttijd['vereist']} jr)</span>",
            unsafe_allow_html=True,
        )
      else:
        col4.markdown(
            f"⏱️ <span style='color:red; font-weight:bold;'>🔴 Wachttijd: {wachttijd['verstreken']}/{wachttijd['vereist']} jr</span>",
            unsafe_allow_html=True,
        )
    else:
      lesuren_tekst = ", ".join([f"{lu[1]} ({lu[2]})" for lu in lid_lesuren])
      col4.write(
          f"⏱️ {lesuren_tekst if lesuren_tekst else 'Geen lesuur'}"
      )

    with col5:
      if st.button("Geslaagd!", key=f"g_{lid_id}"):
        vandaag_iso = date.today().strftime("%Y-%m-%d")
        gelukt, nw_band = database.behaal_examen(lid_id, band, vandaag_iso)
        if gelukt:
          st.balloons()
          st.toast(
              f"🎉 Geweldig! {naam} is gepromoveerd naar {nw_band}!", icon="🥋"
          )
          # Kleine pauze zodat de ballonnen en toast zichtbaar zijn voor de pagina herlaadt
          import time

          time.sleep(1.5)
          st.rerun()

    with col6:
      if st.button("❌", key=f"v_{lid_id}"):
        database.verwijder_lid(lid_id)
        st.rerun()

    if notitie:
      st.info(f"📝 **Notitie:** {notitie}")

    # Tijdlijn & Archief beheren
    with st.expander(f"📜 Tijdlijn & Archief beheren van {naam}"):
      historie = database.haal_historie_op(lid_id)
      if not historie:
        st.write("Nog geen examenhistorie bekend.")
      else:
        st.write("Hier zie je de tijdlijn. Je kunt stappen aanpassen of wissen:")
        for h_id, h_band, h_datum_iso in historie:
          h_datum_nl = naar_dd_mm_jjjj(h_datum_iso)
          col_h1, col_h2, col_h3 = st.columns([3, 2, 1])
          col_h1.write(f"🥋 **{h_band}** (Datum: {h_datum_nl})")

          with col_h2:
            with st.popover(f"✏️ Bewerk stap"):
              with st.form(key=f"edit_hist_{h_id}"):
                nw_h_band = st.selectbox(
                    "Band",
                    database.GUP_VOLGORDE,
                    index=(
                        database.GUP_VOLGORDE.index(h_band.lower())
                        if h_band.lower() in database.GUP_VOLGORDE
                        else 0
                    ),
                    key=f"sb_h_band_{h_id}",
                )
                nw_h_datum_nl = st.text_input(
                    "Examendatum (DD-MM-JJJJ)",
                    value=h_datum_nl,
                    key=f"dt_h_{h_id}",
                )

                if st.form_submit_button("Stap opslaan"):
                  iso_check = naar_jjjj_mm_dd(nw_h_datum_nl)
                  if not iso_check:
                    st.error("Gebruik formaat DD-MM-JJJJ")
                  else:
                    database.update_historie_item(h_id, nw_h_band, iso_check)
                    st.success("Stap aangepast!")
                    st.rerun()

          with col_h3:
            if st.button("❌", key=f"del_hist_{h_id}", help="Verwijder stap"):
              database.verwijder_historie_item(h_id)
              st.warning("Stap verwijderd.")
              st.rerun()

    # Bewerken scherm lid
    with st.expander(f"✏️ Bewerk gegevens van {naam}"):
      with st.form(key=f"edit_form_{lid_id}"):
        nw_naam = st.text_input("Naam", value=naam)
        nw_geboortedatum_nl = st.text_input(
            "Geboortedatum (DD-MM-JJJJ)", value=geboortedatum_nl
        )

        try:
          b_idx = database.GUP_VOLGORDE.index(band.lower())
        except ValueError:
          b_idx = 0
        nw_band = st.selectbox("Band", database.GUP_VOLGORDE, index=b_idx)

        nw_examendatum_nl = st.text_input(
            "Laatste Examendatum (DD-MM-JJJJ)", value=examendatum_nl
        )

        nw_notitie = st.text_area(
            "Notities / Feedback",
            value=notitie,
            placeholder="Voeg hier feedback toe...",
        )

        st.write("⏱️ **Selecteer lesuren:**")
        huidige_ids = [l[0] for l in lid_lesuren]
        gekozen_ids_edit = []
        for lu in alle_lesuren:
          lu_id, omschrijving, leraar = lu
          is_aan = lu_id in huidige_ids
          if st.checkbox(
              f"{omschrijving} — Leraar: {leraar}",
              value=is_aan,
              key=f"chk_edit_{lid_id}_{lu_id}",
          ):
            gekozen_ids_edit.append(lu_id)

        if st.form_submit_button("Opslaan"):
          geldig, resultaat_geb = valideer_en_parse_datum(nw_geboortedatum_nl)
          geldig_ex, resultaat_ex = valideer_en_parse_datum(nw_examendatum_nl)

          if not geldig:
            st.error(f"Geboortedatum fout: {resultaat_geb}")
          elif not geldig_ex:
            st.error(f"Examendatum fout: {resultaat_ex}")
          else:
            database.update_lid(
                lid_id,
                nw_naam,
                resultaat_geb,
                nw_band,
                resultaat_ex,
                nw_notitie,
                gekozen_ids_edit,
            )
            st.success("Aangepast!")
            st.rerun()

    st.divider()

# --- SIDEBAR: NIEUW LID TOEVOEGEN ---
st.sidebar.header("➕ Nieuw Lid Toevoegen")

n_naam = st.sidebar.text_input("Naam", key="sb_naam")
n_geboortedatum_nl = st.sidebar.text_input(
    "Geboortedatum (DD-MM-JJJJ)",
    value="15-05-1995",
    placeholder="Bijv. 20-04-1985",
    key="sb_geb",
)
n_band = st.sidebar.selectbox("Band", database.GUP_VOLGORDE, key="sb_band_sel")
n_datum_nl = st.sidebar.text_input(
    "Laatste Examendatum (DD-MM-JJJJ)",
    value=date.today().strftime("%d-%m-%Y"),
    placeholder="Bijv. 01-01-2026",
    key="sb_ex",
)
n_notitie = st.sidebar.text_area("Notities / Feedback", key="sb_not")

nieuwe_ids = []
with st.sidebar.expander("⏱️ Klik hier om lesuren te selecteren"):
  for lu in alle_lesuren:
    lu_id, omschrijving, leraar = lu
    if st.checkbox(
        f"{omschrijving} — Leraar: {leraar}", key=f"chk_new_{lu_id}"
    ):
      nieuwe_ids.append(lu_id)

st.sidebar.write("")

if st.sidebar.button("Lid Toevoegen", type="primary"):
  if n_naam:
    geldig, resultaat_geb = valideer_en_parse_datum(n_geboortedatum_nl)
    geldig_ex, resultaat_ex = valideer_en_parse_datum(n_datum_nl)

    if not geldig:
      st.sidebar.error(f"Geboortedatum fout: {resultaat_geb}")
    elif not geldig_ex:
      st.sidebar.error(f"Examendatum fout: {resultaat_ex}")
    else:
      database.voeg_lid_toe(
          n_naam, resultaat_geb, n_band, resultaat_ex, n_notitie, nieuwe_ids
      )
      st.sidebar.success("Lid toegevoegd!")
      st.rerun()
  else:
    st.sidebar.error("Vul ten minste een naam in.")

# --- TAB 2: LERAREN KOPPELEN ---
with tab_leraren:
  st.subheader("Leraren Koppelen aan Lesuren")
  for lu in alle_lesuren:
    lu_id, omschrijving, huidige_leraar = lu
    c1, c2, c3 = st.columns([3, 2, 1])
    c1.write(f"**{omschrijving}**")
    nieuwe_leraar_naam = c2.text_input(
        f"Leraar {omschrijving}",
        value=huidige_leraar,
        key=f"ler_{lu_id}",
        label_visibility="collapsed",
    )
    if c3.button("Opslaan", key=f"btn_ler_{lu_id}"):
      database.update_leraar_bij_lesuur(lu_id, nieuwe_leraar_naam)
      st.success("Bijgewerkt!")
      st.rerun()

# --- TAB 3: AGENDA & VERVANGINGEN ---
with tab_agenda:
    database.init_agenda_tabel()
    st.subheader("📅 Lesagenda & Vervangingen")
    st.write("Hier kun je zien welke lessen er aankomen, of er leraren afwezig zijn, en wie een les kan overnemen.")

    # Datumkiezer voor de agenda (standaard vandaag of komende dagen)
    col_d1, col_d2 = st.columns([2, 2])
    with col_d1:
        gekozen_datum = st.date_input("Selecteer datum", value=date.today())
    
    gekozen_datum_str = gekozen_datum.strftime("%d-%m-%Y")
    dag_van_week = gekozen_datum.strftime("%A") # Bijv. Monday, Wednesday, Friday
    
    # Vertaling dag naar Nederlands voor de visuele check
    dagen_nl = {
        "Monday": "Maandag",
        "Wednesday": "Woensdag",
        "Friday": "Vrijdag",
        "Tuesday": "Dinsdag",
        "Thursday": "Donderdag",
        "Saturday": "Zaterdag",
        "Sunday": "Zondag"
    }
    dag_nl_tekst = dagen_nl.get(dag_van_week, dag_van_week)
    st.markdown(f"### Lessen op {dag_nl_tekst} ({gekozen_datum.strftime('%d-%m-%Y')})")

    # Filter de vaste lesuren op basis van de dag in de omschrijving
    relevante_lessen = []
    for lu in alle_lesuren:
        lu_id, omschrijving, leraar = lu
        if dag_nl_tekst.lower() in omschrijving.lower():
            relevante_lessen.append(lu)

    if not relevante_lessen:
        st.info(f"Op {dag_nl_tekst} staan er geen vaste lessen ingeroosterd in het systeem.")
    else:
        for lu in relevante_lessen:
            lu_id, omschrijving, vaste_leraar = lu
            
            # Haal eventuele vervanging op voor deze datum
            vervanging = database.haal_vervanging_op(lu_id, gekozen_datum_str)
            
            status = "Normaal"
            vervanger = ""
            if vervanging:
                status = vervanging[1]
                vervanger = vervanging[2]

            with st.container(border=True):
                c_a1, c_a2, c_a3 = st.columns([2, 1.5, 2])
                
                with c_a1:
                    st.write(f"**{omschrijving}**")
                    st.caption(id_tekst := f"Vaste leraar: {vaste_leraar}")

                with c_a2:
                    if status == "Normaal" or not status:
                        st.markdown("🟢 **Normaal**")
                    elif status == "Gezocht":
                        st.markdown("🔴 **Vervanger Gezocht!**")
                    elif status == "Overgenomen":
                        st.markdown(f"🟡 **Overgenomen door {vervanger}**")

                with c_a3:
                    # Popover of knoppen om status aan te passen
                    with st.popover("⚙️ Beheer vervanging"):
                        st.write(f"**{omschrijving}**")
                        
                        # Optie 1: Vaste leraar kan aangeven dat hij afwezig is
                        if st.button("🔴 Ik ben afwezig (zoek vervanger)", key=f"afw_{lu_id}_{gekozen_datum_str}"):
                            database.sla_vervanging_op(lu_id, gekozen_datum_str, "Gezocht", "")
                            st.toast("Status gewijzigd naar: Vervanger gezocht!", icon="🚨")
                            st.rerun()
                            
                        # Optie 2: Collega kan invallen
                        ingevallen_naam = st.selectbox("Collega die invalt:", ["Kies leraar..."] + alle_leraren, key=f"inv_{lu_id}_{gekozen_datum_str}")
                        if ingevallen_naam != "Kies leraar...":
                            if st.button("🟢 Neem deze les over", key=f"overn_{lu_id}_{gekozen_datum_str}"):
                                database.sla_vervanging_op(lu_id, gekozen_datum_str, "Overgenomen", ingevallen_naam)
                                st.toast(f"Les overgenomen door {ingevallen_naam}!", icon="👍")
                                st.rerun()

                        # Optie 3: Terugzetten naar normaal
                        if status != "Normaal":
                            if st.button("🔄 Zet terug naar normaal", key=f"herstel_{lu_id}_{gekozen_datum_str}"):
                                database.sla_vervanging_op(lu_id, gekozen_datum_str, "Normaal", "")
                                st.toast("Les hersteld naar normaal rooster.", icon="🔄")
                                st.rerun()

# --- TAB 4: EXCEL IMPORT ---
with tab_excel:
  st.subheader("Leden importeren via Excel")
  st.write(
      "Zorg dat je Excel-bestand de juiste kolomnamen gebruikt. Datums noteer"
      " je als **DD-MM-JJJJ** en voor lesuren gebruik je de nummers uit de"
      " legenda hieronder."
  )

  # Legenda en Voorbeeld in een inklapmenu (inclusief actuele leraren)
  with st.expander(
      "💡 Klik hier voor de Lesuur-legenda, Excel-voorbeeld en kolomuitleg"
  ):
    st.markdown("### 📋 Lesuur-legenda (Gebruik deze nummers in Excel):")

    # Dynamische legenda genereren op basis van de database (inclusief actuele leraren!)
    legenda_md = ""
    for lu in alle_lesuren:
      lu_id, omschrijving, leraar = lu
      legenda_md += f"* **{lu_id}** = {omschrijving} — *Leraar: {leraar}*\n"
    st.markdown(legenda_md)

    st.markdown("---")
    st.write(
        "Je Excel-bestand (`.xlsx` of `.xls`) moet op de **eerste rij** de"
        " volgende exacte kolomnamen bevatten:"
    )

    voorbeeld_data = pd.DataFrame({
        "naam": ["Jan de Vries", "Lisa Jansen"],
        "geboortedatum": ["15-06-1995", "20-03-2008"],
        "band": ["wit", "groen"],
        "examendatum": ["15-01-2026", "10-11-2025"],
        "notitie": ["Heeft moeite met sparing", "Talentvol"],
        "lesuren": ["1, 2", "5, 8"],
    })

    st.dataframe(voorbeeld_data, hide_index=True)

    st.caption(
        "📌 **Belangrijke tips:**\n"
        "1. Kolomnamen exact overnemen in kleine letters (`naam`,"
        " `geboortedatum`, etc.).\n"
        "2. Datums in notatie **`DD-MM-JJJJ`** (bijv. `15-06-1995`).\n"
        "3. In de kolom `lesuren` noteer je de nummers uit de legenda,"
        " gescheiden door een komma (bijv. `1, 2`)."
    )

  st.divider()

  excel_file = st.file_uploader(
      "Kies je ingevulde Excel-bestand", type=["xlsx", "xls"]
  )
  if excel_file and st.button("Verwerk Excel"):
    try:
      df = pd.read_excel(excel_file, usecols="A:F")
      df = df.dropna(subset=['naam'])
    except Exception as e:
      st.error(
          "❌ Kan het bestand niet lezen. Zorg dat het een geldig"
          f" Excel-bestand is (.xlsx of .xls).\nFoutmelding: {e}"
      )
      st.stop()

    verplichte_kolommen = ["naam", "geboortedatum", "band"]
    ontbrekend = [
        col for col in verplichte_kolommen if col not in df.columns
    ]
    if ontbrekend:
      st.error(
          "❌ Het Excel-bestand mist verplichte kolommen: "
          f"**{', '.join(ontbrekend)}**. Controleer de kolomnamen op de eerste"
          " rij (moeten kleine letters zijn)."
      )
    else:
      fouten = []
      aantal_gelukt = 0

      for idx, row in df.iterrows():
        naam_val = str(row["naam"]) if pd.notna(row["naam"]) else "Onbekend"
        geb_raw = (
            str(row["geboortedatum"]).split(" ")[0]
            if pd.notna(row["geboortedatum"])
            else ""
        )
        geb_val = row.get("geboortedatum")
        if pd.isna(geb_val) or geb_val is None:
            geb_raw = ""
        elif isinstance(geb_val, datetime):
            geb_raw = geb_val.strftime("%d-%m-%Y")
        else:
            geb_raw = str(geb_val)

        geldig, resultaat_geb = valideer_en_parse_datum(geb_raw)
        if not geldig:
          fouten.append(f"Rij {idx+2} ({naam_val}) - Geboortedatum: {resultaat_geb}")
          continue

        band_val = (
            str(row["band"]).strip().lower()
            if pd.notna(row["band"])
            else database.GUP_VOLGORDE[0]
        )
        if band_val not in database.GUP_VOLGORDE:
          fouten.append(
              f"Rij {idx+2} ({naam_val}) - Band: Onbekende bandnaam"
              f" '{row['band']}'."
          )
          continue

        datum_raw = (
            str(row["examendatum"]).split(" ")[0]
            if "examendatum" in df.columns and pd.notna(row["examendatum"])
            else date.today().strftime("%d-%m-%Y")
        )
        if isinstance(row.get("examendatum"), datetime):
          datum_raw = row["examendatum"].strftime("%d-%m-%Y")

        geldig_ex, resultaat_ex = valideer_en_parse_datum(datum_raw)
        if not geldig_ex:
          resultaat_ex = date.today().strftime("%Y-%m-%d")

        notitie_val = (
            str(row["notitie"])
            if "notitie" in df.columns and pd.notna(row["notitie"])
            else ""
        )

        gekozen_ids = []
        if "lesuren" in df.columns and pd.notna(row["lesuren"]):
          lesuur_input = str(row["lesuren"]).replace(".0", "")
          ingevoerde_nummers = [
              x.strip() for x in lesuur_input.replace(";", ",").split(",")
          ]

          for num in ingevoerde_nummers:
            if num.isdigit():
              num_int = int(num)
              matching_lu = [lu for lu in alle_lesuren if lu[0] == num_int]
              if matching_lu:
                gekozen_ids.append(matching_lu[0][0])

        database.voeg_lid_toe(
            naam_val,
            resultaat_geb,
            band_val,
            resultaat_ex,
            notitie_val,
            list(set(gekozen_ids)),
        )
        aantal_gelukt += 1

      if fouten:
        st.warning(
            f"⚠️ Er zijn {aantal_gelukt} leden succesvol geïmporteerd, maar er"
            " zijn ook fouten gevonden in specifieke rijen:\n"
            + "\n".join(f"- {f}" for f in fouten)
        )
      else:
        st.balloons()
        st.success(
            f"🎉 Gelukt! Alle {aantal_gelukt} leden zijn succesvol geïmporteerd"
            " vanuit het Excel-bestand."
        )