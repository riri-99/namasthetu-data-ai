/**
 * Production Ingestion Pipeline: OpenStreetMap GeoPackage (.gpkg) -> PostgreSQL + PostGIS
 *
 * Ingests high-density civic & spatial GIS data (POIs, transport, places, water, landuse)
 * across Indian zones directly into indexed PostGIS tables.
 *
 * Usage:
 *   bun run scripts/ingest-osm-gpkg.ts             # Ingests southern, western, central by default
 *   bun run scripts/ingest-osm-gpkg.ts --all       # Ingests all 6 zones of India
 *   bun run scripts/ingest-osm-gpkg.ts southern    # Ingests specific zone
 */
import { Database } from "bun:sqlite";
import { existsSync, readdirSync } from "fs";
import { join } from "path";
import { bunPG, closeSql } from "../src/db/sql";

interface ZoneFile {
  zone: string;
  name: string;
  path: string;
}

const DOWNLOADS_DIR = "C:/Users/dcode/Downloads";

function findGpkgFiles(): ZoneFile[] {
  const result: ZoneFile[] = [];
  const entries = readdirSync(DOWNLOADS_DIR, { withFileTypes: true });

  for (const entry of entries) {
    if (entry.isDirectory() && entry.name.includes("-zone-")) {
      const folderPath = join(DOWNLOADS_DIR, entry.name);
      const innerFiles = readdirSync(folderPath);
      const gpkg = innerFiles.find((f) => f.endsWith(".gpkg"));
      if (gpkg) {
        const zoneKey = entry.name.replace(/-\d+.*$/, "");
        result.push({
          zone: zoneKey,
          name: entry.name,
          path: join(folderPath, gpkg).replace(/\\/g, "/"),
        });
      }
    }
  }
  return result;
}

function extractWkbHex(geomBuf: Uint8Array): string {
  const buf = Buffer.from(geomBuf);
  const flags = buf[3];
  const envelopeType = (flags >> 1) & 0x07;
  let headerSize = 8;
  if (envelopeType === 1) headerSize += 32;
  else if (envelopeType === 2 || envelopeType === 3) headerSize += 48;
  else if (envelopeType === 4) headerSize += 64;
  return buf.subarray(headerSize).toString("hex");
}

async function initPostGisSchema() {
  console.log("[ingest-osm] Initializing PostGIS tables & spatial indices...");

  await bunPG.unsafe(`
    -- Ensure PostGIS extension is active
    CREATE EXTENSION IF NOT EXISTS postgis;

    -- 1. POIs (Schools, Hospitals, Clinics, Banks, Supermarkets, etc.)
    CREATE TABLE IF NOT EXISTS osm_pois (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      zone TEXT NOT NULL,
      osm_id TEXT NOT NULL,
      code INTEGER,
      fclass TEXT NOT NULL,
      name TEXT,
      geom geometry(Point, 4326) NOT NULL,
      latitude DOUBLE PRECISION GENERATED ALWAYS AS (ST_Y(geom)) STORED,
      longitude DOUBLE PRECISION GENERATED ALWAYS AS (ST_X(geom)) STORED,
      CONSTRAINT osm_pois_osm_id_unique UNIQUE (osm_id)
    );
    CREATE INDEX IF NOT EXISTS osm_pois_geom_gist ON osm_pois USING GIST (geom);
    CREATE INDEX IF NOT EXISTS osm_pois_fclass_idx ON osm_pois (fclass);
    CREATE INDEX IF NOT EXISTS osm_pois_zone_idx ON osm_pois (zone);

    -- 2. Transport (Metro stations, railway stations, bus stops, airports)
    CREATE TABLE IF NOT EXISTS osm_transport (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      zone TEXT NOT NULL,
      osm_id TEXT NOT NULL,
      code INTEGER,
      fclass TEXT NOT NULL,
      name TEXT,
      geom geometry(Point, 4326) NOT NULL,
      latitude DOUBLE PRECISION GENERATED ALWAYS AS (ST_Y(geom)) STORED,
      longitude DOUBLE PRECISION GENERATED ALWAYS AS (ST_X(geom)) STORED,
      CONSTRAINT osm_transport_osm_id_unique UNIQUE (osm_id)
    );
    CREATE INDEX IF NOT EXISTS osm_transport_geom_gist ON osm_transport USING GIST (geom);
    CREATE INDEX IF NOT EXISTS osm_transport_fclass_idx ON osm_transport (fclass);
    CREATE INDEX IF NOT EXISTS osm_transport_zone_idx ON osm_transport (zone);

    -- 3. Places (Cities, Suburbs, Localities, Towns, Villages)
    CREATE TABLE IF NOT EXISTS osm_places (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      zone TEXT NOT NULL,
      osm_id TEXT NOT NULL,
      code INTEGER,
      fclass TEXT NOT NULL,
      name TEXT NOT NULL,
      population INTEGER,
      geom geometry(Point, 4326) NOT NULL,
      latitude DOUBLE PRECISION GENERATED ALWAYS AS (ST_Y(geom)) STORED,
      longitude DOUBLE PRECISION GENERATED ALWAYS AS (ST_X(geom)) STORED,
      CONSTRAINT osm_places_osm_id_unique UNIQUE (osm_id)
    );
    CREATE INDEX IF NOT EXISTS osm_places_geom_gist ON osm_places USING GIST (geom);
    CREATE INDEX IF NOT EXISTS osm_places_fclass_idx ON osm_places (fclass);
    CREATE INDEX IF NOT EXISTS osm_places_name_idx ON osm_places (name);

    -- 4. Water Bodies (Lakes, Reservoirs, Rivers, Wetlands)
    CREATE TABLE IF NOT EXISTS osm_water_bodies (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      zone TEXT NOT NULL,
      osm_id TEXT NOT NULL,
      code INTEGER,
      fclass TEXT NOT NULL,
      name TEXT,
      geom geometry(Geometry, 4326) NOT NULL,
      CONSTRAINT osm_water_bodies_osm_id_unique UNIQUE (osm_id)
    );
    CREATE INDEX IF NOT EXISTS osm_water_bodies_geom_gist ON osm_water_bodies USING GIST (geom);
    CREATE INDEX IF NOT EXISTS osm_water_bodies_fclass_idx ON osm_water_bodies (fclass);

    -- 5. Landuse & Parks (Parks, Forests, Commercial, Residential)
    CREATE TABLE IF NOT EXISTS osm_landuse (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      zone TEXT NOT NULL,
      osm_id TEXT NOT NULL,
      code INTEGER,
      fclass TEXT NOT NULL,
      name TEXT,
      geom geometry(Geometry, 4326) NOT NULL,
      CONSTRAINT osm_landuse_osm_id_unique UNIQUE (osm_id)
    );
    CREATE INDEX IF NOT EXISTS osm_landuse_geom_gist ON osm_landuse USING GIST (geom);
    CREATE INDEX IF NOT EXISTS osm_landuse_fclass_idx ON osm_landuse (fclass);
  `);

  console.log("[ingest-osm] Schema and spatial indices verified.");
}

