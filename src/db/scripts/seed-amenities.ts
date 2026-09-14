import { bunPG } from "../src/db/sql";

// ============================================================================
// Amenity Catalogue Seeder & High-Speed Set-Based Backfill (Phase 2, plan.md)
//
// 1. Seeds the canonical amenity catalogue (amenity_definitions) based on
//    Square Yards parity groups (Sports, Convenience, Safety, Leisure,
//    Environment, Property).
// 2. Maps the 64 legacy free-text amenity strings from `properties.amenities`
//    to canonical amenity codes and populates `property_amenities` in a SINGLE
//    set-based PostGIS SQL query.
// ============================================================================

interface AmenityDef {
  code: string;
  label: string;
  category: "SPORTS" | "CONVENIENCE" | "SAFETY" | "LEISURE" | "ENVIRONMENT" | "PROPERTY";
  scope: "SOCIETY" | "UNIT";
  icon: string;
  isFilterable: boolean;
  sortOrder: number;
}

export const CANONICAL_AMENITIES: AmenityDef[] = [
  // --- SPORTS ---
  { code: "GYMNASIUM", label: "Gymnasium", category: "SPORTS", scope: "SOCIETY", icon: "dumbbell", isFilterable: true, sortOrder: 1 },
  { code: "SWIMMING_POOL", label: "Swimming Pool", category: "SPORTS", scope: "SOCIETY", icon: "waves", isFilterable: true, sortOrder: 2 },
  { code: "BADMINTON_COURT", label: "Badminton Court", category: "SPORTS", scope: "SOCIETY", icon: "activity", isFilterable: true, sortOrder: 3 },
  { code: "TENNIS_COURT", label: "Tennis Court", category: "SPORTS", scope: "SOCIETY", icon: "circle-dot", isFilterable: false, sortOrder: 4 },
  { code: "SQUASH_COURT", label: "Squash Court", category: "SPORTS", scope: "SOCIETY", icon: "box", isFilterable: false, sortOrder: 5 },
  { code: "CRICKET_PITCH", label: "Cricket Pitch", category: "SPORTS", scope: "SOCIETY", icon: "shield", isFilterable: false, sortOrder: 6 },
  { code: "BASKETBALL_COURT", label: "Basketball Court", category: "SPORTS", scope: "SOCIETY", icon: "dribbble", isFilterable: false, sortOrder: 7 },
  { code: "KIDS_PLAY_AREA", label: "Kids' Play Area", category: "SPORTS", scope: "SOCIETY", icon: "smile", isFilterable: true, sortOrder: 8 },
  { code: "YOGA_AREA", label: "Yoga & Meditation Area", category: "SPORTS", scope: "SOCIETY", icon: "heart", isFilterable: false, sortOrder: 9 },
  { code: "JOGGING_TRACK", label: "Jogging / Cycle Track", category: "SPORTS", scope: "SOCIETY", icon: "footprints", isFilterable: true, sortOrder: 10 },
  { code: "TABLE_TENNIS", label: "Table Tennis", category: "SPORTS", scope: "SOCIETY", icon: "disc", isFilterable: false, sortOrder: 11 },
  { code: "SNOOKER_BILLIARDS", label: "Snooker / Billiards", category: "SPORTS", scope: "SOCIETY", icon: "circle", isFilterable: false, sortOrder: 12 },
  { code: "SKATING_RINK", label: "Skating Rink", category: "SPORTS", scope: "SOCIETY", icon: "wind", isFilterable: false, sortOrder: 13 },
  { code: "GOLF_COURSE", label: "Golf Course", category: "SPORTS", scope: "SOCIETY", icon: "flag", isFilterable: false, sortOrder: 14 },

  // --- CONVENIENCE ---
  { code: "POWER_BACKUP", label: "Power Backup", category: "CONVENIENCE", scope: "SOCIETY", icon: "zap", isFilterable: true, sortOrder: 15 },
  { code: "LIFT", label: "High-Speed Elevators", category: "CONVENIENCE", scope: "SOCIETY", icon: "arrow-up-down", isFilterable: true, sortOrder: 16 },
  { code: "TREATED_WATER", label: "Treated Water Supply", category: "CONVENIENCE", scope: "SOCIETY", icon: "droplet", isFilterable: false, sortOrder: 17 },
  { code: "WATER_24_7", label: "24×7 Water Supply", category: "CONVENIENCE", scope: "SOCIETY", icon: "droplets", isFilterable: true, sortOrder: 18 },
  { code: "CAR_WASH_BAY", label: "Car Wash Bay", category: "CONVENIENCE", scope: "SOCIETY", icon: "car", isFilterable: false, sortOrder: 19 },
  { code: "DRIVER_AREA", label: "Driver Rest Lounge", category: "CONVENIENCE", scope: "SOCIETY", icon: "coffee", isFilterable: false, sortOrder: 20 },
  { code: "GUEST_ROOMS", label: "Guest Rooms", category: "CONVENIENCE", scope: "SOCIETY", icon: "bed", isFilterable: false, sortOrder: 21 },
  { code: "EV_CHARGING", label: "EV Fast Charger", category: "CONVENIENCE", scope: "SOCIETY", icon: "battery-charging", isFilterable: true, sortOrder: 22 },
  { code: "ATTACHED_MARKET", label: "Attached Market / Convenience Store", category: "CONVENIENCE", scope: "SOCIETY", icon: "shopping-bag", isFilterable: true, sortOrder: 23 },
  { code: "MEDICAL_FACILITY", label: "First Aid / Medical Facility", category: "CONVENIENCE", scope: "SOCIETY", icon: "cross", isFilterable: false, sortOrder: 24 },
  { code: "SEPARATE_ENTRY_EXIT", label: "Separate Entry & Exit Gates", category: "CONVENIENCE", scope: "SOCIETY", icon: "door-open", isFilterable: false, sortOrder: 25 },
  { code: "AC_LOBBY", label: "Air-Conditioned Waiting Lobby", category: "CONVENIENCE", scope: "SOCIETY", icon: "fan", isFilterable: false, sortOrder: 26 },
  { code: "CONCIERGE", label: "Concierge Service", category: "CONVENIENCE", scope: "SOCIETY", icon: "bell", isFilterable: false, sortOrder: 27 },
  { code: "VALET_PARKING", label: "Valet Parking", category: "CONVENIENCE", scope: "SOCIETY", icon: "key", isFilterable: false, sortOrder: 28 },
  { code: "HELIPAD", label: "Helipad", category: "CONVENIENCE", scope: "SOCIETY", icon: "plane-landing", isFilterable: false, sortOrder: 58 },

  // --- SAFETY ---
  { code: "SECURITY_24_7", label: "24×7 Security & Guard Patrol", category: "SAFETY", scope: "SOCIETY", icon: "shield-check", isFilterable: true, sortOrder: 29 },
  { code: "CCTV", label: "CCTV Video Surveillance", category: "SAFETY", scope: "SOCIETY", icon: "video", isFilterable: true, sortOrder: 30 },
  { code: "BIOMETRIC_ACCESS", label: "Biometric / Access-Controlled Entry", category: "SAFETY", scope: "SOCIETY", icon: "fingerprint", isFilterable: false, sortOrder: 31 },
  { code: "FIRE_SAFETY", label: "Fire Fighting & Sprinkler System", category: "SAFETY", scope: "SOCIETY", icon: "flame", isFilterable: true, sortOrder: 32 },
  { code: "INTERCOM", label: "Intercom Facility", category: "SAFETY", scope: "SOCIETY", icon: "phone-call", isFilterable: false, sortOrder: 33 },

  // --- LEISURE ---
  { code: "CLUBHOUSE", label: "Clubhouse", category: "LEISURE", scope: "SOCIETY", icon: "home", isFilterable: true, sortOrder: 34 },
  { code: "CAFE", label: "Cafe / Coffee Lounge", category: "LEISURE", scope: "SOCIETY", icon: "cup-soda", isFilterable: false, sortOrder: 35 },
  { code: "MINI_THEATRE", label: "Private Screening Cinema", category: "LEISURE", scope: "SOCIETY", icon: "film", isFilterable: false, sortOrder: 36 },
  { code: "LIBRARY", label: "Library & Reading Lounge", category: "LEISURE", scope: "SOCIETY", icon: "book-open", isFilterable: false, sortOrder: 37 },
  { code: "AMPHITHEATRE", label: "Amphitheatre", category: "LEISURE", scope: "SOCIETY", icon: "music", isFilterable: false, sortOrder: 38 },
  { code: "INDOOR_GAMES", label: "Indoor Games Room", category: "LEISURE", scope: "SOCIETY", icon: "gamepad-2", isFilterable: false, sortOrder: 39 },
  { code: "SPA_SAUNA", label: "Spa & Steam / Sauna", category: "LEISURE", scope: "SOCIETY", icon: "sparkles", isFilterable: false, sortOrder: 40 },
  { code: "FOOD_COURT", label: "Food Court", category: "LEISURE", scope: "SOCIETY", icon: "utensils", isFilterable: false, sortOrder: 41 },
  { code: "SKY_LOUNGE", label: "Sky Lounge & Terrace Deck", category: "LEISURE", scope: "SOCIETY", icon: "sun", isFilterable: false, sortOrder: 42 },
  { code: "PARTY_HALL", label: "Multipurpose Party Hall", category: "LEISURE", scope: "SOCIETY", icon: "party-popper", isFilterable: false, sortOrder: 43 },
  { code: "PRIVATE_BEACH", label: "Private Beach Access", category: "LEISURE", scope: "SOCIETY", icon: "umbrella", isFilterable: false, sortOrder: 56 },
  { code: "MARINA_BERTH", label: "Marina / Yacht Berth", category: "LEISURE", scope: "SOCIETY", icon: "sailboat", isFilterable: false, sortOrder: 57 },

  // --- ENVIRONMENT ---
  { code: "RAINWATER_HARVESTING", label: "Rainwater Harvesting", category: "ENVIRONMENT", scope: "SOCIETY", icon: "cloud-rain", isFilterable: true, sortOrder: 44 },
  { code: "SEWAGE_TREATMENT_PLANT", label: "Sewage Treatment Plant (STP)", category: "ENVIRONMENT", scope: "SOCIETY", icon: "recycle", isFilterable: false, sortOrder: 45 },
  { code: "SOLAR_WATER_HEATING", label: "Solar Water Heating", category: "ENVIRONMENT", scope: "SOCIETY", icon: "sun-medium", isFilterable: true, sortOrder: 46 },
  { code: "LARGE_GREEN_AREA", label: "Large Landscaped Garden", category: "ENVIRONMENT", scope: "SOCIETY", icon: "trees", isFilterable: true, sortOrder: 47 },
  { code: "WASTE_MANAGEMENT", label: "Solid Waste Management", category: "ENVIRONMENT", scope: "SOCIETY", icon: "trash-2", isFilterable: false, sortOrder: 48 },
  { code: "GREEN_RATED", label: "IGBC / GRIHA Green Certified", category: "ENVIRONMENT", scope: "SOCIETY", icon: "leaf", isFilterable: true, sortOrder: 49 },

  // --- PROPERTY (UNIT SCOPE) ---
  { code: "PRIVATE_POOL", label: "Private Plunge Pool", category: "PROPERTY", scope: "UNIT", icon: "waves", isFilterable: true, sortOrder: 50 },
  { code: "PRIVATE_TERRACE", label: "Private Terrace Garden", category: "PROPERTY", scope: "UNIT", icon: "flower-2", isFilterable: true, sortOrder: 51 },
  { code: "SMART_HOME", label: "Smart Home Automation", category: "PROPERTY", scope: "UNIT", icon: "cpu", isFilterable: true, sortOrder: 52 },
  { code: "FIBRE_INTERNET", label: "High-Speed Fibre Internet", category: "PROPERTY", scope: "UNIT", icon: "wifi", isFilterable: false, sortOrder: 53 },
  { code: "SERVANT_ROOM", label: "Servant / Maid's Quarters", category: "PROPERTY", scope: "UNIT", icon: "user-check", isFilterable: true, sortOrder: 54 },
  { code: "COVERED_PARKING", label: "Covered Reserved Parking", category: "PROPERTY", scope: "UNIT", icon: "car", isFilterable: true, sortOrder: 55 },
];

