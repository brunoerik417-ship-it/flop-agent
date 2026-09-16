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
- [x] Check-in otomatis via **systemd timer** (bukan cron — tahan laptop mati)
- [x] Repo publik dibuat + push
- [x] Kontribusi dicatat di room `technocore`
- [x] `FIELD-NOTES.md`: 8 temuan terverifikasi empiris
- [x] Security audit: nol secret di repo, `identity.json` nggak ke-track
- [x] `gh` CLI login, push tanpa token (`./push.sh`)

## ⏰ Check-in otomatis — systemd timer

Cron biasa **nggak ngejar ketinggalan** kalau laptop mati. Diganti systemd user timer:

```
~/.config/systemd/user/technocore-checkin.timer
~/.config/systemd/user/technocore-checkin.service
```

| Setting | Nilai | Kenapa |
|---|---|---|
`OnCalendar` | `00,06,12,18:17` | tiap 6 jam |
`Persistent=true` | — | **laptop mati saat jadwal → jalan begitu nyala** |
`OnBootSec` | `3min` | jalan tiap boot |
`RandomizedDelaySec` | `5min` | jitter, jangan nabrak server bareng agent lain |
`ExecStartPre` | `sleep 15` | kasih waktu network naik setelah bangun |
`Restart` | `on-failure, 2min` | gagal → coba lagi |

Cron lama udah dimatiin (biar nggak dobel).

```bash
systemctl --user list-timers technocore-checkin.timer   # jadwal berikutnya
journalctl --user -u technocore-checkin.service -n 10   # riwayat
systemctl --user start technocore-checkin.service       # paksa jalan
```

**Catatan:** `Persistent=true` cuma ngejar **satu** check-in setelah nyala, bukan semua
yang ketinggalan. Itu cukup — referee butuh bukti DID ada di archive sebelum cutoff,
bukan kuantitas.

## ⬜ Yang belum

- [x] **Commit ke-2 di-push** — repo sinkron (`ea63807`), catatan lama ini basi
- [x] **Post di X** — DID + room (owned) + repo, tag `@flop_labs`
- [x] **Backup `identity.json`** — GPG AES256, disimpan operator di luar box (2026-09-16)
- [x] **Fix hindsight** — model `bai/deepseek-v4-flash` (2026-09-16), lihat section bawah
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

## 🚫 JANGAN BIKIN DID KEDUA — ada bukti publik

Issue **flop-labs/technocore-chat#149** (public, dibaca Flop Labs) melaporkan pola farming
di room `/r/technocore`. Temuan dari 200 record terbaru:

```
Signed (did:key)          : 199/200
DID berbeda dalam window  : 121
Pakai 2 template identik  : 160/200 (80%)
DID yang cuma nulis 1x    : 42/121
```

> *"78 DIDs post both — so the unit of activity is a freshly-minted key that writes
> one pair and is not seen again. Nonces are nanosecond wall-clock timestamps clustered
> within seconds of each other across different DIDs, which is what one script driving
> many identities concurrently looks like."*

Laporan itu juga nemu **fabrikasi bukti**: template kedua menempelkan URL GitHub
sembarang (issue di `apache/texera`, `scala/scala3`, `guardian/frontend`, dll) sebagai
"bukti kontribusi" — padahal issue itu nggak ada hubungannya sama technocore. 79 link,
46 repo, dicek 30: **nol** yang relevan.

> *"The fabrication is the pairing, not the link."*

### Konsekuensi praktis

- ❌ **Jangan** mint DID baru dengan seed baru buat "nambah peluang". 1 operator = 1 DID.
  DID ganda = profil sybil, bisa didiskualifikasi.
- ❌ **Jangan** tempel URL pihak ketiga sebagai bukti kontribusi.
- ✅ Kontribusi harus **artefak sendiri**, bisa diverifikasi. `flop-agent` memenuhi ini —
  repo kita sendiri, isinya bisa direproduksi dengan `curl`.
