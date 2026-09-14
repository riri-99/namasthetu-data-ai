/**
 * Import OpenStreetMap places into `pois` from Geofabrik free GeoPackage extracts.
 *
 *   bun run import:pois --file <zone.gpkg | extracted folder | zone.gpkg.zip> [--file ...]
 *   bun run import:pois --zone western-zone [--zone ...]     download the latest extract first
 *
 *   --dry-run      read and classify only; no database connection
 *   --work-dir     where zips are downloaded and unpacked (default: OS temp dir)
 *   --keep-temp    keep downloaded and unpacked files
 *
 * Needs DATABASE_URL (except --dry-run). Additive and idempotent: places are
 * upserted on (source, sourceRef, category), ops edits are never overwritten,
 * and places missing from two finished runs of a region are marked retired,
 * never deleted. Zones: see REGIONS in src/modules/locality/osmGpkg.ts.
 *
 * Data © OpenStreetMap contributors, ODbL 1.0: credit it wherever places are shown.
 */
import { SQL } from "bun";
import { existsSync, statSync, readdirSync } from "node:fs";
import { mkdir, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, dirname, join } from "node:path";
import { parseArgs } from "node:util";
import { writePois } from "../src/modules/locality/importPois";
import { datasetDateFrom, readZone, regionFromFileName, REGIONS } from "../src/modules/locality/osmGpkg";
import { extractZipEntry, listZipEntries } from "../src/modules/locality/zipEntry";

const { values: args } = parseArgs({
  args: Bun.argv.slice(2),
  options: {
    file: { type: "string", multiple: true },
    zone: { type: "string", multiple: true },
    "dry-run": { type: "boolean", default: false },
    "work-dir": { type: "string" },
    "keep-temp": { type: "boolean", default: false },
    help: { type: "boolean", default: false },
  },
});

const USAGE = "Usage: import-pois (--file <path> | --zone <name>)... [--dry-run] [--work-dir <dir>] [--keep-temp]";

interface PreparedInput {
  gpkgPath: string;
  readme: string | null;
  /** Recorded on the run: the file or folder the operator pointed at. */
  sourceFile: string;
  /** Temporary files to remove afterwards. */
  temp: string[];
}

const log = (message: string) => console.log(`[import-pois] ${message}`);
const mb = (bytes: number) => `${Math.round(bytes / 1024 / 1024)} MB`;

async function readmeIn(dir: string): Promise<string | null> {
  const path = join(dir, "README");
  return existsSync(path) ? await Bun.file(path).text() : null;
}

async function prepare(input: string, workDir: string): Promise<PreparedInput> {
  if (!existsSync(input)) throw new Error(`${input} does not exist`);

  if (statSync(input).isDirectory()) {
    const gpkgs = readdirSync(input).filter((f) => f.toLowerCase().endsWith(".gpkg"));
    if (gpkgs.length !== 1) throw new Error(`${input}: expected exactly one .gpkg inside, found ${gpkgs.length}`);
    return { gpkgPath: join(input, gpkgs[0]!), readme: await readmeIn(input), sourceFile: basename(input), temp: [] };
  }

  if (input.toLowerCase().endsWith(".zip")) {
    const entries = await listZipEntries(input);
    const gpkg = entries.find((e) => e.name.toLowerCase().endsWith(".gpkg"));
    if (!gpkg) throw new Error(`${input}: no .gpkg inside`);
    const outDir = join(workDir, basename(input).replace(/\.zip$/i, "") + ".unpacked");
    await mkdir(outDir, { recursive: true });
    const gpkgPath = join(outDir, basename(gpkg.name));
    log(`unpacking ${gpkg.name} (${mb(gpkg.size)}) to ${outDir}`);
    await extractZipEntry(input, gpkg, gpkgPath);
    const readmeEntry = entries.find((e) => basename(e.name) === "README");
    let readme: string | null = null;
    if (readmeEntry) {
      const readmePath = join(outDir, "README");
      await extractZipEntry(input, readmeEntry, readmePath);
      readme = await Bun.file(readmePath).text();
    }
    return { gpkgPath, readme, sourceFile: basename(input), temp: [outDir] };
  }

  if (input.toLowerCase().endsWith(".gpkg")) {
    return { gpkgPath: input, readme: await readmeIn(dirname(input)), sourceFile: basename(input), temp: [] };
  }

  throw new Error(`${input}: expected a .gpkg file, a folder containing one, or a .gpkg.zip`);
}

