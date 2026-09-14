import { bunPG, closeSql } from "../src/db/sql";

async function testPropertyEnrichment() {
  console.log("=== Querying Real Civic Telemetry from PostGIS for Namasthetu Properties ===\n");

  const sampleProps = await bunPG.unsafe(`
    SELECT id, slug, title, locality, city, latitude, longitude
    FROM properties
    WHERE city IN ('Bengaluru', 'Mumbai', 'Pune', 'Indore')
    LIMIT 4
  `);

  for (const p of sampleProps) {
    console.log(`--------------------------------------------------------------------------------`);
    console.log(`Property: "${p.title}"`);
    console.log(`Location: ${p.locality}, ${p.city} (Lat: ${p.latitude}, Lng: ${p.longitude})`);

    // 1. Nearest Transit / Metro (subway, railway_station, bus_stop)
    const transit = await bunPG.unsafe(`
      SELECT name, fclass, ROUND(ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography)) AS distance_meters
      FROM osm_transport
      WHERE name IS NOT NULL AND name != ''
      ORDER BY geom <-> ST_SetSRID(ST_MakePoint($1, $2), 4326)
      LIMIT 3
    `, [p.longitude, p.latitude]);

    console.log("\n  [Transit Access]:");
    for (const t of transit) {
      console.log(`   - ${t.name} (${t.fclass}): ${t.distance_meters}m away`);
    }

    // 2. Top Schools Nearby (< 5km)
    const schools = await bunPG.unsafe(`
      SELECT name, fclass, ROUND(ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography)) AS distance_meters
      FROM osm_pois
      WHERE fclass IN ('school', 'college', 'kindergarten')
        AND name IS NOT NULL AND name != ''
        AND ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography, 5000)
      ORDER BY distance_meters ASC
      LIMIT 3
    `, [p.longitude, p.latitude]);

    console.log("\n  [Schools Nearby]:");
    for (const s of schools) {
      console.log(`   - ${s.name} (${s.fclass}): ${s.distance_meters}m away`);
    }

    // 3. Nearest Healthcare / Hospital (< 5km)
    const hospital = await bunPG.unsafe(`
      SELECT name, fclass, ROUND(ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography)) AS distance_meters
      FROM osm_pois
      WHERE fclass IN ('hospital', 'clinic', 'pharmacy')
        AND name IS NOT NULL AND name != ''
      ORDER BY geom <-> ST_SetSRID(ST_MakePoint($1, $2), 4326)
      LIMIT 2
    `, [p.longitude, p.latitude]);

    console.log("\n  [Healthcare]:");
    for (const h of hospital) {
      console.log(`   - ${h.name} (${h.fclass}): ${h.distance_meters}m away`);
    }

    // 4. Nearest Lake / Waterbody
    const water = await bunPG.unsafe(`
      SELECT name, fclass, ROUND(ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint($1, $2), 4326)::geography)) AS distance_meters
      FROM osm_water_bodies
      WHERE name IS NOT NULL AND name != ''
      ORDER BY geom <-> ST_SetSRID(ST_MakePoint($1, $2), 4326)
      LIMIT 1
    `, [p.longitude, p.latitude]);

    if (water.length > 0) {
      console.log("\n  [Water Security / Lake View]:");
      console.log(`   - ${water[0].name} (${water[0].fclass}): ${water[0].distance_meters}m away`);
    }
    console.log("\n");
  }

  await closeSql();
}

testPropertyEnrichment().catch(console.error);
