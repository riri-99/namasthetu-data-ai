/**
 * Dev seed: load the public website's 8 mock listings into Postgres.
 *
 *   bun run seed:listings
 *
 * Source: namasethu-frontend-web/src/data/mockProperties1.ts (MOCK_PROPERTIES).
 * Override with MOCK_LISTINGS_PATH=<absolute path>.
 *
 * Idempotent. Every row is keyed on a natural or deterministic key and only
 * written when a value actually differs, so a second run reports 0 created /
 * 0 updated:
 *   users               phone
 *   owner_profiles      userId
 *   inspector_profiles  userId
 *   properties          slug
 *   listings            publicId  (list_<sha(slug)>)
 *   inspections         publicId  (insp_seed_<mock inspection id>)
 *   digital_twins       propertyId
 *   ai_valuations       (propertyId, generatedAt) - the seed's own valuation
 *   deed_history_events replaced per property, only when the chain differs
 *   neighbourhood_intelligence propertyId
 *
 * Refuses to run with BUN_ENV=production. All bank / licence / UPI values are
 * obviously fake dev placeholders.
 *
 * Bun notes: timestamps are passed as ISO strings with an explicit ::timestamp
 * cast (a JS Date serialises as "... GMT+0530", which Postgres rejects);
 * arrays and JSON go through `$n::text::jsonb` because unsafe() neither
 * serialises JS arrays as text[] nor leaves pre-stringified JSON alone.
 */
import crypto from "crypto";
import { tmpdir } from "os";
import { join, resolve } from "path";
import { unlink } from "fs/promises";
import type { SQL } from "bun";

if (Bun.env.BUN_ENV === "production") {
  console.error("[seed-listings] Refusing to run with BUN_ENV=production. This is a dev-only seed.");
  process.exit(1);
}

// ============================================================================
// Mock shape (the subset of the frontend's PropertyListing this seed reads)
// ============================================================================

interface MockListing {
  id: string;
  slug: string;
  title: string;
  locality: string;
  city: string;
  state: string;
  coordinates: { lat: number; lng: number };
  listingMode: "BUY" | "RENT";
  category: string[];
  propertyType: string;
  configuration: string;
  bathrooms: number;
  carpetAreaSqft: number;
  superBuiltUpAreaSqft: number;
  floor: string;
  facing: string;
  waterSupply: string;
  pricePaise: string;
  maintenanceMonthlyPaise?: string;
  images: string[];
  has3dTour: boolean;
  spatialRooms?: unknown[];
  trustScore: number;
  verifiedOwnerBadge: boolean;
  topBadge?: string;
  inspection: {
    id: string;
    inspectorName: string;
    inspectionDate: string;
    scores: {
      composite: number;
      structural: number;
      plumbing: number;
      electrical: number;
      finishes: number;
      cadastral: number;
    };
    verifiedPointsCount: number;
    seepageDetected: boolean;
    activeLiens: boolean;
    summary: string;
    keyFindings: unknown[];
    pdfUrl?: string;
  };
  valuation: {
    fairMarketPricePaise: string;
    listedPricePaise: string;
    differencePercentage: number;
    marketPosition: "BELOW_AVM" | "FAIR_MARKET" | "PREMIUM";
    grossYieldPercentage?: number;
    monthlyRentalEstimatePaise?: string;
    projected5YrAppreciation: string;
    historicalTransactionsCount: number;
  };
  deedHistory: Array<{
    year: string;
    eventType: string;
    title: string;
    parties: string;
    volumeNumber?: string;
    status: string;
  }>;
  owner: {
    fullName: string;
    avatarUrl: string;
    joinedDate: string;
    responseTime: string;
    unredactedPhone?: string;
    unredactedWhatsApp?: string;
  };
  amenities: string[];
  neighbourhood: {
    metroDistanceMeters: number;
    schoolsNearby: string[];
    hospitalNearby: string;
    waterSecurityIndex: string;
  };
  availableFrom: string;
  ulpin: string;
  reraNumber?: string;
}

function resolveMockPath(): string {
  if (Bun.env.MOCK_LISTINGS_PATH) return Bun.env.MOCK_LISTINGS_PATH;
  const arg = process.argv[2];
  if (arg && !arg.startsWith("-")) {
    if (arg.includes("/") || arg.includes("\\")) return resolve(arg);
    const fileName = arg.endsWith(".ts") ? arg : `${arg}.ts`;
    return resolve(import.meta.dir, `../../../namasethu-frontend-web/src/data/${fileName}`);
  }
  return resolve(import.meta.dir, "./data/mockProperties.ts");
}

const MOCK_PATH = resolveMockPath();

/**
 * Bun imports the TS file directly (its only import is type-only and gets
 * elided). If that ever breaks - e.g. a value import through the "@/" alias,
 * which only resolves inside the frontend - fall back to a temp copy with the
 * alias imports stripped.
 */
async function loadMockListings(): Promise<MockListing[]> {
  let mod: { MOCK_PROPERTIES?: unknown };
  try {
    mod = await import(MOCK_PATH);
  } catch (err) {
    console.warn(`[seed-listings] Direct import failed (${(err as Error).message}); retrying via stripped copy.`);
    const src = await Bun.file(MOCK_PATH).text();
    const stripped = src.replace(/^\s*import\s[^;]*?from\s+["']@\/[^"']+["'];?\s*$/gm, "");
    const tmp = join(tmpdir(), `seed-listings-mock-${process.pid}.ts`);
    await Bun.write(tmp, stripped);
    try {
      mod = await import(tmp);
    } finally {
      await unlink(tmp).catch(() => {});
    }
  }
  const list = mod.MOCK_PROPERTIES;
  if (!Array.isArray(list) || list.length === 0) {
    throw new Error(`MOCK_PROPERTIES missing or empty in ${MOCK_PATH}`);
  }
  for (const p of list as MockListing[]) {
    if (!p?.slug || !p.owner?.unredactedPhone || !p.inspection || !p.valuation) {
      throw new Error(`Mock listing ${p?.id ?? "?"} is missing slug/owner phone/inspection/valuation`);
    }
  }
  return list as MockListing[];
}

// ============================================================================
// Mapping helpers (site labels -> DB values)
// ============================================================================

