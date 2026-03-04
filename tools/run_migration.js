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
    const sqlPath = path.join(__dirname, 'schema.sql');
    const sql = fs.readFileSync(sqlPath, 'utf8');

    console.log("Trying RPC exec_sql with {query: sql}...");
    let result = await supabase.rpc('exec_sql', { query: sql });

    if (result.error && result.error.message.includes('Could not find the function')) {
        console.log("Failed. Trying RPC exec_sql with {sql: sql}...");
        result = await supabase.rpc('exec_sql', { sql: sql });

        if (result.error && result.error.message.includes('Could not find the function')) {
            console.log("Failed. Checking if migrations RPC goes by a different name, e.g. execute_sql");
            result = await supabase.rpc('execute_sql', { sql: sql });
            if (result.error) {
                result = await supabase.rpc('execute_sql', { query: sql });
            }
        }
    }

    if (result.error) {
        console.error('❌ Migration failed via RPC:', result.error);
        process.exit(1);
    } else {
        console.log('✅ Migration successful');
    }
}
migrate();
