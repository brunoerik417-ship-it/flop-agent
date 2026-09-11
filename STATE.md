# STATE — proyek FLOP / Technocore

Terakhir update: 2026-09-11 20:50 UTC
Operator: Gøønjøru · Agent: Hermes (profile `godhood`)

---

## ⚠️ MASALAH YANG BELUM SELESAI: `hindsight_retain` gagal

**Gejala:** tool `hindsight_retain` balikin `Failed to store memory: ` — **error kosong**,
tanpa detail apa pun.

**Diagnosa (11 Sep 2026, 20:40 UTC):**

| Komponen | Status |
|---|---|
| `hindsight-api` (port 8888) | ✅ hidup, `/health/ready` → `status: healthy` |
| Postgres (`127.0.0.1:5432`) | ✅ connected |
| Auth | ✅ `Authorization: Bearer <key>` → 200 (**bukan** `X-API-Key`, itu 401) |
| Bank `hermes-godhood` | ✅ ada, 140 fakta, `last_write_at: 20:37` |
| Backend LLM (`192.168.18.8:20128`) | ✅ hidup, 42 model, `baip/hy3` ada |
| **Model `baip/hy3`** | ⚠️ **reasoning model — output `content` KOSONG** |

**Akar masalah:** Hindsight pakai LLM buat **ekstraksi fakta terstruktur** sebelum simpan.
Model `baip/hy3` itu reasoning model — dia ngabisin token di `reasoning_content`, dan
`content`-nya kosong:

```json
{"choices":[{"message":{"content":"","reasoning_content":"The user said \"say ok\". This is a"},
             "finish_reason":"length"}]}
```

Ekstraksi gagal → retain gagal → error kosong (crash di level parsing, bukan HTTP).

**Bukan** masalah API key, **bukan** masalah token GitHub, **bukan** masalah setup.

### Solusi (belum dijalankan — operator mau cek model dulu)

Hindsight dikonfigurasi lewat **env process** `hindsight-api`, bukan `config.yaml` Hermes:

```
HINDSIGHT_API_LLM_BASE_URL = http://192.168.18.8:20128/v1
HINDSIGHT_API_LLM_MODEL    = baip/hy3          ← GANTI INI
HINDSIGHT_API_LLM_PROVIDER = openai
HINDSIGHT_API_LLM_API_KEY  = (35 char, ada)
HINDSIGHT_API_EMBEDDINGS_PROVIDER = onnx
```

**Ganti `HINDSIGHT_API_LLM_MODEL` ke model non-reasoning**, terus restart service.

Model yang tersedia di backend itu (42 total, sebagian): `mistral/mistral-large-latest`,
`mistral/codestral-latest`, `mistral/mistral-medium-latest`, `ag/gemini-3.7-flash-*`,
`oc/mimo-v2.5-free`. **Cek dulu mana yang non-reasoning** (yang `content`-nya keisi,
bukan cuma `reasoning_content`).

Cara verifikasi model cocok:
```bash
curl -sS -X POST -H "Authorization: Bearer $LLMKEY" -H "Content-Type: application/json" \
  "http://192.168.18.8:20128/v1/chat/completions" \
  -d '{"model":"<KANDIDAT>","messages":[{"role":"user","content":"Reply with JSON: {\"ok\":true}"}],"max_tokens":50}'
```
Yang `content`-nya **nggak kosong** → itu yang dipakai.

**Service:** `hindsight-api.service` (user unit). `ps` PID berubah; cari via
`systemctl --user status hindsight-api`.

---

## 🔑 Identitas

| Item | Nilai |
|---|---|
| DID | `did:key:z6MkfKukH6d7yqToKpk2mDcETct9hCJ3LdJ8pe5RfGkhVvgz` |
| Fingerprint | `65112d27018cd892` (sha256(DID)[:16]) |
| Seed | **di `identity.json`, chmod 600 — JANGAN pernah dishare** |

## 📍 Lokasi & artefak

| Item | Lokasi / URL |
|---|---|
| Folder kerja | `/home/goonjoru/.hermes/profiles/godhood/workspace/flop-agent/` |
| `identity.json` | folder yang sama (RAHASIA, gitignored) |
| DID note | https://technocore.chat/kv/did-65/112d27018cd892 |
| Room **owned** | https://technocore.chat/r/d-agent-65112d27018cd892 |
| Room check-in lama | https://technocore.chat/r/d-65112d27018cd892 |
| Repo publik | https://github.com/brunoerik417-ship-it/flop-agent |
| Akun GitHub | `brunoerik417-ship-it` |
| State note (Technocore) | `https://technocore.chat/kv/flop-65112d/state` |

## ✅ Yang udah selesai

- [x] Follow `@flop_labs` + `@CryptoHayes`
- [x] DID Ed25519 dibuat (`identity.json`, chmod 600)
- [x] DID note di-publish ke sharded path `/kv/did-65/112d27018cd892`
- [x] Room `d-agent-65112d27018cd892` **diklaim** (owned, cuma DID kita yang bisa nulis)
- [x] Check-in cron aktif: `17 */6 * * *` → `checkin.sh`
- [x] Repo publik dibuat + push (2 commit)
- [x] Kontribusi dicatat di room `technocore` (nonce `1789158769243`)
- [x] `FIELD-NOTES.md`: 8 temuan terverifikasi empiris
- [x] Security audit: nol secret di repo, `identity.json` nggak ke-track

## ⬜ Yang belum

- [ ] **Commit ke-2 belum di-push** (`064481a`) — butuh token GitHub
- [ ] **Post di X** — DID + repo URL + room + seq, tag `@flop_labs`
- [ ] **Backup `identity.json`** ke luar box
- [ ] **Fix hindsight** (lihat section atas)
- [ ] Token GitHub read-only & full **dicabut** di https://github.com/settings/tokens

## 🧠 Temuan teknis (ringkas — detail di FIELD-NOTES.md)

1. Lobby ~30 msg/sec (dua sampel: 32, 28) — check-in lobby hilang ~2 menit
2. `/kv/did` unsharded → 404, harus sharded `/kv/did-<2>/<14>`
3. Signed note cuma boleh `room-owners`/`room-allow`
4. Signature wajib atas text **setelah sweep** — raw text → 403
5. `sign.py` resmi butuh Python **≥3.12**, beda dari versi copy-an orang
6. Rate limit: read 600/min, write 300/min, dupe filter 120s/6 salinan
7. `?since=` wajib; `?wait=` cuma ngefek bareng `since=`
8. Room `d-` harus diklaim **sebelum** pesan pertama, atau selamanya nggak bisa

## 🎯 Konteks airdrop

- Testnet **Q4 2026** (belum live), genesis block **Q1 2027**
- Airdrop ~20,4% supply, didistribusi lewat **partisipasi testnet** — bukan check-in
- Faucet testnet di-host di `technocore.chat`, cuma DID holder yang bisa klaim
- Arthur Hayes konfirmasi **anti-sybil clustering** bakal filter bot repetitif
- **Belum ada** aturan resmi, snapshot date, atau claim page

## 🛡️ Aturan keamanan (JANGAN dilanggar)

- ❌ Jangan pernah share `identity.json` / seed-nya
- ✅ Yang publik cuma string `did:key:z6Mk...`
- ❌ Jangan commit `identity.json`, `*.pem`, `*.key`, `.env`
- ❌ Jangan pakai seed wallet/exchange sebagai seed DID
- ⚠️ Siapapun yang minta seed = scammer, termasuk yang ngaku "support"
