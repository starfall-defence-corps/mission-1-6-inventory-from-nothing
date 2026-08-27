"""
ARIA Custom Test Reporter — Mission 1.6: Inventory from Nothing

The phase-oriented summary is rendered by the shared `aria-reporter` pytest
plugin (installed via requirements.txt); this file only declares the mission's
phases + friendly objective names.
"""
PHASES = {
    "TestReconSweep":       ("1", "Recon Sweep"),
    "TestFingerprint":      ("2", "Service Fingerprint"),
    "TestInventoryBuilt":   ("3", "Fleet Registry"),
    "TestFactsReport":      ("4", "Reconnaissance"),
    "TestDynamicInventory": ("5", "Adaptive Cartography"),
}

FRIENDLY = {
    "test_live_hosts_file_exists":        "Recon sweep recorded",
    "test_all_managed_hosts_discovered":  "All managed nodes discovered",
    "test_services_file_exists":          "Service fingerprint recorded",
    "test_roles_match_fingerprints":      "Roles inferred from services",
    "test_decoy_not_treated_as_managed":  "Decoy correctly excluded",
    "test_inventory_lists_all_hosts":     "Inventory reaches all nodes",
    "test_inventory_groups_by_role":      "Hosts grouped by role",
    "test_inventory_ping":                "All nodes respond to ping",
    "test_report_exists":                 "Fleet report created",
    "test_report_matches_live_facts":     "Report built from live facts",
    "test_report_nonces_match":           "Live nonce proves contact",
    "test_dynamic_inventory_present":     "Dynamic inventory deployed",
    "test_dynamic_inventory_after_rotation": "Survives Nyx's rotation",
    "test_dynamic_inventory_ping":        "Dynamic inventory reaches fleet",
}

from aria_reporter import configure  # noqa: E402

configure(phases=PHASES, friendly=FRIENDLY, mission_id="1-6")
