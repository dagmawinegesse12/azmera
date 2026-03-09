// ── Region definitions ────────────────────────────────────────────
// Source of truth for all 13 Ethiopian administrative regions
// that Azmera supports. Mirrors REGION_DISPLAY in validation.py.

export const REGION_KEYS = [
  "addis_ababa",
  "afar",
  "amhara",
  "benishangul_gumz",
  "dire_dawa",
  "gambela",
  "harari",
  "oromia",
  "sidama",
  "snnpr",
  "somali",
  "south_west",
  "tigray",
] as const;

export type RegionKey = (typeof REGION_KEYS)[number];

export const REGION_DISPLAY: Record<RegionKey, string> = {
  addis_ababa:      "Addis Ababa",
  afar:             "Afar",
  amhara:           "Amhara",
  benishangul_gumz: "Benishangul-Gumz",
  dire_dawa:        "Dire Dawa",
  gambela:          "Gambela",
  harari:           "Harari",
  oromia:           "Oromia",
  sidama:           "Sidama",
  snnpr:            "SNNPR",
  somali:           "Somali",
  south_west:       "South West",
  tigray:           "Tigray",
};

// Inverse lookup: display name → key
export const DISPLAY_TO_REGION_KEY: Record<string, RegionKey> = Object.fromEntries(
  Object.entries(REGION_DISPLAY).map(([k, v]) => [v, k as RegionKey])
) as Record<string, RegionKey>;

// Sorted list for UI dropdowns
export const REGION_OPTIONS = REGION_KEYS.map((key) => ({
  key,
  label: REGION_DISPLAY[key],
})).sort((a, b) => a.label.localeCompare(b.label));

// Harari routes through Dire Dawa model — flag this in UI notes
export const HARARI_USES_DIRE_DAWA_MODEL = true;

// GeoJSON NAME_1 → Azmera region key mapping.
//
// The bundled GeoJSON (public/ethiopia_regions.geojson) is a GADM admin-level-1
// file sourced before the 2020/2021 regional re-organisation, so it contains
// 11 features. Sidama and South West were carved out of SNNPR after that date
// and are therefore absent from the file — they inherit SNNPR's polygon for
// map display purposes (both map to "snnpr" until a newer boundary file is used).
//
// NAME_1 strings in the file are concatenated GADM identifiers (no spaces):
export const GEOJSON_TO_AZMERA: Record<string, RegionKey> = {
  // Exact NAME_1 values from the bundled GADM file
  "AddisAbeba":                   "addis_ababa",
  "Afar":                         "afar",
  "Amhara":                       "amhara",
  "Benshangul-Gumaz":             "benishangul_gumz",
  "DireDawa":                     "dire_dawa",
  "GambelaPeoples":               "gambela",
  "HarariPeople":                 "harari",
  "Oromia":                       "oromia",
  "Somali":                       "somali",
  "SouthernNations,Nationalities":"snnpr",
  "Tigray":                       "tigray",

  // Aliases for newer / cleaned-up GeoJSON files
  "Addis Ababa":                  "addis_ababa",
  "Dire Dawa":                    "dire_dawa",
  "Gambela":                      "gambela",
  "Harari":                       "harari",
  "Sidama":                       "sidama",
  "Southern Nations, Nationalities, and Peoples' Region": "snnpr",
  "South West Ethiopia People's Region":                   "south_west",
  "South West":                   "south_west",
};
