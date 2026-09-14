import { bunPG } from "../src/db/sql";

// ============================================================================
// Commute Hubs Seeder (Phase 3, plan.md)
//
// Populates major employment, commercial, airport and transit hubs per city:
// Bengaluru, Pune, Mumbai, Indore, Dubai, plus Gurgaon, Delhi and Noida.
// Used for the PIP "Check Travel Time" section; the neighbourhood job also
// reads the AIRPORT hubs for each property's airport distance.
//
// Coordinates: Indore's come from our own OpenStreetMap import (central zone,
// 2026-09-12). Dubai has no OSM import yet, so its hubs use published
// landmark coordinates; re-check them against OSM once the GCC zone is loaded.
// Idempotent: upserts on (city, name).
// ============================================================================

interface HubDef {
  country: "IN" | "AE";
  city: string;
  name: string;
  category: "FINANCE" | "AIRPORT" | "TECH" | "COMMERCIAL" | "TRANSIT" | "EDUCATION" | "HEALTH";
  latitude: number;
  longitude: number;
  transitHint?: string;
  sortOrder: number;
}

export const CANONICAL_HUBS: HubDef[] = [
  // --- BENGALURU ---
  {
    country: "IN",
    city: "Bengaluru",
    name: "Kempegowda International Airport (BLR)",
    category: "AIRPORT",
    latitude: 13.1986,
    longitude: 77.7066,
    transitHint: "Airport Shuttle & Proposed Blue Line Metro",
    sortOrder: 1,
  },
  {
    country: "IN",
    city: "Bengaluru",
    name: "Manyata Tech Park (Hebbal)",
    category: "TECH",
    latitude: 13.0494,
    longitude: 77.6206,
    transitHint: "Outer Ring Road / Blue Line Metro",
    sortOrder: 2,
  },
  {
    country: "IN",
    city: "Bengaluru",
    name: "Electronic City Phase 1",
    category: "TECH",
    latitude: 12.8452,
    longitude: 77.6602,
    transitHint: "Yellow Line Elevated Metro",
    sortOrder: 3,
  },
  {
    country: "IN",
    city: "Bengaluru",
    name: "International Tech Park Bangalore (ITPL, Whitefield)",
    category: "TECH",
    latitude: 12.9855,
    longitude: 77.7289,
    transitHint: "Purple Line Metro (ITPL Station)",
    sortOrder: 4,
  },
  {
    country: "IN",
    city: "Bengaluru",
    name: "Outer Ring Road (Bellandur / Ecospace)",
    category: "COMMERCIAL",
    latitude: 12.9260,
    longitude: 77.6762,
    transitHint: "ORR Transit Corridor",
    sortOrder: 5,
  },
  {
    country: "IN",
    city: "Bengaluru",
    name: "MG Road / Brigade Road CBD",
    category: "FINANCE",
    latitude: 12.9756,
    longitude: 77.6066,
    transitHint: "Purple Line Metro (MG Road Station)",
    sortOrder: 6,
  },

  // --- PUNE ---
  {
    country: "IN",
    city: "Pune",
    name: "Hinjewadi Rajiv Gandhi Infotech Park Phase 1",
    category: "TECH",
    latitude: 18.5913,
    longitude: 73.7389,
    transitHint: "Pune Metro Line 3 (Hinjewadi-Shivajinagar)",
    sortOrder: 1,
  },
  {
    country: "IN",
    city: "Pune",
    name: "Pune International Airport (PNQ, Lohegaon)",
    category: "AIRPORT",
    latitude: 18.5822,
    longitude: 73.9197,
    transitHint: "Airport Road Transit Shuttle",
    sortOrder: 2,
  },
  {
    country: "IN",
    city: "Pune",
    name: "Magarpatta Cybercity (Hadapsar)",
    category: "TECH",
    latitude: 18.5158,
    longitude: 73.9272,
    transitHint: "Solapur Road Corridor",
    sortOrder: 3,
  },
  {
    country: "IN",
    city: "Pune",
    name: "EON Free Zone / World Trade Center (Kharadi)",
    category: "TECH",
    latitude: 18.5515,
    longitude: 73.9515,
    transitHint: "Nagar Road Corridor & Ramwadi Metro",
    sortOrder: 4,
  },
  {
    country: "IN",
    city: "Pune",
    name: "Senapati Bapat Road / ICC Tech Park",
    category: "COMMERCIAL",
    latitude: 18.5314,
    longitude: 73.8298,
    transitHint: "Shivajinagar Metro Hub",
    sortOrder: 5,
  },
  {
    country: "IN",
    city: "Pune",
    name: "Pune Railway Station Central",
    category: "TRANSIT",
    latitude: 18.5284,
    longitude: 73.8744,
    transitHint: "Central Rail Terminal & Pune Metro Line 2",
    sortOrder: 6,
  },

  // --- MUMBAI ---
  {
    country: "IN",
    city: "Mumbai",
    name: "Bandra Kurla Complex (BKC Financial District)",
    category: "FINANCE",
    latitude: 19.0657,
    longitude: 72.8687,
    transitHint: "Metro Line 3 (Aqua Line) & BKC Connector",
    sortOrder: 1,
  },
  {
    country: "IN",
    city: "Mumbai",
    name: "Chhatrapati Shivaji Maharaj International Airport (BOM)",
    category: "AIRPORT",
    latitude: 19.0896,
    longitude: 72.8656,
    transitHint: "Metro Line 3 & Western Express Highway",
    sortOrder: 2,
  },
  {
    country: "IN",
    city: "Mumbai",
    name: "Nariman Point / Fort Financial Hub",
    category: "FINANCE",
    latitude: 18.9256,
    longitude: 72.8242,
    transitHint: "Churchgate / CSMT Suburban Rail Terminus",
    sortOrder: 3,
  },
  {
    country: "IN",
    city: "Mumbai",
    name: "Mindspace Malad / Goregaon IT Parks",
    category: "TECH",
    latitude: 19.1764,
    longitude: 72.8347,
    transitHint: "Metro Line 2A & Western Express Highway",
    sortOrder: 4,
  },
  {
    country: "IN",
    city: "Mumbai",
    name: "Hiranandani Business Park (Powai)",
    category: "COMMERCIAL",
    latitude: 19.1176,
    longitude: 72.9060,
    transitHint: "JVLR & Upcoming Metro Line 6",
    sortOrder: 5,
  },
  {
    country: "IN",
    city: "Mumbai",
    name: "Navi Mumbai International Airport (NMI)",
    category: "AIRPORT",
    latitude: 18.9912,
    longitude: 73.0673,
    transitHint: "Atal Setu (MTHL) Expressway",
    sortOrder: 6,
  },

  // --- GURGAON & DELHI NCR ---
  {
    country: "IN",
    city: "Gurgaon",
    name: "DLF Cyber City (Gurgaon)",
    category: "TECH",
    latitude: 28.4950,
    longitude: 77.0895,
    transitHint: "Rapid Metro Cyber City Station",
    sortOrder: 1,
  },
  {
    country: "IN",
    city: "Gurgaon",
    name: "Golf Course Road Commercial Belt",
    category: "COMMERCIAL",
    latitude: 28.4595,
    longitude: 77.0984,
    transitHint: "Rapid Metro Sector 54 Station",
    sortOrder: 2,
  },
  {
    country: "IN",
    city: "Delhi",
    name: "Indira Gandhi International Airport (DEL)",
    category: "AIRPORT",
    latitude: 28.5562,
    longitude: 77.1000,
    transitHint: "Airport Express Metro Line",
    sortOrder: 1,
  },
  {
    country: "IN",
    city: "Delhi",
    name: "Connaught Place Central Business District",
    category: "COMMERCIAL",
    latitude: 28.6315,
    longitude: 77.2167,
    transitHint: "Rajiv Chowk Metro Inter-change Hub",
    sortOrder: 2,
  },
  {
    country: "IN",
    city: "Noida",
    name: "Sector 62 IT & Media Hub (Noida)",
    category: "TECH",
    latitude: 28.6258,
    longitude: 77.3653,
    transitHint: "Blue Line Metro (Noida Electronic City)",
    sortOrder: 1,
  },

  // --- INDORE (coordinates from our OSM import) ---
  {
    country: "IN",
    city: "Indore",
    name: "Devi Ahilyabai Holkar Airport (IDR)",
    category: "AIRPORT",
    latitude: 22.7206,
    longitude: 75.8018,
    transitHint: "Airport Road",
    sortOrder: 1,
  },
  {
    country: "IN",
    city: "Indore",
    name: "Super Corridor IT Hub",
    category: "TECH",
    latitude: 22.7782,
    longitude: 75.8258,
    transitHint: "Super Corridor",
    sortOrder: 2,
  },
  {
    country: "IN",
    city: "Indore",
    name: "Vijay Nagar & AB Road Commercial Belt",
    category: "COMMERCIAL",
    latitude: 22.7513,
    longitude: 75.8943,
    transitHint: "AB Road",
    sortOrder: 3,
  },
  {
    country: "IN",
    city: "Indore",
    name: "Palasia Business District",
    category: "COMMERCIAL",
    latitude: 22.7248,
    longitude: 75.8872,
    transitHint: "AB Road",
    sortOrder: 4,
  },
  {
    country: "IN",
    city: "Indore",
    name: "Indore Junction Railway Station",
    category: "TRANSIT",
    latitude: 22.717,
    longitude: 75.8685,
    transitHint: "Western Railway mainline",
    sortOrder: 5,
  },
  {
    country: "IN",
    city: "Indore",
    name: "Pithampur Industrial Area",
    category: "COMMERCIAL",
    latitude: 22.6106,
    longitude: 75.679,
    transitHint: "Indore–Pithampur Road",
    sortOrder: 6,
  },

  // --- DUBAI (published landmark coordinates) ---
  {
    country: "AE",
    city: "Dubai",
    name: "Dubai International Airport (DXB)",
    category: "AIRPORT",
    latitude: 25.2528,
    longitude: 55.3644,
    transitHint: "Dubai Metro Red Line (Airport Terminals 1 & 3)",
    sortOrder: 1,
  },
  {
    country: "AE",
    city: "Dubai",
    name: "Dubai International Financial Centre (DIFC)",
    category: "FINANCE",
    latitude: 25.2131,
    longitude: 55.2825,
    transitHint: "Dubai Metro Red Line (Financial Centre)",
    sortOrder: 2,
  },
  {
    country: "AE",
    city: "Dubai",
    name: "Downtown Dubai & Business Bay",
    category: "COMMERCIAL",
    latitude: 25.1972,
    longitude: 55.2744,
    transitHint: "Dubai Metro Red Line (Burj Khalifa/Dubai Mall)",
    sortOrder: 3,
  },
  {
    country: "AE",
    city: "Dubai",
    name: "Dubai Internet City & Media City",
    category: "TECH",
    latitude: 25.0956,
    longitude: 55.16,
    transitHint: "Dubai Metro Red Line (Dubai Internet City)",
    sortOrder: 4,
  },
  {
    country: "AE",
    city: "Dubai",
    name: "Dubai Silicon Oasis",
    category: "TECH",
    latitude: 25.121,
    longitude: 55.377,
    sortOrder: 5,
  },
  {
    country: "AE",
    city: "Dubai",
    name: "Al Maktoum International Airport (DWC)",
    category: "AIRPORT",
    latitude: 24.8961,
    longitude: 55.1614,
    sortOrder: 6,
  },
];