async function ingestTable(
  gpkg: Database,
  zone: string,
  sourceTable: string,
  targetTable: string,
  isPolygon: boolean = false,
  hasPopulation: boolean = false,
) {
  const tableCheck = gpkg.query(`SELECT name FROM sqlite_master WHERE type='table' AND name=?`).get(sourceTable);
  if (!tableCheck) return;

  const countRow: any = gpkg.query(`SELECT count(*) as count FROM "${sourceTable}"`).get();
  const total = countRow.count;
  console.log(`[ingest-osm] ${zone}: Loading ${total.toLocaleString()} rows from ${sourceTable} -> ${targetTable}...`);

  const selectCols = hasPopulation
    ? `osm_id, code, fclass, name, population, geom`
    : `osm_id, code, fclass, name, geom`;

  const query = gpkg.query(`SELECT ${selectCols} FROM "${sourceTable}"`);
  const BATCH_SIZE = 1500;
  let batch: any[] = [];
  let inserted = 0;
  const t0 = Date.now();

  for (const row of query.iterate() as Iterable<any>) {
    if (!row.geom) continue;
    batch.push(row);

    if (batch.length >= BATCH_SIZE) {
      await insertChunk(targetTable, zone, batch, isPolygon, hasPopulation);
      inserted += batch.length;
      if (inserted % 15000 === 0 || inserted === total) {
        const rate = (inserted / ((Date.now() - t0) / 1000)).toFixed(0);
        console.log(`[ingest-osm] ${targetTable}: ${inserted.toLocaleString()}/${total.toLocaleString()} (${rate} rows/s)`);
      }
      batch = [];
    }
  }

  if (batch.length > 0) {
    await insertChunk(targetTable, zone, batch, isPolygon, hasPopulation);
    inserted += batch.length;
  }

  const elapsed = ((Date.now() - t0) / 1000).toFixed(1);
  console.log(`[ingest-osm] ${targetTable}: Finished ${inserted.toLocaleString()} rows in ${elapsed}s.`);
}

