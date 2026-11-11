import {neon} from '@neondatabase/serverless';
import {readFileSync} from 'node:fs';
const url=process.env.DATABASE_URL;if(!url)throw Error('DATABASE_URL missing');
const sql=neon(url);const statements=readFileSync('migrations/0001_initial.sql','utf8').split(';').map(x=>x.trim()).filter(Boolean);
await sql.transaction(statements.map(text=>sql.query(text)));
console.log('Postgres migration applied');