async function seedCommuteHubs() {
  console.log("=== Seeding Canonical Commute Hubs (commute_hubs) ===");

  for (const hub of CANONICAL_HUBS) {
    await bunPG`
      INSERT INTO commute_hubs (
        id, country, city, name, category, latitude, longitude, "transitHint", "sortOrder", "isActive", "createdAt", "updatedAt"
      )
      VALUES (
        gen_random_uuid()::text,
        ${hub.country}::"CountryCode",
        ${hub.city},
        ${hub.name},
        ${hub.category}::"CommuteHubCategory",
        ${hub.latitude},
        ${hub.longitude},
        ${hub.transitHint || null},
        ${hub.sortOrder},
        true,
        NOW(),
        NOW()
      )
      ON CONFLICT (city, name) DO UPDATE SET
        category = EXCLUDED.category,
        latitude = EXCLUDED.latitude,
        longitude = EXCLUDED.longitude,
        "transitHint" = EXCLUDED."transitHint",
        "sortOrder" = EXCLUDED."sortOrder",
        "isActive" = true,
        "updatedAt" = NOW()
    `;
  }

  const [count] = await bunPG<Array<{ count: number }>>`SELECT count(*)::int FROM commute_hubs`;
  console.log(`✅ Loaded ${count?.count} commute hubs across operating cities.\n`);

  const summary = await bunPG<Array<{ city: string; count: number }>>`
    SELECT city, count(*)::int AS count
    FROM commute_hubs
    GROUP BY city
    ORDER BY city;
  `;
  console.table(summary);

  process.exit(0);
}

seedCommuteHubs().catch((err) => {
  console.error("Error seeding commute hubs:", err);
  process.exit(1);
});
