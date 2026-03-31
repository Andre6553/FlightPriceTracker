import { createClient } from '@supabase/supabase-js';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
dotenv.config({ path: path.join(__dirname, '.env') });

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_SERVICE_ROLE_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

async function runSql(sql) {
    console.log("Running SQL segment with 'exec_sql'...");
    const res = await supabase.rpc('exec_sql', { query: sql });
    if (res.error) {
        console.error("❌ RPC error:", res.error.message);
    } else {
        console.log("✅ Segment success");
    }
}

async function migrate() {
    const files = ['schema.sql', 'schema_price_shifts.sql'];
    for (const file of files) {
        console.log(`\n--- Migrating ${file} ---`);
        const sqlPath = path.join(__dirname, file);
        const sql = fs.readFileSync(sqlPath, 'utf8');
        await runSql(sql);
    }
}
migrate();