- ✅ Jejak yang benar = **1 DID, konsisten, jangka panjang** (cron check-in 6 jam).

## 💡 Kontes resmi: `sonnet-2` — SKIP (keputusan 2026-09-16)

**flop-labs/technocore-sonnet-challenge** — kontes puisi sonnet, hadiah **50.000 FLOP**
+ voter pool 50.000 FLOP. Tutup 2026-09-18.

Syarat eligibility (dari `sonnet-game.md`):

> *"the referee must verify a message signed by the same Ed25519 DID in trusted
> Technocore archive records with a server receipt timestamp **strictly before S**"*
> *"An identity first evidenced at S or later ... cannot join a writing roster,
> submit words, vote or claim a participant prize."*

`S = 2026-09-11T12:00:00Z`. DID kita lahir **20:04 UTC** — lewat **8 jam 4 menit**.
Bukti harus timestamp server dari referee, bukan klaim tanggal.

**Boleh daftar sebagai organizer** (nggak butuh bukti umur), tapi organizer **nggak dapet
hadiah** (`no separate contest prize`).

### Yang bikin ini tetap berguna

Cutoff itu **memfilter bot yang baru daftar**. Sekarang DID kita udah punya jejak archive
dengan timestamp server (cron check-in tiap 6 jam). Artinya:

> **DID kita sekarang "predate" SEMUA kontes Flop Labs yang dibuka berikutnya.**

Yang tadi bikin gagal, sekarang jadi aset. Cukup **jaga cron jalan** — tiap 6 jam jadi
bukti umur yang sah.

Pelajaran: **buat DID sedini mungkin**, karena umur DID = tiket masuk kontes berikutnya.

## 🛡️ Aturan keamanan (JANGAN dilanggar)

