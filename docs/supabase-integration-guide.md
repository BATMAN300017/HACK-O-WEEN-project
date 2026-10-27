# SentinelFlow AI — Complete Supabase Integration Guide
**Connecting Database, Authentication, Transactional Email, and File Storage**

SentinelFlow AI is engineered to run seamlessly with **Supabase** as the unified cloud infrastructure layer:
1. **Database:** Managed PostgreSQL (with pgvector & connection pooling)
2. **Authentication:** Supabase Auth (GoTrue JWTs + Role-based permissions)
3. **File Storage:** Supabase Storage (S3-compatible bucket for PDF case dossiers & KYC attachments)
4. **Email:** Transactional email via Supabase Auth + Custom SMTP (Resend, SendGrid, SES)

---

## 1. Database: Connecting Supabase PostgreSQL

### Step 1.1: Run the Schema Script in Supabase
1. Open your [Supabase Dashboard](https://supabase.com/dashboard).
2. Click on **SQL Editor** in the left navigation sidebar.
3. Click **New Query**.
4. Copy the entire contents of [`scripts/supabase_schema.sql`](../scripts/supabase_schema.sql) and paste it into the editor.
5. Click **Run** (or `Ctrl + Enter`).
6. This automatically creates all 27 core financial tables, indexes, storage buckets, and seeds standard investigator accounts.

### Step 1.2: Get Your Database Connection String
1. In your Supabase project, navigate to **Project Settings** (gear icon) -> **Database**.
2. Scroll to **Connection string** and select the **URI** tab.
3. Choose **Transaction Pooler** (recommended for serverless/containers on port `6543`) or **Session Pooler**:
   ```
   postgresql://postgres.[YOUR-PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require
   ```
4. Replace `[YOUR-PASSWORD]` with your database password.
5. In your `.env` file, set:
   ```env
   DATABASE_URL="postgresql://postgres.[YOUR-PROJECT-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require"
   ```

---

## 2. Authentication: Connecting Supabase Auth

SentinelFlow AI's API automatically validates Supabase Auth JWT access tokens in the `Authorization: Bearer <token>` header.

### Step 2.1: Get Supabase API Keys
1. In your Supabase Dashboard, go to **Project Settings** -> **API**.
2. Copy:
   - **Project URL** (e.g. `https://xyzproject.supabase.co`)
   - **anon / public key**
   - **service_role key** (keep secret; used for backend operations)
   - **JWT Secret** (under JWT Settings)
3. Add these to your `.env`:
   ```env
   SUPABASE_URL="https://[YOUR-PROJECT-REF].supabase.co"
   SUPABASE_ANON_KEY="eyJhbGciOi..."
   SUPABASE_SERVICE_ROLE_KEY="eyJhbGciOi..."
   SUPABASE_JWT_SECRET="your-supabase-jwt-secret"
   ```

### Step 2.2: User Roles in Supabase
When inviting or signing up an investigator in Supabase Auth, assign their role in the `user_metadata`:
```json
{
  "full_name": "Sarah Lin",
  "role": "investigator"
}
```
Supported roles:
- `investigator`: Can triage alerts, convert cases, add notes, and submit dispositions.
- `senior_investigator`: Can approve or reject peer reviews and high-value decisions.
- `fraud_admin`: Can modify and publish detection rules and promote ML models.
- `auditor`: Read-only access to audit trail and compliance logs.

---

## 3. File Storage: Supabase Storage Buckets

SentinelFlow AI exports official case dossiers, PDF reports, and evidence files directly to Supabase Storage.

### Step 3.1: Create Storage Bucket
The `scripts/supabase_schema.sql` script creates this automatically, or you can create it manually:
1. In the Supabase Dashboard, go to **Storage**.
2. Click **New Bucket**.
3. Name it: `evidence-files`.
4. Toggle **Public bucket** to `ON` (or keep private and use signed URLs).
5. In `.env`:
   ```env
   SUPABASE_STORAGE_BUCKET="evidence-files"
   ```

### Step 3.2: Verification
Whenever an investigator clicks **"Export Dossier"** or an evidence file is attached, SentinelFlow's `supabase_service.py` uploads the binary and returns a permanent public/signed URL stored on the `evidence_items.storage_file_path` column.

---

## 4. Email: Transactional & Alert Notifications

### Step 4.1: Built-in Supabase Auth Emails
Supabase comes with built-in emails for:
- User invitations (inviting investigators to the command center)
- Password resets & Magic links
- Confirmation emails

### Step 4.2: Connecting Custom SMTP (For High-Deliverability Fraud Alerts)
To ensure alert notifications reach investigators' inboxes reliably:
1. Go to **Authentication** -> **SMTP Settings** in your Supabase project.
2. Toggle **Enable Custom SMTP** to `ON`.
3. Enter your SMTP provider credentials:
   - **Resend (Recommended):** Host: `smtp.resend.com`, Port: `587`, User: `resend`, Password: `[YOUR-API-KEY]`
   - **SendGrid:** Host: `smtp.sendgrid.net`, Port: `587`, User: `apikey`, Password: `[YOUR-SENDGRID-KEY]`
   - **AWS SES:** Host: `email-smtp.[region].amazonaws.com`, Port: `587`
4. Set Sender Email: `alerts@sentinelflow.bank` or your verified domain.
5. Click **Save**.

---

## 5. Summary of Environment Variables for Supabase

Add the following block to your root `.env` or cloud deployment environment variables (Render, Railway, or Docker):

```env
# Database (Supabase PostgreSQL)
DATABASE_URL=postgresql://postgres.[YOUR-REF]:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres?sslmode=require

# Supabase Infrastructure
SUPABASE_URL=https://[YOUR-REF].supabase.co
SUPABASE_ANON_KEY=eyJhbGciOi...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOi...
SUPABASE_JWT_SECRET=your-supabase-jwt-secret
SUPABASE_STORAGE_BUCKET=evidence-files
```

With these variables set, the SentinelFlow AI backend and frontend automatically switch from local SQLite to your live Supabase cloud backend!
