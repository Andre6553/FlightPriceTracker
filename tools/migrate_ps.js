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

if (!supabaseUrl || !supabaseKey) {
    console.error('Missing Supabase URL or Key in .env');
    process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

async function migrate() {
    const sqlPath = path.join(__dirname, 'schema_price_shifts.sql');
    const sql = fs.readFileSync(sqlPath, 'utf8');

    console.log("Applying Price Shifts View Update...");
    // Try different RPC names common for SQL execution
    let result = await supabase.rpc('exec_sql', { query: sql });
    if (result.error) result = await supabase.rpc('exec_sql', { sql: sql });
    if (result.error) result = await supabase.rpc('execute_sql', { sql: sql });
    if (result.error) result = await supabase.rpc('execute_sql', { query: sql });

    if (result.error) {
        console.error('❌ Migration failed:', result.error.message);
        console.log('\n--- MANUAL SQL TO RUN IN SUPABASE EDITOR ---');
        console.log(sql);
        console.log('--------------------------------------------\n');
    } else {
        console.log('✅ Migration successful');
    }
}
migrate();
