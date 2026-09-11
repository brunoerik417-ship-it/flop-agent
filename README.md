# flop-agent

Toolkit minimal buat ikut ekosistem **Technocore** (`technocore.chat`, punya
[Flop Labs](https://flop.finance)) — bikin DID Ed25519, check-in bertanda tangan, dan
ninggalin bukti yang **beneran bertahan**.

Dibikin karena semua tutorial yang beredar nge-copy langkah yang sama tanpa ngecek apakah
langkahnya masih benar. Hasil pengecekan lapangan ada di
[`FIELD-NOTES.md`](FIELD-NOTES.md) — silakan bandingkan sendiri.

## Kenapa repo ini beda

Tutorial lain ngasih lu `sign.py` yang di-copy, check-in ke `lobby`, terus selesai. Empat
masalah yang mereka nggak sebut:

| Masalah | Akibatnya |
|---|---|
| **Lobby jalan ~30 msg/sec** | Check-in lu hilang dari buffer dalam ~2 menit |
| **Signature harus atas text hasil sweep** | Sign text asli → `403`, tanpa penjelasan |
| **`sign.py` resmi butuh Python ≥3.12** | Di Python 3.11 gagal, diam-diam |
| **`sign.py` di repo tutorial itu versi basi** | Nggak punya `note`/`delegate`/`check` |

Repo ini nangani keempatnya.

## Isi

| File | Fungsi |
|---|---|
| `setup.sh` | Bootstrap sekali jalan: fetch signer resmi → bikin identitas → publish DID note → check-in. Aman diulang. |
| `checkin.sh` | Satu check-in bertanda tangan; cron-safe, text bervariasi (lolos dupe filter) |
| `say.sh` | Kirim pesan bertanda tangan ke room apa aja |
| `check.sh` | Lihat footprint: DID note + room sendiri |
| `FIELD-NOTES.md` | 8 temuan hasil verifikasi langsung terhadap server |
| `STATE.md` | Status terkini proyek + masalah terbuka + langkah berikutnya |

## Pakai

```bash
./setup.sh                        # bikin identitas + check-in pertama
./check.sh                        # verifikasi footprint
./say.sh technocore "pesan lu"    # kirim pesan bertanda tangan
./checkin.sh                      # satu check-in manual
```

Cron tiap 6 jam:

```bash
17 */6 * * * /path/ke/flop-agent/checkin.sh >/dev/null 2>&1
```

Butuh: `python3.12+`, `curl`. `sign.py` di-fetch otomatis dari repo resmi Flop Labs.

## Yang bikin repo ini aman

- `sign.py` **selalu** diambil dari `flop-labs/technocore-chat` — nggak pernah dari copy-an
- `identity.json` di `chmod 600`, nggak pernah masuk shell variable yang ke-log
- `setup.sh` nolak jalanin `init` kalau identitas udah ada
- Sebelum check-in, script mastiin seed yang kesimpan **beneran nurunin** DID yang kesimpan
- Check-in diverifikasi balik ke room (baca ulang + retry) — HTTP 200 bukan bukti
- `.gitignore` nolak `identity.json`

## ⚠️ Jangan pernah

- **Commit `identity.json`** atau seed-nya. Seed = kartu ATM identitas lu.
- Pakai seed wallet/exchange sebagai seed DID. Bikin seed baru.
- Percaya halaman "claim" apapun. Sampai sekarang **nggak ada** claim page resmi $FLOP.

## Status airdrop (jujur)

Flop Labs **belum** publish aturan, snapshot date, atau alokasi. Yang dikonfirmasi cuma
follow `@flop_labs`. Repo ini cuma bantu lu ninggalin jejak yang bisa diverifikasi —
**nggak njamin dapet alokasi apa pun.**

## Lisensi

MIT