/**
 * Mapping of legacy free-text strings to one or more canonical codes.
 */
export const LEGACY_MAPPINGS: Array<{ raw: string; code: string; detail: string | null }> = [
  { raw: "24/7 Power Backup (100% DG)", code: "POWER_BACKUP", detail: "100% DG backup" },
  { raw: "100% Power Backup for Full Flat", code: "POWER_BACKUP", detail: "100% backup for full flat" },
  { raw: "Dedicated EV 7.4kW Fast Charger", code: "EV_CHARGING", detail: "Dedicated 7.4kW Fast Charger" },
  { raw: "Tesla/EV Level-2 Fast Charger", code: "EV_CHARGING", detail: "Level-2 Fast Charger" },
  { raw: "Electric Vehicle Multi-Charger Infrastructure", code: "EV_CHARGING", detail: "Multi-charger infrastructure" },
  { raw: "Clubhouse & 25m Heated Lap Pool", code: "CLUBHOUSE", detail: "Clubhouse" },
  { raw: "Clubhouse & 25m Heated Lap Pool", code: "SWIMMING_POOL", detail: "25m heated lap pool" },
  { raw: "State-of-the-art Gymnasium & Yoga Studio", code: "GYMNASIUM", detail: "State-of-the-art gymnasium" },
  { raw: "State-of-the-art Gymnasium & Yoga Studio", code: "YOGA_AREA", detail: "Yoga studio" },
  { raw: "Biometric Access Lobby & 3-Tier Security", code: "BIOMETRIC_ACCESS", detail: "Biometric access lobby" },
  { raw: "Biometric Access Lobby & 3-Tier Security", code: "SECURITY_24_7", detail: "3-tier security" },
  { raw: "Biometric Access Lobby", code: "BIOMETRIC_ACCESS", detail: null },
  { raw: "24/7 Armed Society Perimeter Patrol", code: "SECURITY_24_7", detail: "Armed perimeter patrol" },
  { raw: "Rainwater Harvesting & Solar Water Heating", code: "RAINWATER_HARVESTING", detail: null },
  { raw: "Rainwater Harvesting & Solar Water Heating", code: "SOLAR_WATER_HEATING", detail: null },
  { raw: "Solar Water Heating", code: "SOLAR_WATER_HEATING", detail: null },
  { raw: "Children's Play Area & Landscaped Garden", code: "KIDS_PLAY_AREA", detail: "Children's play area" },
  { raw: "Children's Play Area & Landscaped Garden", code: "LARGE_GREEN_AREA", detail: "Landscaped garden" },
  { raw: "Children's Play Area & Crèche", code: "KIDS_PLAY_AREA", detail: "Play area & crèche" },
  { raw: "24/7 Quintessentially Luxury Concierge", code: "CONCIERGE", detail: "24/7 Quintessentially Luxury Concierge" },
  { raw: "24/7 Concierge by Quintessentially", code: "CONCIERGE", detail: "Concierge by Quintessentially" },
  { raw: "Concierge Service & Valet Parking", code: "CONCIERGE", detail: "Concierge service" },
  { raw: "Concierge Service & Valet Parking", code: "VALET_PARKING", detail: "Valet parking" },
  { raw: "Chauffeur & Valet Basement Parking", code: "VALET_PARKING", detail: "Chauffeur & valet parking" },
  { raw: "Direct Skybridge Access to Retail Galleria", code: "ATTACHED_MARKET", detail: "Skybridge access to retail galleria" },
  { raw: "Integrated Orion Mall Skywalk", code: "ATTACHED_MARKET", detail: "Integrated mall skywalk" },
  { raw: "Burj Khalifa & Palm Panoramic Sky Lounge", code: "SKY_LOUNGE", detail: "Panoramic sky lounge" },
  { raw: "Armani / Casa Designed Sky Lounge", code: "SKY_LOUNGE", detail: "Armani/Casa designed sky lounge" },
  { raw: "Rooftop Infinity Pool & Sky Deck", code: "SWIMMING_POOL", detail: "Rooftop infinity pool" },
  { raw: "Rooftop Infinity Pool & Sky Deck", code: "SKY_LOUNGE", detail: "Sky deck" },
  { raw: "Temperature-Controlled Infinity Horizon Pool", code: "SWIMMING_POOL", detail: "Temperature-controlled infinity pool" },
  { raw: "Olympic Size Swimming Pool & Badminton Courts", code: "SWIMMING_POOL", detail: "Olympic size swimming pool" },
  { raw: "Olympic Size Swimming Pool & Badminton Courts", code: "BADMINTON_COURT", detail: "Badminton courts" },
  { raw: "Heated Swimming Pool & Tennis Court", code: "SWIMMING_POOL", detail: "Heated swimming pool" },
  { raw: "Heated Swimming Pool & Tennis Court", code: "TENNIS_COURT", detail: "Tennis court" },
  { raw: "Heated Indoor Pool & Squash Courts", code: "SWIMMING_POOL", detail: "Heated indoor pool" },
  { raw: "Heated Indoor Pool & Squash Courts", code: "SQUASH_COURT", detail: "Squash courts" },
  { raw: "Swimming Pool & Gymnasium", code: "SWIMMING_POOL", detail: null },
  { raw: "Swimming Pool & Gymnasium", code: "GYMNASIUM", detail: null },
  { raw: "Private Plunge Pool & Sun Deck", code: "PRIVATE_POOL", detail: "Private plunge pool with sun deck" },
  { raw: "Private Heated Plunge Pool", code: "PRIVATE_POOL", detail: "Private heated plunge pool" },
  { raw: "Hydrotherapy Spa & Turkish Hammam", code: "SPA_SAUNA", detail: "Hydrotherapy spa & Turkish hammam" },
  { raw: "Six Senses Luxury Spa & Hydrotherapy Pool", code: "SPA_SAUNA", detail: "Luxury spa & hydrotherapy pool" },
  { raw: "Falcon Greens 5-Star Club & Spa", code: "CLUBHOUSE", detail: "5-star club" },
  { raw: "Falcon Greens 5-Star Club & Spa", code: "SPA_SAUNA", detail: "Spa facility" },
  { raw: "Private Beach Access & Yacht Marina Berth", code: "PRIVATE_BEACH", detail: null },
  { raw: "Private Beach Access & Yacht Marina Berth", code: "MARINA_BERTH", detail: null },
  { raw: "Smart Home Automation by Control4 / Lutron", code: "SMART_HOME", detail: "Control4 / Lutron automation" },
  { raw: "Fibre to the Home & Smart Home Automation", code: "SMART_HOME", detail: "Home automation" },
  { raw: "Fibre to the Home & Smart Home Automation", code: "FIBRE_INTERNET", detail: "Fibre to the home" },
  { raw: "High-speed 300 Mbps Fibre Installed", code: "FIBRE_INTERNET", detail: "300 Mbps fibre" },
  { raw: "Private Screening Cinema (20-30 Seats)", code: "MINI_THEATRE", detail: "20-30 seats screening room" },
  { raw: "Private Screening Cinema (24 Seats)", code: "MINI_THEATRE", detail: "24 seats cinema" },
  { raw: "Squash & Badminton International Courts", code: "SQUASH_COURT", detail: "International squash court" },
  { raw: "Squash & Badminton International Courts", code: "BADMINTON_COURT", detail: "International badminton court" },
  { raw: "Badminton & Squash Courts", code: "BADMINTON_COURT", detail: null },
  { raw: "Badminton & Squash Courts", code: "SQUASH_COURT", detail: null },
  { raw: "18-Hole PGA Standard Golf Course", code: "GOLF_COURSE", detail: "18-hole PGA standard golf course" },
  { raw: "Private Earth Terrace Garden with Automatic Sprinklers", code: "PRIVATE_TERRACE", detail: "Private earth terrace with sprinklers" },
  { raw: "Private Sky Deck with National Park Views", code: "PRIVATE_TERRACE", detail: "Sky deck with panoramic views" },
  { raw: "Covered Reserved Stilt Car Parking", code: "COVERED_PARKING", detail: "Covered stilt parking" },
  { raw: "Direct High-Speed Elevators (6 m/s)", code: "LIFT", detail: "6 m/s high speed" },
  { raw: "Water Filtration & RO Plant", code: "TREATED_WATER", detail: "RO filtration plant" },
  { raw: "100% Centralized Water Softening", code: "TREATED_WATER", detail: "Centralized water softener" },
  { raw: "Kaveri Water Supply Direct", code: "WATER_24_7", detail: "Kaveri water direct" },
  { raw: "IGBC Gold Rated Green Building", code: "GREEN_RATED", detail: "IGBC Gold Rated" },
  { raw: "Zero Water Runoff Zero Waste Society", code: "WASTE_MANAGEMENT", detail: "Zero waste society" },
  { raw: "Zero Water Runoff Zero Waste Society", code: "RAINWATER_HARVESTING", detail: "Zero water runoff" },
  { raw: "Lake Promenade & Running Track", code: "JOGGING_TRACK", detail: "Lake promenade running track" },
  { raw: "Helipad & Chauffeur Waiting Lounge", code: "HELIPAD", detail: null },
  { raw: "Helipad & Chauffeur Waiting Lounge", code: "DRIVER_AREA", detail: "Chauffeur waiting lounge" },
  { raw: "Helipad Access on Request", code: "HELIPAD", detail: "Access on request" },
  { raw: "Helipad Access on Society Tower", code: "HELIPAD", detail: "On the society tower" },
  { raw: "Microbrewery on Premises", code: "CAFE", detail: "Microbrewery on premises" },
  { raw: "25-Acre Integrated Master Planned Development", code: "LARGE_GREEN_AREA", detail: "25-acre township greens" },
];