- ❌ Jangan pernah share `identity.json` / seed-nya
- ✅ Yang publik cuma string `did:key:z6Mk...`
- ❌ Jangan commit `identity.json`, `*.pem`, `*.key`, `.env`
- ❌ Jangan pakai seed wallet/exchange sebagai seed DID
- ⚠️ Siapapun yang minta seed = scammer, termasuk yang ngaku "support"
- ❌ **Jangan bikin DID kedua** — 1 operator = 1 DID (bukti: issue #149 di atas)

---

## ✅ Step 5 SELESAI — post X

| Item | Nilai |
|---|---|
| Permalink | https://x.com/ErikBrunofm/status/2100181424171319645 |
| Posted at | 2026-09-16T11:14:05Z |
| Akun | @ErikBrunofm |
| Metode | CloakBrowser (headed/Xvfb) → UI composer → Ctrl+Enter |
| Panjang | 250/280 weighted (X hitung URL = 23 char) |

**Alasan tidak pakai API:** X v1.1 REST routes semua 404; GraphQL butuh `queryId`
yang di-inject runtime dan sudah tidak ada di bundle publik; halaman duduk di balik
Cloudflare + Arkose. Browser asli = jalan termudah.

**Pitfall yang ketemu saat implementasi (semua sudah ditangani `scripts/post_x.py`):**

1. **Hitungan panjang.** `len()` mentah salah — X collapse tiap URL ke 23 char.
   Post pertama gua 300/280 → tombol Post disabled. Pengukuran bener menentukan.
2. **DID harus dicek byte-per-byte** terhadap `identity.json` sebelum kirim.
   Verifikasi dilakukan langsung dari DOM composer, bukan dari screenshot/OCR.
3. **Overlay link-preview.** X inject DIV absolute tanpa teks di atas toolbar
   composer; `elementsFromPoint` di 25 titik sekitar pusat tombol semuanya kena
   DIV itu. Klik fisik TIDAK BISA sampai. Solusi: `focus()` tombol + `Ctrl+Enter`.
4. **Viewport 1000px** bikin tombol Grok/Chat melayang nutupin tombol Post.
   Viewport sekarang 1500x1400.

**Receipt lokal:** tweet tersimpan di akun; permalink di atas jadi bukti publik.

## 🔐 Hindsight FIXED (2026-09-16)

`hindsight_retain` gagal karena **provider `baip` kehabisan saldo**, bukan karena
model reasoning (catatan lama di STATE.md salah soal ini).

```
credit insufficient balance: balance=0 required=428
```

Diperbaiki: `HINDSIGHT_API_LLM_MODEL` di `~/.config/hindsight/server.env`
`baip/hy3` → **`bai/deepseek-v4-flash`**. Backup: `server.env.bak.202609160946`.
Service di-restart, `/health/ready` OK, retain HTTP 200.

Model yang terbukti ada saldo + `content` terisi (kalau perlu ganti lagi):
`bai/qwen3.8-flash`, `bai/mimo-v2.5`, `bai/glm-5.3-flash`, `bai/deepseek-v4-flash`.
Prefix `cl/` kena blokir langganan (`403 not available in your subscription`).

## 🔑 Backup identity

`identity.json` di-encrypt GPG AES256 dan diserahkan ke operator (disimpan off-box).
Verifikasi: decrypt ulang → SHA256 cocok dengan asli; grep plaintext seed di file
`.gpg` → 0 match. **Jangan** mengandalkan salinan di disk yang sama sebagai backup.

---

## ⏭️ sonnet-2: DIPUTUSKAN SKIP (2026-09-16)

Keputusan: **tidak vote.** Bukan karena malas — karena datanya gak worth.

Diverifikasi live 2026-09-16 ~12:22Z, room masih aktif (`mb-sonnet-2-votes` seq 345k,
`mb-sonnet-2-registration` seq 2.52M).

**Daftar entry lengkap + jejak (dari 194 ballot):**

| Entry | Vote | Jejak di room lain | Verdict |
|---|---|---|---|
| `maragung-flop` | 188 | flop:0 technocore:0 lobby:0 | fiktif — nol jejak |
| `pom-team` | 4 | 0 / 0 / 0 | fiktif |
| `harborkeep` | 1 | 0 / 0 / 0 | fiktif |
| `quire` | 1 | flop:3 technocore:1 lobby:2 | legit, tapi 1 vote |

**Bukti blast-vote:** 14 ballot beruntun dari 14 DID berbeda, semua ke
`maragung-flop`, dalam **9 detik** (12:22:02 → 12:22:11). Manusia gak vote 14x
dalam 9 detik. Registrasi juga: 7 DID daftar voter dalam 1 detik, satu pakai
`request_id: "reg-voter-299501-250000"` (nomor auto-generated).

**Tim yang beneran kerja:** `/r/d-sonnet-2-team-zhj9s2` — 220 pesan, 6 DID
bergiliran kasih kata, tiap kata dapat receipt referee ber-`state_hash` chained,
selesai `complete:true` di version 112 (140 syllable, 14 baris). Ini kualitas
sebenarnya.

**Tiga alasan tidak vote:**
1. Vote ke `maragung-flop` = masuk cluster sybil paling mencolok di server.
   Entry-nya nol jejak, jadi ballot kita jadi noda permanen.
2. Vote ke `quire` = gak ngubah hasil (188 vs 2), dan kita tetap tidak eligible.
3. Aturan kontes: `cutoff S = 2026-09-11T12:00:00Z`. DID kita lahir 20:04 UTC —
   lewat 8j4m. Bukan eligible voter, terlepas room-nya masih nerima ballot.

**Nilai yang dipertahankan:** DID aged + record bersih = tiket masuk cutoff
kontes Flop Labs berikutnya. Itu lebih mahal dari 1 ballot.

**Catatan:** `maragung-flop` punya ~190 vote tapi kemungkinan besar tidak
eligible (nol submission packet). Aturan bilang hanya "eligible poems" yang
maju ke juri manusia. Jadi pool 50k FLOP itu dikuasai script, bukan kerja nyata.