/** "Within N days" is relative; pin it to a fixed date so re-runs stay no-ops. */
const SEED_REFERENCE_DATE = "2026-09-14";
const SEED_REFERENCE_TS = `${SEED_REFERENCE_DATE}T00:00:00`;
/** Age is derived from the earliest title event, against this fixed year. */
const SEED_REFERENCE_YEAR = 2026;

const sha = (s: string) => crypto.createHash("sha256").update(s).digest("hex");

const PROPERTY_TYPE: Record<string, string> = {
  Apartment: "APARTMENT",
  Villa: "VILLA",
  Penthouse: "PENTHOUSE",
  "Independent Floor": "INDEPENDENT_HOUSE",
};

const MARKET_POSITION: Record<string, string> = {
  BELOW_AVM: "BELOW_MARKET",
  FAIR_MARKET: "ALIGNED",
  PREMIUM: "ABOVE_MARKET",
};

const DEED_EVENT_TYPES = new Set(["SALE_DEED", "KHATA_TRANSFER", "ENCUMBRANCE_CLEARED", "ULPIN_SEEDED", "INSPECTION_AUDIT"]);
const DEED_EVENT_STATUSES = new Set(["VERIFIED", "CLEARED"]);

/** The mock has no street address or pincode; these are real streets/pincodes for each locality. */
const ADDRESS_BY_SLUG: Record<string, { street: string; pincode: string }> = {
  "sobha-silicon-oasis-3bhk": { street: "Hosa Road, Electronic City Phase 1", pincode: "560100" },
  "prestige-golfshire-luxury-villa": { street: "Nandi Hills Road, Karahalli Post, Devanahalli", pincode: "562110" },
  "lodha-world-towers-3bhk": { street: "Senapati Bapat Marg, Upper Worli, Lower Parel", pincode: "400013" },
  "total-environment-windmills-4bhk": { street: "EPIP Zone, Whitefield Main Road", pincode: "560066" },
  "puravankara-silicon-heights-rent": { street: "100 Feet Road, HAL 2nd Stage, Indiranagar", pincode: "560038" },
  "brigade-gateway-lakeview-2bhk": { street: "26/1 Dr. Rajkumar Road, Rajajinagar", pincode: "560055" },
  "oberoi-sky-city-penthouse": { street: "Off Western Express Highway, Datta Pada Road, Borivali East", pincode: "400066" },
  "embassy-pristine-lakeview-rent": { street: "Iblur Village, Bellandur Outer Ring Road", pincode: "560103" },
};
const DEFAULT_PINCODE_BY_CITY: Record<string, string> = {
  Bengaluru: "560001",
  Mumbai: "400001",
  Pune: "411001",
  Indore: "452001",
  Dubai: "00000",
};

/** Normalise phone to E.164 (+<country_code><digits>). */
function normalisePhone(raw: string): string {
  const digits = raw.replace(/\D/g, "");
  if (raw.trim().startsWith("+")) return `+${digits}`;
  if (digits.length === 10) return `+91${digits}`;
  if (digits.length === 12 && digits.startsWith("91")) return `+${digits}`;
  return `+${digits}`;
}

/** "< 45 minutes" -> 45, "< 1 hour" -> 60. */
function parseResponseMinutes(s: string): number | null {
  const m = s.match(/(\d+(?:\.\d+)?)\s*(minute|min|hour|hr)/i);
  if (!m) return null;
  const n = Number(m[1]);
  return Math.round(/^h/i.test(m[2]) ? n * 60 : n);
}

const MONTHS: Record<string, string> = {
  jan: "01", feb: "02", mar: "03", apr: "04", may: "05", jun: "06",
  jul: "07", aug: "08", sep: "09", oct: "10", nov: "11", dec: "12",
};

/** "15 Feb 2026" -> "2026-02-15". */
function parseDayMonthYear(s: string): string {
  const m = s.trim().match(/^(\d{1,2})\s+([A-Za-z]{3})[a-z]*\s+(\d{4})$/);
  const mm = m && MONTHS[m[2].toLowerCase()];
  if (!m || !mm) throw new Error(`Unrecognised date: ${s}`);
  return `${m[3]}-${mm}-${m[1].padStart(2, "0")}`;
}

/** "October 2024" -> "2024-10-01". */
function parseMonthYear(s: string): string {
  const m = s.trim().match(/^([A-Za-z]{3})[a-z]*\s+(\d{4})$/);
  const mm = m && MONTHS[m[1].toLowerCase()];
  if (!m || !mm) throw new Error(`Unrecognised month: ${s}`);
  return `${m[2]}-${mm}-01`;
}

