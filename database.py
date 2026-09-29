from supabase import create_client, Client
import streamlit as st

# Maak verbinding met Supabase via de veilige secrets
url: str = st.secrets["SUPABASE_URL"]
key: str = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

GUP_VOLGORDE = [
    "wit",
    "geel",
    "geel/streep",
    "oranje",
    "oranje/streep",
    "groen",
    "groen/streep",
    "groen/blauw",
    "groen/blauw/streep",
    "blauw",
    "blauw/streep",
    "blauw/rood",
    "blauw/rood/streep",
    "rood",
    "rood/streep",
    "rood/zwart",
    "1ste dan",
    "2e dan",
    "3e dan",
    "4e dan",
    "5e dan",
    "6e dan",
    "7e dan",
    "8e dan",
    "9e dan",
]

def init_database():
    # Tabellen zijn al via Supabase SQL aangemaakt
    pass

def init_agenda_tabel():
    pass

def haal_lesuren_op():
    response = supabase.table("lesuren").select("id, omschrijving, leraar").order("id").execute()
    # Om te zorgen dat het exact matcht met wat je oude code teruggaf (tuples/lijst van rijen):
    return [(item["id"], item["omschrijving"], item["leraar"]) for item in response.data]

def update_leraar_bij_lesuur(lesuur_id, nieuwe_leraar):
    supabase.table("lesuren").update({
        "leraar": nieuwe_leraar
    }).eq("id", lesuur_id).execute()

def voeg_lid_toe(naam, geboortedatum, band, examendatum, notitie, lesuur_ids):
    # Voeg lid toe
    res = supabase.table("leden").insert({
        "naam": naam,
        "geboortedatum": geboortedatum,
        "band": band,
        "examendatum": examendatum,
        "notitie": notitie
    }).execute()
    
    # Haal het zojuist aangemaakte ID op
    lid_id = res.data[0]["id"]

    # Voeg examen historie toe
    supabase.table("examen_historie").insert({
        "lid_id": lid_id,
        "band": band,
        "examendatum": examendatum
    }).execute()

    # Koppel lesuren
    if lesuur_ids:
        rijen = [{"lid_id": lid_id, "lesuur_id": l_id} for l_id in lesuur_ids]
        supabase.table("lid_lesuren").insert(rijen).execute()

def update_lid(lid_id, naam, geboortedatum, band, examendatum, notitie, lesuur_ids):
    supabase.table("leden").update({
        "naam": naam,
        "geboortedatum": geboortedatum,
        "band": band,
        "examendatum": examendatum,
        "notitie": notitie
    }).eq("id", lid_id).execute()

    # Verwijder oude lesuur koppelingen en voeg nieuwe toe
    supabase.table("lid_lesuren").delete().eq("lid_id", lid_id).execute()
    if lesuur_ids:
        rijen = [{"lid_id": lid_id, "lesuur_id": l_id} for l_id in lesuur_ids]
        supabase.table("lid_lesuren").insert(rijen).execute()

def haal_historie_op(lid_id):
    response = supabase.table("examen_historie").select("id, band, examendatum").eq("lid_id", lid_id).order("id").execute()
    return [(item["id"], item["band"], item["examendatum"]) for item in response.data]

def update_historie_item(historie_id, nieuwe_band, nieuwe_datum):
    supabase.table("examen_historie").update({
        "band": nieuwe_band,
        "examendatum": nieuwe_datum
    }).eq("id", historie_id).execute()

def verwijder_historie_item(historie_id):
    supabase.table("examen_historie").delete().eq("id", historie_id).execute()

def haal_leden_gefilterd(filter_lesuur_id=None, filter_leraar=None):
    # Haal alle leden op uit Supabase
    leden_res = supabase.table("leden").select("*").execute()
    leden = leden_res.data
    
    resultaat = []
    
    for lid in leden:
        lid_id = lid["id"]
        
        # Haal gekoppelde lesuren op voor dit lid via een join-achtige query
        koppelingen = supabase.table("lid_lesuren").select("lesuur_id").eq("lid_id", lid_id).execute()
        lesuur_ids = [k["lesuur_id"] for k in koppelingen.data]
        
        if not lesuur_ids:
            lesuren = []
        else:
            l_res = supabase.table("lesuren").select("id, omschrijving, leraar").in_("id", lesuur_ids).execute()
            lesuren = [(l["id"], l["omschrijving"], l["leraar"]) for l in l_res.data]
            
        # Filters toepassen
        match = True
        
        if filter_lesuur_id and filter_lesuur_id != "Alles":
            # Check of het lid dit lesuur volgt
            bevat_lesuur = any(l[0] == filter_lesuur_id for l in lesuren)
            if not bevat_lesuur:
                match = False
                
        if filter_leraar and filter_leraar != "Alles":
            # Check of een van de lesuren van dit lid bij deze leraar hoort
            bevat_leraar = any(l[2] == filter_leraar for l in lesuren)
            if not bevat_leraar:
                match = False
                
        if match:
            resultaat.append({
                "id": lid["id"],
                "naam": lid["naam"],
                "geboortedatum": lid["geboortedatum"] if lid["geboortedatum"] else "2000-01-01",
                "band": lid["band"],
                "examendatum": lid["examendatum"],
                "notitie": lid["notitie"] if lid["notitie"] else "",
                "lesuren": lesuren,
            })
            
    return resultaat

def behaal_examen(lid_id, huidige_band, nieuwe_datum):
    huidige_band_clean = str(huidige_band).strip().lower()
    gup_lower = [b.lower() for b in GUP_VOLGORDE]

    if huidige_band_clean in gup_lower:
        index = gup_lower.index(huidige_band_clean)
        if index < len(GUP_VOLGORDE) - 1:
            volgende_band = GUP_VOLGORDE[index + 1]
            
            supabase.table("leden").update({
                "band": volgende_band,
                "examendatum": nieuwe_datum
            }).eq("id", lid_id).execute()
            
            supabase.table("examen_historie").insert({
                "lid_id": lid_id,
                "band": volgende_band,
                "examendatum": nieuwe_datum
            }).execute()
            
            return True, volgende_band
            
    return False, huidige_band

def verwijder_lid(lid_id):
    supabase.table("leden").delete().eq("id", lid_id).execute()
    supabase.table("examen_historie").delete().eq("lid_id", lid_id).execute()

# --- DATABASE FUNCTIES VOOR AGENDA & VERVANGINGEN ---

def haal_vervanging_op(lesuur_id, datum):
    response = supabase.table("vervangingen").select("id, status, vervanger_naam").eq("lesuur_id", lesuur_id).eq("datum", datum).execute()
    if response.data:
        res = response.data[0]
        return (res["id"], res["status"], res["vervanger_naam"])
    return None

def sla_vervanging_op(lesuur_id, datum, status, vervanger_naam):
    bestaat = haal_vervanging_op(lesuur_id, datum)
    
    if bestaat:
        supabase.table("vervangingen").update({
            "status": status,
            "vervanger_naam": vervanger_naam
        }).eq("lesuur_id", lesuur_id).eq("datum", datum).execute()
    else:
        supabase.table("vervangingen").insert({
            "lesuur_id": lesuur_id,
            "datum": datum,
            "status": status,
            "vervanger_naam": vervanger_naam
        }).execute()