/**
 * Rows written by earlier versions of the mapping above that misstated what a
 * listing claims (a beach and marina berth recorded as a clubhouse; a helipad
 * recorded as concierge). The backfill deletes them, CLAIMED rows only: a
 * VERIFIED or NOT_FOUND row is an engineer's decision and is never touched.
 */
const RETIRED_MAPPINGS: Array<{ code: string; detail: string }> = [
  { code: "CLUBHOUSE", detail: "Beach access & marina berth" },
  { code: "CONCIERGE", detail: "Helipad booking assistance" },
];

async function seedAmenities() {
  console.log(`=== 1. Upserting ${CANONICAL_AMENITIES.length} Canonical Amenity Definitions ===`);
  for (const item of CANONICAL_AMENITIES) {
    await bunPG`
      INSERT INTO amenity_definitions (
        code, label, category, scope, icon, "isFilterable", "sortOrder", "isActive", "createdAt", "updatedAt"
      )
      VALUES (
        ${item.code},
        ${item.label},
        ${item.category}::"AmenityCategory",
        ${item.scope}::"AmenityScope",
        ${item.icon},
        ${item.isFilterable},
        ${item.sortOrder},
        true,
        NOW(),
        NOW()
      )
      ON CONFLICT (code) DO UPDATE SET
        label = EXCLUDED.label,
        category = EXCLUDED.category,
        scope = EXCLUDED.scope,
        icon = EXCLUDED.icon,
        "isFilterable" = EXCLUDED."isFilterable",
        "sortOrder" = EXCLUDED."sortOrder",
        "updatedAt" = NOW()
    `;
  }
  const [countDef] = await bunPG<Array<{ count: number }>>`SELECT count(*)::int FROM amenity_definitions`;
  console.log(`✅ Loaded ${countDef?.count} canonical amenity definitions.\n`);

  console.log("=== 2. Removing rows written by retired mappings ===");
  for (const retired of RETIRED_MAPPINGS) {
    const removed = await bunPG`
      DELETE FROM property_amenities
      WHERE "amenityCode" = ${retired.code}
        AND detail = ${retired.detail}
        AND status = 'CLAIMED'::"AmenityStatus"
    `;
    console.log(`  ${retired.code} "${retired.detail}": ${removed.count} removed`);
  }

  console.log("\n=== 3. Executing Set-Based Property Amenities Backfill ===");
  const t0 = performance.now();

  let ruleIndex = 0;
  for (const m of LEGACY_MAPPINGS) {
    ruleIndex++;
    await bunPG`
      INSERT INTO property_amenities ("propertyId", "amenityCode", status, detail, "createdAt", "updatedAt")
      SELECT DISTINCT p.id, ${m.code}, 'CLAIMED'::"AmenityStatus", ${m.detail}, NOW(), NOW()
      FROM properties p
      WHERE ${m.raw} = ANY(p.amenities)
      ON CONFLICT ("propertyId", "amenityCode") DO NOTHING;
    `;
  }

  const durationMs = (performance.now() - t0).toFixed(2);
  console.log(`✅ Set-based backfill completed in ${durationMs}ms across ${ruleIndex} mapping rules.`);

  const [totalPropAmenities] = await bunPG<Array<{ count: number }>>`SELECT count(*)::int FROM property_amenities`;
  console.log(`\n🎉 Total rows in property_amenities: ${totalPropAmenities?.count}`);

  process.exit(0);
}

seedAmenities().catch((err) => {
  console.error("Error seeding amenities:", err);
  process.exit(1);
});
