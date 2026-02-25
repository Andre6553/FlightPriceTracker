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
    console.log('Running migration...');
    const sqlPath = path.join(__dirname, 'schema.sql');
    const sql = fs.readFileSync(sqlPath, 'utf8');

    // Most custom Supabase exe_sql functions use either 'sql' or 'query' as the parameter. We will try 'query' first.
    let { data, error } = await supabase.rpc('exec_sql', { sql: sql });

    if (error) {
        console.log("Failed with 'sql' parameter, trying 'query' parameter...");
        let retry = await supabase.rpc('exec_sql', { query: sql });
        if (retry.error) {
            console.error('❌ Migration failed via RPC:', retry.error);
            console.error('Make sure the exec_sql RPC function is created in Supabase first.');
            // Let's create another way if RPC is missing...
            process.exit(1);
        } else {
            console.log('✅ Migration successful');
        }
    } else {
        console.log('✅ Migration successful');
    }
}
migrate();
