# Deploying the matching test page to Vercel

The deployed page runs the **v2 test set (4,130 entries)**, not the 39k stress set:
a serverless function can't hold the 1.9 GB of caches the big set needs.

1. **Build the bundle** (after any code change):
   `cd matching-prototype && . .venv/bin/activate && python deploy/make_deploy.py`
2. **Supabase (ratings only):** create a free project, run `deploy/ratings.sql` in its
   SQL Editor, and copy the project URL and the `service_role` key (Settings -> API).
3. **Vercel:** `cd deploy/out && npx vercel login`, then `npx vercel` (accept the defaults,
   it creates the project).
4. **Environment variables** (Vercel dashboard -> Settings -> Environment Variables, or
   `npx vercel env add NAME production`): `OPENAI_API_KEY`, `JEV_API_KEY`,
   `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, `TEAM_PASSCODE`, `SUPABASE_URL`,
   `SUPABASE_SERVICE_KEY`.
5. **Deploy:** `npx vercel --prod`, then send the link and the passcode.

Every run spends real credits (about $0.003 on this dataset); set spending limits in the
OpenAI, Anthropic and Google consoles before sharing.