/** Add days to "YYYY-MM-DD", returning "YYYY-MM-DD". */
function addDays(date: string, days: number): string {
  const d = new Date(`${date}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/**
 * "8th of 14 Floors" -> 8/14; "G + 2 Independent Villa" -> ground (0) of 3;
 * "11th & 12th Floor Duplex" -> 11/unknown. The label itself has no column.
 */
function parseFloor(s: string): { floorNumber: number | null; totalFloors: number | null } {
  let m = s.match(/^(\d+)(?:st|nd|rd|th)?\s+of\s+(\d+)/i);
  if (m) return { floorNumber: Number(m[1]), totalFloors: Number(m[2]) };
  m = s.match(/^G\s*\+\s*(\d+)/i);
  if (m) return { floorNumber: 0, totalFloors: Number(m[1]) + 1 };
  m = s.match(/^(\d+)(?:st|nd|rd|th)/i);
  if (m) return { floorNumber: Number(m[1]), totalFloors: null };
  return { floorNumber: null, totalFloors: null };
}

/** "North-East" -> "NORTH_EAST". */
function mapFacing(s: string): string {
  const v = s.trim().toUpperCase().replace(/[\s-]+/g, "_");
  if (!["NORTH", "SOUTH", "EAST", "WEST", "NORTH_EAST", "NORTH_WEST", "SOUTH_EAST", "SOUTH_WEST"].includes(v)) {
    throw new Error(`Unrecognised facing: ${s}`);
  }
  return v;
}

/** Null means ready to move in. "Within 15 Days" -> reference date + 15. */
function parseAvailableFrom(s: string): string | null {
  const within = s.match(/within\s+(\d+)\s+days?/i);
  if (within) return addDays(SEED_REFERENCE_DATE, Number(within[1]));
  if (/immediate|ready to move|move in/i.test(s)) return null;
  throw new Error(`Unrecognised availableFrom: ${s}`);
}

/**
 * "+44% (Airport corridor expansion)" -> { pct: 44, driver: "Airport corridor expansion" }.
 * RENT mocks put a yield here instead ("Rental Yield: 4.9% p.a.") -> { yieldPct: 4.9 }.
 */
function parseOutlook(s: string): { pct: number | null; driver: string | null; yieldPct: number | null } {
  const y = s.match(/yield:\s*([\d.]+)\s*%/i);
  if (y) return { pct: null, driver: null, yieldPct: Number(y[1]) };
  const m = s.trim().match(/^([+-]?\d+(?:\.\d+)?)\s*%\s*(?:\((.+)\))?/);
  if (m) return { pct: Number(m[1]), driver: m[2]?.trim() || null, yieldPct: null };
  return { pct: null, driver: null, yieldPct: null };
}

/** "High (92/100) — On-site deep aquifer" -> { index: 92, note: "On-site deep aquifer" }. */
function parseWaterSecurity(s: string): { index: number | null; note: string | null } {
  const idx = s.match(/\((\d+)\s*\/\s*100\)/);
  const note = s.split(/\s+[—–-]\s+/).slice(1).join(" — ").trim();
  return { index: idx ? Number(idx[1]) : null, note: note || null };
}

/** "Sobha Silicon Oasis 3BHK with ..." -> "Sobha Silicon Oasis". */
function buildingNameFrom(title: string): string {
  const m = title.match(/^(.*?)\s+\d\s*BHK\b/i);
  return (m ? m[1] : title).trim();
}

function formatCurrency(paise: bigint, currency: string = "INR"): string {
  const amount = Number(paise) / 100;
  if (currency === "AED") return `AED ${amount.toLocaleString("en-AE")}`;
  if (amount >= 1e7) return `₹${(amount / 1e7).toFixed(2)} Cr`;
  if (amount >= 1e5) return `₹${(amount / 1e5).toFixed(2)} L`;
  return `₹${amount.toLocaleString("en-IN")}`;
}

// ============================================================================
// SQL builder: column specs -> parameterised upserts that skip no-op updates
// ============================================================================

type Db = Pick<SQL, "unsafe">;

/** One column: a SQL template whose {0}, {1}... are bound to `vs`. */
interface Col {
  vs: unknown[];
  tpl: string;
  /** Include in the "did anything change" comparison (default true). */
  compare?: boolean;
  /** Only written on insert; an existing row keeps its value. */
  insertOnly?: boolean;
}

const c = (v: unknown, cast: string): Col => ({ vs: [v ?? null], tpl: `{0}::${cast}` });
const txt = (v: string | null | undefined) => c(v ?? null, "text");
const int = (v: number | null | undefined) => c(v ?? null, "int");
const dbl = (v: number | null | undefined) => c(v ?? null, "double precision");
const bool = (v: boolean | null | undefined) => c(v ?? null, "boolean");
const big = (v: bigint | string | null | undefined) => c(v == null ? null : String(v), "bigint");
const ts = (iso: string | null | undefined) => c(iso ?? null, "timestamp");
const en = (v: string | null | undefined, enumName: string) => c(v ?? null, `"${enumName}"`);
const json = (v: unknown) => ({ vs: [v == null ? null : JSON.stringify(v)], tpl: "{0}::text::jsonb" });
const textArr = (a: string[]): Col => ({
  vs: [JSON.stringify(a)],
  tpl: "ARRAY(SELECT x FROM jsonb_array_elements_text({0}::text::jsonb) WITH ORDINALITY AS t(x, n) ORDER BY n)",
});
const raw = (sqlText: string, extra: Partial<Col> = {}): Col => ({ vs: [], tpl: sqlText, ...extra });

const q = (name: string) => `"${name}"`;

function render(cols: Record<string, Col>, params: unknown[]): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [name, col] of Object.entries(cols)) {
    const base = params.length;
    params.push(...col.vs);
    out[name] = col.tpl.replace(/\{(\d+)\}/g, (_, i: string) => `$${base + Number(i) + 1}`);
  }
  return out;
}

type Action = "created" | "updated" | "unchanged";

interface Counter {
  created: number;
  updated: number;
  unchanged: number;
  deleted: number;
}
const stats: Record<string, Counter> = {};
function bump(table: string, action: Action | "deleted", n = 1) {
  stats[table] ??= { created: 0, updated: 0, unchanged: 0, deleted: 0 };
  stats[table][action] += n;
}

/**
 * INSERT ... ON CONFLICT (key) DO UPDATE ... WHERE (current) IS DISTINCT FROM (new).
 * An identical row produces no write at all, so updatedAt does not churn.
 */
// ---- commute matrix ---------------------------------------------------------
// Estimated from each listing's real coordinates to fixed hubs: straight-line
// distance × ROAD_FACTOR for the road network, at a typical off-peak city speed,
// with a peak-hour multiplier. Estimates, not live traffic, but they differ per
// home, unlike the single per-city list the page used to hard-code.
interface CommuteHubDef {
  hub: string;
  category: "FINANCE" | "AIRPORT" | "TECH" | "COMMERCIAL";
  lat: number;
  lng: number;
  transitMode: "DRIVE" | "METRO" | "RAIL";
  transitOption: string;
}

const HUBS_BY_CITY: Record<string, CommuteHubDef[]> = {
  Bengaluru: [
    { hub: "Kempegowda Int. Airport (BLR)", category: "AIRPORT", lat: 13.1986, lng: 77.7066, transitMode: "DRIVE", transitOption: "Airport Road via Hebbal flyover" },
    { hub: "Central Business District (MG Road)", category: "FINANCE", lat: 12.9756, lng: 77.6066, transitMode: "METRO", transitOption: "Namma Metro Purple Line" },
    { hub: "Outer Ring Road (Bellandur)", category: "TECH", lat: 12.926, lng: 77.6762, transitMode: "DRIVE", transitOption: "Outer Ring Road" },
    { hub: "Electronic City Phase 1", category: "TECH", lat: 12.8456, lng: 77.6603, transitMode: "DRIVE", transitOption: "Hosur Road elevated expressway" },
  ],
  Mumbai: [
    { hub: "Bandra Kurla Complex (BKC)", category: "FINANCE", lat: 19.066, lng: 72.868, transitMode: "DRIVE", transitOption: "Western Express Highway / BKC Connector" },
    { hub: "Nariman Point", category: "FINANCE", lat: 18.9256, lng: 72.8242, transitMode: "DRIVE", transitOption: "Mumbai Coastal Road" },
    { hub: "CSM Int. Airport (BOM) T2", category: "AIRPORT", lat: 19.099, lng: 72.874, transitMode: "DRIVE", transitOption: "Western Express Highway" },
    { hub: "Lower Parel", category: "COMMERCIAL", lat: 18.9953, lng: 72.83, transitMode: "RAIL", transitOption: "Western Railway local" },
  ],
  Pune: [
    { hub: "Pune International Airport (PNQ)", category: "AIRPORT", lat: 18.5822, lng: 73.9197, transitMode: "DRIVE", transitOption: "Airport Road via Yerawada" },
    { hub: "Hinjewadi Rajiv Gandhi Infotech Park", category: "TECH", lat: 18.5913, lng: 73.7389, transitMode: "DRIVE", transitOption: "Mumbai-Pune Expressway bypass" },
    { hub: "Kharadi EON Free Zone", category: "TECH", lat: 18.5518, lng: 73.9515, transitMode: "DRIVE", transitOption: "Mundhwa-Kharadi Road" },
    { hub: "Shivajinagar / FC Road", category: "COMMERCIAL", lat: 18.5314, lng: 73.8446, transitMode: "METRO", transitOption: "Pune Metro Line 1" },
  ],
  Dubai: [
    { hub: "Dubai International Airport (DXB) T3", category: "AIRPORT", lat: 25.2532, lng: 55.3657, transitMode: "DRIVE", transitOption: "Airport Road (D89) / E11" },
    { hub: "DIFC / Downtown Dubai", category: "FINANCE", lat: 25.2048, lng: 55.2708, transitMode: "METRO", transitOption: "Dubai Metro Red Line" },
    { hub: "Dubai Media City / Internet City", category: "TECH", lat: 25.0934, lng: 55.1565, transitMode: "METRO", transitOption: "Dubai Metro Red Line" },
    { hub: "Business Bay Commercial Tower Hub", category: "COMMERCIAL", lat: 25.1837, lng: 55.2665, transitMode: "DRIVE", transitOption: "Al Khail Road (E44)" },
  ],
  Indore: [
    { hub: "Devi Ahilya Bai Holkar Airport (IDR)", category: "AIRPORT", lat: 22.7217, lng: 75.8011, transitMode: "DRIVE", transitOption: "Aerodrome Road" },
    { hub: "Super Corridor IT Hub", category: "TECH", lat: 22.7533, lng: 75.8937, transitMode: "DRIVE", transitOption: "Super Corridor Road" },
    { hub: "Vijay Nagar Commercial Square", category: "COMMERCIAL", lat: 22.7533, lng: 75.8937, transitMode: "DRIVE", transitOption: "AB Road (BRTS)" },
  ],
};
const OFF_PEAK_SPEED_KMH: Record<string, number> = { Bengaluru: 26, Mumbai: 24, Pune: 28, Dubai: 45, Indore: 30 };
const PEAK_FACTOR = 1.8;
const ROAD_FACTOR = 1.35;

function haversineKm(aLat: number, aLng: number, bLat: number, bLng: number): number {
  const rad = (d: number) => (d * Math.PI) / 180;
  const dLat = rad(bLat - aLat);
  const dLng = rad(bLng - aLng);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(aLat)) * Math.cos(rad(bLat)) * Math.sin(dLng / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(h));
}

function commuteMatrixFor(city: string, lat: number, lng: number) {
  const speed = OFF_PEAK_SPEED_KMH[city] ?? 25;
  return (HUBS_BY_CITY[city] ?? []).map((h) => {
    const distanceKm = Math.round(haversineKm(lat, lng, h.lat, h.lng) * ROAD_FACTOR * 10) / 10;
    const offPeakMins = Math.max(5, Math.round((distanceKm / speed) * 60));
    return {
      hub: h.hub,
      category: h.category,
      distanceKm,
      offPeakMins,
      peakMins: Math.round(offPeakMins * PEAK_FACTOR),
      transitMode: h.transitMode,
      transitOption: h.transitOption,
    };
  });
}

function airportDistanceMetersFor(city: string, lat: number, lng: number): number | null {
  const airport = (HUBS_BY_CITY[city] ?? []).find((h) => h.category === "AIRPORT");
  return airport ? Math.round(haversineKm(lat, lng, airport.lat, airport.lng) * ROAD_FACTOR * 1000) : null;
}

async function upsert(
  db: Db,
  table: string,
  conflict: string[],
  cols: Record<string, Col>,
  opts: { updatedAt?: boolean } = {},
): Promise<{ id: string; action: Action }> {
  const withUpdatedAt = opts.updatedAt ?? true;
  const params: unknown[] = [];
  const exprs = render(cols, params);
  const names = Object.keys(cols);

  const insertNames = ["id", ...names, ...(withUpdatedAt ? ["updatedAt"] : [])];
  const insertVals = ["gen_random_uuid()", ...names.map((n) => exprs[n]), ...(withUpdatedAt ? ["NOW()"] : [])];

  const updatable = names.filter((n) => !conflict.includes(n) && !cols[n].insertOnly);
  const compared = updatable.filter((n) => cols[n].compare !== false);
  const setList = [
    ...updatable.map((n) => `${q(n)} = EXCLUDED.${q(n)}`),
    ...(withUpdatedAt ? [`"updatedAt" = NOW()`] : []),
  ];

  const sqlText = `
    INSERT INTO ${table} (${insertNames.map(q).join(", ")})
    VALUES (${insertVals.join(", ")})
    ON CONFLICT (${conflict.map(q).join(", ")}) DO UPDATE SET ${setList.join(", ")}
    WHERE (${compared.map((n) => `${table}.${q(n)}`).join(", ")})
          IS DISTINCT FROM (${compared.map((n) => `EXCLUDED.${q(n)}`).join(", ")})
    RETURNING id, (xmax = 0) AS inserted`;

  const rows = (await db.unsafe(sqlText, params)) as Array<{ id: string; inserted: boolean }>;
  let result: { id: string; action: Action };
  if (rows.length > 0) {
    result = { id: rows[0].id, action: rows[0].inserted ? "created" : "updated" };
  } else {
    const keyParams: unknown[] = [];
    const keyExprs = render(Object.fromEntries(conflict.map((k) => [k, cols[k]])), keyParams);
    const found = (await db.unsafe(
      `SELECT id FROM ${table} WHERE ${conflict.map((k) => `${q(k)} = ${keyExprs[k]}`).join(" AND ")} LIMIT 1`,
      keyParams,
    )) as Array<{ id: string }>;
    if (!found[0]) throw new Error(`${table}: conflict row vanished for ${conflict.join(",")}`);
    result = { id: found[0].id, action: "unchanged" };
  }
  bump(table, result.action);
  return result;
}

/**
 * For tables with no unique key to conflict on: find by `key`, then insert or
 * update-if-different.
 */
async function syncByKey(
  db: Db,
  table: string,
  key: Record<string, Col>,
  cols: Record<string, Col>,
): Promise<{ id: string; action: Action }> {
  const keyParams: unknown[] = [];
  const keyExprs = render(key, keyParams);
  const found = (await db.unsafe(
    `SELECT id FROM ${table} WHERE ${Object.keys(key).map((k) => `${q(k)} = ${keyExprs[k]}`).join(" AND ")}
     ORDER BY id LIMIT 1`,
    keyParams,
  )) as Array<{ id: string }>;

  let result: { id: string; action: Action };
  if (!found[0]) {
    const all = { ...key, ...cols };
    const params: unknown[] = [];
    const exprs = render(all, params);
    const names = Object.keys(all);
    const rows = (await db.unsafe(
      `INSERT INTO ${table} ("id", ${names.map(q).join(", ")})
       VALUES (gen_random_uuid(), ${names.map((n) => exprs[n]).join(", ")}) RETURNING id`,
      params,
    )) as Array<{ id: string }>;
    result = { id: rows[0].id, action: "created" };
  } else {
    const params: unknown[] = [found[0].id];
    const exprs = render(cols, params);
    const names = Object.keys(cols);
    const rows = (await db.unsafe(
      `UPDATE ${table} SET ${names.map((n) => `${q(n)} = ${exprs[n]}`).join(", ")}
       WHERE id = $1
         AND (${names.map((n) => `${table}.${q(n)}`).join(", ")})
             IS DISTINCT FROM (${names.map((n) => exprs[n]).join(", ")})
       RETURNING id`,
      params,
    )) as Array<{ id: string }>;
    result = { id: found[0].id, action: rows.length ? "updated" : "unchanged" };
  }
  bump(table, result.action);
  return result;
}

// ============================================================================
// Inspectors (shared across listings, so upserted up front)
// ============================================================================

interface InspectorSeed {
  key: string;
  fullName: string;
  phone: string;
  city: string;
  pincodes: string[];
  inspections: number;
}

/**
 * The mock spells the same engineer two ways ("Er. Ramesh S. Rao, M.Tech Civil"
 * and "... M.Tech Civil (NICMAR)"), so inspectors are keyed on the name before
 * the credentials comma and keep the most complete spelling.
 */
function collectInspectors(listings: MockListing[]): Map<string, InspectorSeed> {
  const map = new Map<string, InspectorSeed>();
  const cityCount = new Map<string, Map<string, number>>();
  for (const p of listings) {
    const full = p.inspection.inspectorName.trim();
    const key = full.split(",")[0].trim();
    const pincode = (ADDRESS_BY_SLUG[p.slug]?.pincode ?? DEFAULT_PINCODE_BY_CITY[p.city]) || null;
    let seed = map.get(key);
    if (!seed) {
      const n = parseInt(sha(`inspector:${key}`).slice(0, 8), 16) % 100000;
      seed = { key, fullName: full, phone: `+9190000${String(n).padStart(5, "0")}`, city: p.city, pincodes: [], inspections: 0 };
      map.set(key, seed);
      cityCount.set(key, new Map());
    }
    if (full.length > seed.fullName.length) seed.fullName = full;
    if (pincode && !seed.pincodes.includes(pincode)) seed.pincodes.push(pincode);
    seed.inspections += 1;
    const cc = cityCount.get(key)!;
    cc.set(p.city, (cc.get(p.city) ?? 0) + 1);
  }
  for (const [key, seed] of map) {
    seed.city = [...cityCount.get(key)!.entries()].sort((a, b) => b[1] - a[1])[0][0];
    seed.pincodes.sort();
  }
  const phones = new Set([...map.values()].map((s) => s.phone));
  if (phones.size !== map.size) throw new Error("Inspector dev phone collision; adjust the hash scheme");
  return map;
}

async function upsertInspector(db: Db, s: InspectorSeed): Promise<string> {
  const user = await upsert(db, "users", ["phone"], {
    phone: txt(s.phone),
    publicId: { ...txt(`user_${sha(s.phone).slice(0, 16)}`), insertOnly: true },
    fullName: txt(s.fullName),
    role: en("INSPECTOR", "UserRole"),
    kycStatus: en("BASIC_KYC", "UserKycStatus"),
    phoneVerifiedAt: raw("NOW()", { insertOnly: true }),
    residenceCountry: txt("IN"),
  });
  const h = sha(s.key).slice(0, 6).toUpperCase();
  const profile = await upsert(db, "inspector_profiles", ["userId"], {
    userId: txt(user.id),
    licenseNumber: txt(`DEV-SEED-CIVIL-${h}`),
    agencyName: txt("Amberstone Field Assurance (dev seed)"),
    operatingCity: txt(s.city),
    servicePincodes: textArr(s.pincodes),
    payoutUpiId: txt(`devseed.${h.toLowerCase()}@fakeupi`),
    totalInspections: int(s.inspections),
  });
  return profile.id;
}

// ============================================================================
// One listing
// ============================================================================

interface CategoryCheck {
  slug: string;
  mock: string[];
  derived: string[];
}

async function seedListing(db: Db, p: MockListing, inspectorProfileId: string): Promise<CategoryCheck> {
  // ---- derived values ----------------------------------------------------
  const phone = normalisePhone(p.owner.unredactedPhone!);
  const joined = parseMonthYear(p.owner.joinedDate);
  const inspDay = parseDayMonthYear(p.inspection.inspectionDate);
  const scheduledAt = `${inspDay}T10:00:00`;
  const startedAt = `${inspDay}T10:20:00`;
  const completedAt = `${inspDay}T13:30:00`;
  const capturedAt = `${inspDay}T12:45:00`;
  const valuedAt = `${addDays(inspDay, 1)}T12:00:00`;
  const activatedAt = `${addDays(inspDay, 3)}T09:00:00`;

  const propertyType = PROPERTY_TYPE[p.propertyType];
  if (!propertyType) throw new Error(`${p.slug}: unmapped propertyType ${p.propertyType}`);
  const marketPosition = MARKET_POSITION[p.valuation.marketPosition];
  if (!marketPosition) throw new Error(`${p.slug}: unmapped marketPosition ${p.valuation.marketPosition}`);

  const { floorNumber, totalFloors } = parseFloor(p.floor);
  const address = ADDRESS_BY_SLUG[p.slug];
  const buildingName = buildingNameFrom(p.title);
  const streetAddress = address ? `${buildingName}, ${address.street}` : `${buildingName}, ${p.locality}`;
  const pincode = address?.pincode ?? DEFAULT_PINCODE_BY_CITY[p.city] ?? null;

  const price = BigInt(p.pricePaise);
  const estimate = BigInt(p.valuation.fairMarketPricePaise);
  const listed = BigInt(p.valuation.listedPricePaise);
  const outlook = parseOutlook(p.valuation.projected5YrAppreciation);
  const grossYield = p.valuation.grossYieldPercentage ?? outlook.yieldPct;
  const monthlyRentEstimate =
    p.valuation.monthlyRentalEstimatePaise != null
      ? BigInt(p.valuation.monthlyRentalEstimatePaise)
      : p.listingMode === "RENT"
        ? estimate
        : null;
  const water = parseWaterSecurity(p.neighbourhood.waterSecurityIndex);
  const isGated = p.category.includes("GATED_COMMUNITIES");

  const titleYears = p.deedHistory
    .filter((e) => e.eventType !== "INSPECTION_AUDIT")
    .map((e) => Number(e.year))
    .filter(Number.isFinite);
  const ageYears = titleYears.length ? SEED_REFERENCE_YEAR - Math.min(...titleYears) : null;

  const isDubai = p.city === "Dubai" || (p.state && p.state.toLowerCase().includes("dubai"));
  const country = isDubai ? "AE" : "IN";
  const currency = isDubai ? "AED" : "INR";

  // ---- 1. owner ------------------------------------------------------------
  const owner = await upsert(db, "users", ["phone"], {
    phone: txt(phone),
    publicId: { ...txt(`user_${sha(phone).slice(0, 16)}`), insertOnly: true },
    fullName: txt(p.owner.fullName),
    avatarUrl: txt(p.owner.avatarUrl),
    role: en("OWNER", "UserRole"),
    kycStatus: en("ENHANCED_OWNER", "UserKycStatus"),
    phoneVerifiedAt: ts(`${joined}T09:00:00`),
    kycCompletedAt: ts(`${addDays(joined, 2)}T11:00:00`),
    responseTimeMinutes: int(parseResponseMinutes(p.owner.responseTime)),
    responseTimeComputedAt: ts(SEED_REFERENCE_TS),
    lastActiveAt: raw("NOW()", { insertOnly: true }),
    residenceCountry: txt(country),
    whatsappOptIn: bool(Boolean(p.owner.unredactedWhatsApp)),
    whatsappOptInAt: ts(p.owner.unredactedWhatsApp ? `${joined}T09:00:00` : null),
    createdAt: ts(`${joined}T09:00:00`),
  });

  const oh = sha(`owner:${phone}`).slice(0, 10);
  await upsert(db, "owner_profiles", ["userId"], {
    userId: txt(owner.id),
    bankAccountNumber: txt(`DEVSEED000${oh.replace(/[a-f]/g, "0")}`),
    bankIfsc: txt("DEVS0000000"),
    beneficiaryName: txt(p.owner.fullName),
    razorpayContactId: txt(`cont_devseed_${oh}`),
    isNri: bool(isDubai),
  });

  // ---- 2. property -------------------------------------------------------
  const property = await upsert(db, "properties", ["slug"], {
    slug: txt(p.slug),
    publicId: { ...txt(`prop_${sha(p.slug).slice(0, 16)}`), insertOnly: true },
    ulpin: txt(p.ulpin),
    reraNumber: txt(p.reraNumber ?? null),
    status: en("ACTIVE_LISTING", "PropertyStatus"),
    verificationScore: int(p.trustScore),
    title: txt(p.title),
    country: en(country, "CountryCode"),
    listingMode: en(p.listingMode, "ListingMode"),
    currency: en(currency, "CurrencyCode"),
    ownerId: txt(owner.id),
    propertyType: en(propertyType, "PropertyType"),
    configuration: txt(p.configuration),
    bathrooms: int(p.bathrooms),
    carpetAreaSqft: dbl(p.carpetAreaSqft),
    superBuiltUpAreaSqft: dbl(p.superBuiltUpAreaSqft),
    floorNumber: int(floorNumber),
    totalFloors: int(totalFloors),
    facing: en(mapFacing(p.facing), "FacingDirection"),
    ageYears: int(ageYears),
    waterSupply: txt(p.waterSupply),
    availableFrom: ts(parseAvailableFrom(p.availableFrom)),
    isGatedCommunity: bool(isGated),
    buildingName: txt(buildingName),
    streetAddress: txt(streetAddress),
    locality: txt(p.locality),
    city: txt(p.city),
    state: txt(p.state),
    pincode: txt(pincode),
    latitude: dbl(p.coordinates.lat),
    longitude: dbl(p.coordinates.lng),
    locationSource: en("MAP_PIN", "LocationSource"),
    // Derived from latitude/longitude, which are compared instead.
    geom: {
      vs: [p.coordinates.lng, p.coordinates.lat],
      tpl: "ST_SetSRID(ST_MakePoint({0}::double precision, {1}::double precision), 4326)::geography",
      compare: false,
    },
    askingPriceMinor: big(p.listingMode === "BUY" ? price : null),
    monthlyRentMinor: big(p.listingMode === "RENT" ? price : null),
    maintenanceMonthlyMinor: big(p.maintenanceMonthlyPaise ?? null),
    images: textArr(p.images),
    amenities: textArr(p.amenities),
    verifiedOwnerBadge: bool(p.verifiedOwnerBadge),
    topBadge: txt(p.topBadge ?? null),
    lastInspectedAt: ts(completedAt),
    seepageDetected: bool(p.inspection.seepageDetected),
    avmDifferencePct: dbl(p.valuation.differencePercentage),
    grossYieldPct: dbl(grossYield ?? null),
  });
  const propertyId = property.id;
  // Rows created before this column set existed could lack geom; never leave it null.
  await db.unsafe(
    `UPDATE properties SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::geography
     WHERE id = $1 AND geom IS NULL`,
    [propertyId],
  );

  // ---- 3. listing --------------------------------------------------------
  await upsert(db, "listings", ["publicId"], {
    publicId: txt(`list_${sha(p.slug).slice(0, 16)}`),
    propertyId: txt(propertyId),
    status: en("ACTIVE", "ListingStatus"),
    listingPriceMinor: big(price),
    lqaScore: int(p.trustScore),
    lqaPassed: bool(true),
    activatedAt: ts(activatedAt),
  });

  // ---- 4. digital twin ---------------------------------------------------
  if (p.has3dTour) {
    await upsert(db, "digital_twins", ["propertyId"], {
      propertyId: txt(propertyId),
      publicId: { ...txt(`twin_${sha(p.slug).slice(0, 16)}`), insertOnly: true },
      // The site's ThreeTwinViewer renders procedurally from spatialRooms and
      // loads no model file, so this is a deliberate placeholder.
      modelUrl: txt(`https://placeholder.invalid/dev-seed/digital-twins/${p.slug}.glb`),
      captureMethod: en("MATTERPORT", "CaptureMethod"),
      qualityScore: int(p.inspection.scores.composite),
      spatialRooms: json(p.spatialRooms ?? []),
      capturedAt: ts(capturedAt),
    });
  } else {
    const removed = (await db.unsafe(`DELETE FROM digital_twins WHERE "propertyId" = $1 RETURNING id`, [
      propertyId,
    ])) as unknown[];
    if (removed.length) bump("digital_twins", "deleted", removed.length);
  }

  // ---- 5. inspection -----------------------------------------------------
  const s = p.inspection.scores;
  await upsert(db, "inspections", ["publicId"], {
    publicId: txt(`insp_seed_${p.inspection.id.replace(/[^A-Za-z0-9]/g, "").replace(/^insp/i, "")}`),
    propertyId: txt(propertyId),
    inspectorId: txt(inspectorProfileId),
    status: en("QA_PASSED", "InspectionStatus"),
    scheduledDate: ts(scheduledAt),
    startedAt: ts(startedAt),
    completedAt: ts(completedAt),
    checkInLatitude: dbl(p.coordinates.lat),
    checkInLongitude: dbl(p.coordinates.lng),
    checkInDistanceMeters: dbl(0),
    scoreOverall: int(s.composite),
    scoreStructural: int(s.structural),
    scorePlumbing: int(s.plumbing),
    scoreElectrical: int(s.electrical),
    scoreFinishes: int(s.finishes),
    scoreCadastral: int(s.cadastral),
    summary: txt(p.inspection.summary),
    keyFindings: json(p.inspection.keyFindings),
    verifiedPointsCount: int(p.inspection.verifiedPointsCount),
    seepageDetected: bool(p.inspection.seepageDetected),
    activeLiens: bool(p.inspection.activeLiens),
    reportPdfUrl: txt(p.inspection.pdfUrl ?? null),
  });

  // ---- 6. valuation ------------------------------------------------------
  const pctText = `${Math.abs(p.valuation.differencePercentage).toFixed(1)}%`;
  const gap =
    p.valuation.differencePercentage < 0
      ? `${pctText} below the estimate`
      : p.valuation.differencePercentage > 0
        ? `${pctText} above the estimate`
        : "in line with the estimate";
  const narrative = [
    `${p.listingMode === "RENT" ? "Fair monthly rent" : "Fair market value"} estimated at ${formatCurrency(estimate, currency)} ` +
      `for this ${p.configuration} ${p.propertyType.toLowerCase()} in ${p.locality}, ${p.city}, ` +
      `from ${p.valuation.historicalTransactionsCount} registered comparable transactions.`,
    `The ${p.listingMode === "RENT" ? "asking rent" : "asking price"} of ${formatCurrency(listed, currency)} sits ${gap}.`,
    grossYield != null ? `Gross rental yield ${grossYield}%.` : "",
    outlook.pct != null
      ? `Five-year outlook ${outlook.pct >= 0 ? "+" : ""}${outlook.pct}%${outlook.driver ? `, driven by ${outlook.driver}` : ""}.`
      : "",
  ]
    .filter(Boolean)
    .join(" ");

  await syncByKey(
    db,
    "ai_valuations",
    { propertyId: txt(propertyId), generatedAt: ts(valuedAt) },
    {
      estimateMinor: big(estimate),
      confidenceLowMinor: big((estimate * 96n) / 100n),
      confidenceHighMinor: big((estimate * 104n) / 100n),
      marketPosition: txt(marketPosition),
      demandSignal: txt("WARM"),
      narrativeSummary: txt(narrative),
      listedPriceMinor: big(listed),
      differencePercentage: dbl(p.valuation.differencePercentage),
      grossYieldPercentage: dbl(grossYield ?? null),
      monthlyRentalEstimateMinor: big(monthlyRentEstimate),
      projected5YrAppreciationPct: dbl(outlook.pct),
      appreciationDriver: txt(outlook.driver),
      historicalTransactionsCount: int(p.valuation.historicalTransactionsCount),
    },
  );

  // ---- 7. deed history (replaced only when the chain differs) ------------
  const desired = p.deedHistory.map((e, i) => {
    if (!DEED_EVENT_TYPES.has(e.eventType)) throw new Error(`${p.slug}: unmapped deed eventType ${e.eventType}`);
    if (!DEED_EVENT_STATUSES.has(e.status)) throw new Error(`${p.slug}: unmapped deed status ${e.status}`);
    return {
      eventType: e.eventType,
      status: e.status,
      year: Number(e.year),
      title: e.title,
      parties: e.parties,
      registrationVolume: e.volumeNumber ?? null,
      sequenceOrder: i,
      verifiedAt: completedAt,
    };
  });
  const existing = (await db.unsafe(
    `SELECT "eventType"::text AS "eventType", status::text AS status, year, title, parties,
            "registrationVolume", "sequenceOrder",
            to_char("verifiedAt", 'YYYY-MM-DD"T"HH24:MI:SS') AS "verifiedAt"
     FROM deed_history_events WHERE "propertyId" = $1
     ORDER BY "sequenceOrder", year DESC, id`,
    [propertyId],
  )) as Array<Record<string, unknown>>;
  const normalise = (rows: Array<Record<string, unknown>>) =>
    JSON.stringify(
      rows.map((r) => [r.eventType, r.status, Number(r.year), r.title, r.parties, r.registrationVolume ?? null, Number(r.sequenceOrder), r.verifiedAt]),
    );
  if (normalise(existing) === normalise(desired)) {
    bump("deed_history_events", "unchanged", desired.length);
  } else {
    if (existing.length) {
      await db.unsafe(`DELETE FROM deed_history_events WHERE "propertyId" = $1`, [propertyId]);
      bump("deed_history_events", "deleted", existing.length);
    }
    for (const e of desired) {
      const params: unknown[] = [];
      const cols: Record<string, Col> = {
        propertyId: txt(propertyId),
        eventType: en(e.eventType, "DeedEventType"),
        status: en(e.status, "DeedEventStatus"),
        year: int(e.year),
        title: txt(e.title),
        parties: txt(e.parties),
        registrationVolume: txt(e.registrationVolume),
        sequenceOrder: int(e.sequenceOrder),
        verifiedAt: ts(e.verifiedAt),
      };
      const exprs = render(cols, params);
      const names = Object.keys(cols);
      await db.unsafe(
        `INSERT INTO deed_history_events ("id", ${names.map(q).join(", ")}, "updatedAt")
         VALUES (gen_random_uuid(), ${names.map((n) => exprs[n]).join(", ")}, NOW())`,
        params,
      );
    }
    bump("deed_history_events", "created", desired.length);
  }

  // ---- 8. neighbourhood --------------------------------------------------
  // Flood drainage, tree canopy and air quality are deliberately left unset:
  // there is no real source for them yet, and the page shows "Not assessed".
  const commute = commuteMatrixFor(p.city, p.coordinates.lat, p.coordinates.lng);
  await upsert(db, "neighbourhood_intelligence", ["propertyId"], {
    propertyId: txt(propertyId),
    metroDistanceMeters: int(p.neighbourhood.metroDistanceMeters),
    schoolsNearby: textArr(p.neighbourhood.schoolsNearby),
    hospitalNearby: txt(p.neighbourhood.hospitalNearby),
    waterSecurityIndex: int(water.index),
    waterSecurityNote: txt(water.note),
    airportDistanceMeters: int(airportDistanceMetersFor(p.city, p.coordinates.lat, p.coordinates.lng)),
    commuteMatrixJson: json(commute.length ? commute : null),
    computedAt: ts(completedAt),
  });

  // ---- category derivation preview (same rules the API applies) ---------
  const derived: string[] = [];
  if (p.verifiedOwnerBadge) derived.push("DIRECT_OWNER");
  if (p.has3dTour) derived.push("DIGITAL_TWIN");
  if (p.valuation.differencePercentage <= -3) derived.push("TOP_AVM_DEALS");
  if (p.trustScore >= 95) derived.push("TRUST_PASS_ELITE");
  if (isGated) derived.push("GATED_COMMUNITIES");
  if (p.reraNumber) derived.push("RERA_APPROVED");
  if (propertyType === "VILLA" || propertyType === "PLOT_LAND") derived.push("VILLAS_PLOTS");
  if (grossYield != null && grossYield >= 4) derived.push("HIGH_RENTAL_YIELD");
  return { slug: p.slug, mock: p.category, derived };
}