async function insertChunk(
  targetTable: string,
  zone: string,
  chunk: any[],
  isPolygon: boolean,
  hasPopulation: boolean,
) {
  const valueClauses: string[] = [];
  const params: any[] = [];
  let pIdx = 1;

  for (const r of chunk) {
    const wkbHex = extractWkbHex(r.geom);
    if (hasPopulation) {
      valueClauses.push(
        `($${pIdx++}, $${pIdx++}, $${pIdx++}, $${pIdx++}, $${pIdx++}, $${pIdx++}, ST_GeomFromWKB(decode($${pIdx++}, 'hex'), 4326))`,
      );
      params.push(zone, r.osm_id, r.code ?? null, r.fclass, r.name ?? null, r.population ?? null, wkbHex);
    } else {
      valueClauses.push(
        `($${pIdx++}, $${pIdx++}, $${pIdx++}, $${pIdx++}, $${pIdx++}, ST_GeomFromWKB(decode($${pIdx++}, 'hex'), 4326))`,
      );
      params.push(zone, r.osm_id, r.code ?? null, r.fclass, r.name ?? null, wkbHex);
    }
  }

  const cols = hasPopulation
    ? `(zone, osm_id, code, fclass, name, population, geom)`
    : `(zone, osm_id, code, fclass, name, geom)`;

  const sql = `
    INSERT INTO ${targetTable} ${cols}
    VALUES ${valueClauses.join(", ")}
    ON CONFLICT (osm_id) DO NOTHING
  `;

  await bunPG.unsafe(sql, params);
}

export async function ingestOsmGpkg(selectedZones?: string[]) {
  await initPostGisSchema();

  const allFiles = findGpkgFiles();
  if (allFiles.length === 0) {
    throw new Error(`No GPKG zone directories found in ${DOWNLOADS_DIR}`);
  }

  // Determine which files to process
  let toProcess = allFiles;
  if (selectedZones && selectedZones.length > 0) {
    toProcess = allFiles.filter((f) =>
      selectedZones.some((sz) => f.zone.toLowerCase().includes(sz.toLowerCase())),
    );
  }

  console.log(`\n[ingest-osm] Found ${allFiles.length} zones; processing ${toProcess.length} zones:`);
  toProcess.forEach((f) => console.log(` - ${f.zone} (${f.path})`));

  const grandStart = Date.now();

  for (const zf of toProcess) {
    console.log(`\n======================================================`);
    console.log(`[ingest-osm] Ingesting Zone: ${zf.zone.toUpperCase()}`);
    console.log(`======================================================`);
    const gpkg = new Database(zf.path, { readonly: true });

    try {
      // 1. Transport (Metro, Rail, Bus, Airport)
      await ingestTable(gpkg, zf.zone, "gis_osm_transport_free", "osm_transport", false, false);

      // 2. POIs (Schools, Hospitals, Banks, Malls)
      await ingestTable(gpkg, zf.zone, "gis_osm_pois_free", "osm_pois", false, false);

      // 3. Places (Suburbs, Localities, Towns, Cities)
      await ingestTable(gpkg, zf.zone, "gis_osm_places_free", "osm_places", false, true);

      // 4. Water Bodies (Lakes, Reservoirs)
      await ingestTable(gpkg, zf.zone, "gis_osm_water_a_free", "osm_water_bodies", true, false);

      // 5. Landuse (Parks, Green spaces, Commercial belts)
      await ingestTable(gpkg, zf.zone, "gis_osm_landuse_a_free", "osm_landuse", true, false);
    } finally {
      gpkg.close();
    }
  }

  const grandElapsed = ((Date.now() - grandStart) / 1000).toFixed(1);
  console.log(`\n[ingest-osm] All ingestion completed in ${grandElapsed}s!`);

  // Print summary counts
  const summary: any = await bunPG.unsafe(`
    SELECT 
      (SELECT count(*) FROM osm_transport) as transport_count,
      (SELECT count(*) FROM osm_pois) as pois_count,
      (SELECT count(*) FROM osm_places) as places_count,
      (SELECT count(*) FROM osm_water_bodies) as water_count,
      (SELECT count(*) FROM osm_landuse) as landuse_count
  `);
  console.log("\n=== PostGIS Ingested Summary Table ===");
  console.table(summary[0]);
}

if (import.meta.main) {
  const args = process.argv.slice(2);
  let zones: string[] | undefined;
  if (args.includes("--all")) {
    zones = undefined; // all
  } else if (args.length > 0 && !args[0].startsWith("-")) {
    zones = args;
  } else {
    // Default to Southern, Western, and Central (Bengaluru, Hyderabad, Mumbai, Pune, Indore)
    zones = ["southern", "western", "central"];
  }

  ingestOsmGpkg(zones)
    .then(async () => {
      await closeSql();
      process.exit(0);
    })
    .catch(async (err) => {
      console.error("[ingest-osm] Failed:", err);
      await closeSql();
      process.exit(1);
    });
}
