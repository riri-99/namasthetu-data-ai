import crypto from "crypto";
import { bunPG, closeSql } from "../src/db/sql";

export interface SeedAdminResult {
  seeded: boolean;
  adminId?: string;
  publicId?: string;
  email: string;
  message: string;
}

/**
 * Idempotent Admin Bootstrap Script (B2 in outstanding-work-spec.md).
 *
 * Creates the initial SUPER_ADMIN account if no admin exists, reading credentials
 * from the environment. Safe to run repeatedly in Docker bring-up or CI.
 */
export async function seedAdmin(): Promise<SeedAdminResult> {
  const email = (process.env.ADMIN_EMAIL || "admin@namasthetu.internal").toLowerCase().trim();
  const password = process.env.ADMIN_PASSWORD || "Admin@Namasthetu2026!";
  const fullName = process.env.ADMIN_FULL_NAME || "System Administrator";
  const department = process.env.ADMIN_DEPARTMENT || "Security & Governance";

  // Check if any admin already exists
  const existingAdmins = await bunPG<Array<{ id: string; email: string }>>`
    SELECT id, email FROM admin_users LIMIT 5
  `;

  if (existingAdmins.length > 0) {
    const matched = existingAdmins.find((a) => a.email === email);
    console.log(
      `[Seed-Admin] Admin user(s) already exist (${existingAdmins.length} found). Skipping bootstrap.`
    );
    return {
      seeded: false,
      adminId: matched?.id ?? existingAdmins[0]?.id,
      email,
      message: "Admin users already exist. Bootstrap skipped (idempotent no-op).",
    };
  }

  const passwordHash = await Bun.password.hash(password, {
    algorithm: "argon2id",
    memoryCost: 65536,
    timeCost: 3,
  });

  const publicId = `adm_${crypto.randomBytes(8).toString("hex")}`;
  const ipAddressHashed = crypto.createHash("sha256").update("127.0.0.1_bootstrap").digest("hex");

  const [newUser] = await bunPG<
    Array<{
      id: string;
      publicId: string;
      email: string;
      fullName: string;
      role: string;
    }>
  >`
    INSERT INTO admin_users (
      id, "publicId", email, "passwordHash", "fullName", role, department, "isActive", "createdAt", "updatedAt"
    ) VALUES (
      gen_random_uuid(), ${publicId}, ${email}, ${passwordHash},
      ${fullName}, 'SUPER_ADMIN'::"AdminRole", ${department}, true, NOW(), NOW()
    )
    RETURNING id, "publicId", email, "fullName", role::text
  `;

  await bunPG`
    INSERT INTO admin_audit_logs (
      id, "actorAdminId", action, "targetEntity", "targetEntityId", "ipAddressHashed", "payloadJson", "createdAt"
    ) VALUES (
      gen_random_uuid(), ${newUser.id}, 'BOOTSTRAP_SUPER_ADMIN', 'AdminUser', ${newUser.id},
      ${ipAddressHashed}, ${JSON.stringify({ email: newUser.email, role: newUser.role })}, NOW()
    )
  `;

  console.log(`[Seed-Admin] Successfully bootstrapped SUPER_ADMIN: ${newUser.email} (${newUser.id})`);

  return {
    seeded: true,
    adminId: newUser.id,
    publicId: newUser.publicId,
    email: newUser.email,
    message: "SUPER_ADMIN bootstrapped successfully.",
  };
}

if (import.meta.main) {
  seedAdmin()
    .then(async (res) => {
      console.log(JSON.stringify(res, null, 2));
      await closeSql();
      process.exit(0);
    })
    .catch(async (err) => {
      console.error("[Seed-Admin] Fatal bootstrap failure:", err);
      await closeSql();
      process.exit(1);
    });
}
