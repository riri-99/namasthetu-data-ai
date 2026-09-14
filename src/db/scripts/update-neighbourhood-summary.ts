import { bunPG, closeSql } from "../src/db/sql";

// ============================================================================
// Neighbourhood summary job (plan.md section 8). Run: bun run job:neighbourhood
//
// Recomputes, for EVERY property, the neighbourhood figures derived from our
// own data:
// - nearest metro station (name and straight-line metres) from `pois`, within 25 km;
// - straight-line metres to the nearest active airport hub in the property's city.
//
// Where nothing qualifies the figure is set to NULL, so a seed value can never
// survive and be shown as measured. Every row is stamped with poiComputedAt and
// the dataset date of the newest finished import, which the PIP shows as
// "as of". Idempotent: re-run it after every POI import or hub change.
// ============================================================================

const METRO_SEARCH_METERS = 25_000;

async function main() {
  const t0 = performance.now();

  const [latest] = await bunPG<Array<{ datasetDate: string | null }>>`
    SELECT TO_CHAR(MAX("datasetDate"), 'YYYY-MM-DD') AS "datasetDate"
    FROM poi_import_runs
    WHERE "finishedAt" IS NOT NULL AND error IS NULL
  `;
  if (!latest?.datasetDate) {
    throw new Error("No finished POI import run. Import pois (bun run import:pois) before running this job.");
  }

  // 1. Every property has a neighbourhood row.
  await bunPG`
    INSERT INTO neighbourhood_intelligence (id, "propertyId", "updatedAt")
    SELECT gen_random_uuid()::text, p.id, NOW()
    FROM properties p
    ON CONFLICT ("propertyId") DO NOTHING
  `;

  // 2. Recompute every row; LEFT JOINs leave NULL where nothing qualifies.
  const updated = await bunPG`
    UPDATE neighbourhood_intelligence ni
    SET "nearestMetroName" = metro.name,
        "metroDistanceMeters" = metro.dist,
        "airportDistanceMeters" = airport.dist,
        "poiComputedAt" = NOW(),
        "poiDatasetDate" = ${latest.datasetDate}::date,
        "updatedAt" = NOW()
    FROM properties p
    LEFT JOIN LATERAL (
      SELECT COALESCE(po."nameOverride", po.name) AS name,
             ROUND(ST_Distance(po.geom, ST_SetSRID(ST_MakePoint(p.longitude, p.latitude), 4326)::geography))::int AS dist
      FROM pois po
      WHERE po.category = 'METRO_STATION'::"PoiCategory"
        AND NOT po."isHidden"
        AND po."retiredAt" IS NULL
        AND ST_DWithin(po.geom, ST_SetSRID(ST_MakePoint(p.longitude, p.latitude), 4326)::geography, ${METRO_SEARCH_METERS})
      ORDER BY po.geom <-> ST_SetSRID(ST_MakePoint(p.longitude, p.latitude), 4326)::geography
      LIMIT 1
    ) metro ON true
    LEFT JOIN LATERAL (
      SELECT ROUND(ST_Distance(
               ST_SetSRID(ST_MakePoint(h.longitude, h.latitude), 4326)::geography,
               ST_SetSRID(ST_MakePoint(p.longitude, p.latitude), 4326)::geography
             ))::int AS dist
      FROM commute_hubs h
      WHERE h.city = p.city AND h.category = 'AIRPORT'::"CommuteHubCategory" AND h."isActive"
      ORDER BY 1
      LIMIT 1
    ) airport ON true
    WHERE ni."propertyId" = p.id
  `;

  const stats = await bunPG<Array<{ city: string; properties: number; withMetro: number; withAirport: number }>>`
    SELECT p.city,
           COUNT(*)::int AS properties,
           COUNT(ni."metroDistanceMeters")::int AS "withMetro",
           COUNT(ni."airportDistanceMeters")::int AS "withAirport"
    FROM properties p
    JOIN neighbourhood_intelligence ni ON ni."propertyId" = p.id
    GROUP BY p.city
    ORDER BY 2 DESC
  `;

  console.log(
    `Recomputed ${updated.count} neighbourhood rows from pois as of ${latest.datasetDate} ` +
      `in ${(performance.now() - t0).toFixed(0)} ms.`
  );
  console.table(stats);
}

main()
  .catch((err) => {
    console.error("Neighbourhood summary job failed:", err);
    process.exitCode = 1;
  })
  .finally(() => closeSql());
