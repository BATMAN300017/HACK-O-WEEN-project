import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.core.database import get_db_connection
from app.services.route_map_service import get_scam_and_route_dossier

with get_db_connection() as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT id, case_number FROM investigations LIMIT 1")
    row = cursor.fetchone()
    inv_id = row[0]
    print(f"Testing route dossier for investigation: {inv_id} ({row[1]})")
    dossier = get_scam_and_route_dossier(conn, investigation_id=inv_id)
    print("Scam Title:", dossier.get("scam_title"))
    print("Scam Category:", dossier.get("scam_category"))
    print("Total Hops:", dossier.get("route_map", {}).get("total_hops"))
    print("Origin:", dossier.get("route_map", {}).get("origin_city"))
    print("Destination:", dossier.get("route_map", {}).get("destination_city"))
    print("Distance:", dossier.get("route_map", {}).get("distance_km"), "km")
    for hop in dossier.get("route_map", {}).get("hops", []):
        print(f"  Hop {hop['hop_index']} [{hop['hop_type']}]: {hop['title']} ({hop['city']}, {hop['country']}) -> {hop['amount']} {hop['currency']}")
    print("Exculpatory checks:", dossier.get("exculpatory_analysis", {}).get("scholarship_or_institution_check"))
    print("\nSUCCESS!")