// ============================================================================
// Main
// ============================================================================

export async function seedListings(): Promise<void> {
  const { bunPG, closeSql } = await import("../src/db/sql");
  try {
    const listings = await loadMockListings();
    console.log(`[seed-listings] Loaded ${listings.length} mock listings from ${MOCK_PATH}`);

    const inspectorSeeds = collectInspectors(listings);
    const inspectorIds = new Map<string, string>();
    for (const seed of inspectorSeeds.values()) {
      inspectorIds.set(seed.key, await bunPG.begin((tx) => upsertInspector(tx, seed)));
    }

    const checks: CategoryCheck[] = [];
    const total = listings.length;
    console.log(`[seed-listings] Seeding ${total} listings...`);
    const startTime = Date.now();
    for (let i = 0; i < total; i++) {
      const p = listings[i];
      const key = p.inspection.inspectorName.split(",")[0].trim();
      const inspectorId = inspectorIds.get(key)!;
      checks.push(await bunPG.begin((tx) => seedListing(tx, p, inspectorId)));
      if ((i + 1) % 500 === 0 || i + 1 === total) {
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
        const rate = ((i + 1) / ((Date.now() - startTime) / 1000)).toFixed(0);
        console.log(`[seed-listings] Seeded ${i + 1}/${total} listings (${elapsed}s, ~${rate}/s)...`);
      }
    }

    console.log("\n[seed-listings] Summary (rows):");
    console.table(stats);

    const mismatches = checks
      .map((ch) => ({
        slug: ch.slug,
        extra: ch.derived.filter((x) => !ch.mock.includes(x)),
        missing: ch.mock.filter((x) => !ch.derived.includes(x)),
      }))
      .filter((m) => m.extra.length || m.missing.length);
    if (mismatches.length) {
      console.log(`[seed-listings] Derived categories differ from mock's \`category\` array for ${mismatches.length} listings:`);
      for (const m of mismatches.slice(0, 10)) {
        console.log(
          `  ${m.slug}: ${m.extra.length ? `+${m.extra.join(" +")}` : ""}${m.missing.length ? ` -${m.missing.join(" -")}` : ""}`,
        );
      }
      if (mismatches.length > 10) {
        console.log(`  ... and ${mismatches.length - 10} more.`);
      }
    } else {
      console.log("[seed-listings] Derived categories match the mock for every listing.");
    }
  } finally {
    await closeSql();
  }
}

if (import.meta.main) {
  seedListings()
    .then(() => process.exit(0))
    .catch((err) => {
      console.error("[seed-listings] Failed:", err);
      process.exit(1);
    });
}
