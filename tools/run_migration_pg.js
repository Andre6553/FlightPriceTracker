import pkg from 'pg';
const { Client } = pkg;
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
dotenv.config({ path: path.join(__dirname, '.env') });

const dbUrl = process.env.SUPABASE_DB_URL; // Using the direct PG connection string
if (!dbUrl) {
    console.error('Missing SUPABASE_DB_URL in .env');
    // Construct it from the project ref if not provided
    const match = process.env.SUPABASE_URL?.match(/https:\/\/([^.]+)\.supabase\.co/);
    if (match) {
        const ref = match[1];
        // password for the db might be different than the anon key.
        console.error(`Please add SUPABASE_DB_URL to tools/.env\nFormat: postgresql://postgres.[project-ref]:[database-password]@aws-0-[region].pooler.supabase.com:6543/postgres`);
    }
    process.exit(1);
}

const client = new Client({
    connectionString: dbUrl,
});

async function migrate() {
    try {
        await client.connect();
        const sqlPath = path.join(__dirname, 'schema.sql');
        const sql = fs.readFileSync(sqlPath, 'utf8');

        console.log("Executing SQL...");
        await client.query(sql);
        console.log('✅ Migration successful');
    } catch (err) {
        console.error('❌ Migration failed:', err);
    } finally {
        await client.end();
    }
}
migrate();
