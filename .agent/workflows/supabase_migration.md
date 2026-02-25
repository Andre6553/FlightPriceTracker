---
description: Supabase Database Migration
---

# Database Migration Workflow

When performing database migrations (adding columns, creating tables, updating RLS), ALWAYS use the `exec_sql` RPC function. Do NOT attempt to connect via direct PostgreSQL (`pg` client) unless this method fails.

// turbo-all

### Connection Details
- **SUPABASE_URL**: `https://opiscawovakabjpmzwte.supabase.co`
- **SERVICE_ROLE_KEY**: Found in the `tools/.env` file under `SUPABASE_SERVICE_ROLE_KEY`.

### Procedure

1. **Create the SQL file** containing the schema changes (e.g., `tools/schema.sql`).
2. **Create a temporary migration script** (`tools/run_migration.js`):
   ```javascript
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
       // Note: update the SQL file path below when running a different migration
       const sqlPath = path.join(__dirname, 'schema.sql');
       const sql = fs.readFileSync(sqlPath, 'utf8');
       const { error } = await supabase.rpc('exec_sql', { query: sql }); // Make sure to use 'query' or 'sql' depending on your RPC definition.
       
       if (error) {
           console.error('❌ Migration failed via RPC (exec_sql) - trying direct postgres or checking RPC:', error);
           process.exit(1);
       } else {
           console.log('✅ Migration successful');
       }
   }
   migrate();
   ```

3. **Install dependencies** (if not already installed in the `tools` directory):
   ```bash
   cd tools
   npm init -y
   npm install @supabase/supabase-js dotenv
   ```

4. **Run the script**:
   ```bash
   cd tools
   node run_migration.js
   ```

5. **Cleanup**:
   Delete or retain the script as needed.