async function download(zone: string, workDir: string): Promise<string> {
  const region = REGIONS[zone];
  if (!region) throw new Error(`unknown zone "${zone}". Known: ${Object.keys(REGIONS).join(", ")}`);
  const target = join(workDir, basename(new URL(region.url).pathname));
  log(`downloading ${region.url}`);
  const response = await fetch(region.url);
  if (!response.ok || !response.body) throw new Error(`${region.url}: HTTP ${response.status}`);
  await Bun.write(target, response);
  log(`downloaded ${mb(Bun.file(target).size)} to ${target}`);
  return target;
}

async function main(): Promise<void> {
  const files = args.file ?? [];
  const zones = args.zone ?? [];
  if (args.help || (files.length === 0 && zones.length === 0)) {
    console.log(USAGE);
    process.exit(args.help ? 0 : 1);
  }

  const dryRun = args["dry-run"];
  const databaseUrl = Bun.env.DATABASE_URL;
  if (!dryRun && !databaseUrl) throw new Error("DATABASE_URL is not set (use --dry-run to only read the files)");

  const workDir = args["work-dir"] ?? join(tmpdir(), "namasthetu-poi-import");
  await mkdir(workDir, { recursive: true });
  const sql = dryRun ? null : new SQL(databaseUrl!);
  const downloads: string[] = [];

  try {
    const inputs = [...files];
    for (const zone of zones) {
      const zip = await download(zone, workDir);
      downloads.push(zip);
      inputs.push(zip);
    }

    for (const input of inputs) {
      const started = performance.now();
      const prepared = await prepare(input, workDir);
      try {
        const region = regionFromFileName(prepared.gpkgPath);
        const config = REGIONS[region];
        if (!config) throw new Error(`${prepared.gpkgPath}: unknown region "${region}". Known: ${Object.keys(REGIONS).join(", ")}`);
        const datasetDate = datasetDateFrom(prepared.readme, [input, prepared.gpkgPath]);
        if (!datasetDate) throw new Error(`${input}: can't tell the data date (no README and no -YYMMDD- in the name)`);

        log(`${region}: reading ${prepared.gpkgPath} (data as of ${datasetDate})`);
        const { records, stats } = readZone(prepared.gpkgPath, config);
        log(
          `${region}: ${records.length} places kept of ${stats.considered} considered ` +
            `(unnamed ${stats.unnamed}, no geometry ${stats.noGeometry}, outside operating cities ${stats.outsideOperatingCities}, ` +
            `merged duplicates ${stats.merged}, metro stations ${stats.metroStations})`,
        );
        log(
          `${region}: ` +
            Object.entries(stats.byCategory)
              .sort((a, b) => b[1]! - a[1]!)
              .map(([category, n]) => `${category} ${n}`)
              .join(" · "),
        );

        if (sql) {
          const result = await writePois(sql, { region, sourceFile: prepared.sourceFile, datasetDate, records });
          log(
            `${region}: run ${result.runId} inserted ${result.inserted}, updated ${result.updated}, retired ${result.retired}` +
              (result.retirementSkipped ? " (retirement skipped: far fewer places than the previous run)" : ""),
          );
        }
        log(`${region}: done in ${((performance.now() - started) / 1000).toFixed(1)} s`);
      } finally {
        if (!args["keep-temp"]) for (const path of prepared.temp) await rm(path, { recursive: true, force: true });
      }
    }
  } finally {
    if (!args["keep-temp"]) for (const path of downloads) await rm(path, { force: true });
    await sql?.close();
  }
}

main().catch((err) => {
  console.error(`[import-pois] failed: ${err instanceof Error ? err.message : String(err)}`);
  process.exit(1);
});
