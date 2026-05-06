# KDP Official Specifications — Single Source of Truth

> **Compilato il**: 2026-05-06
> **Fonte**: https://kdp.amazon.com/help (15+ pagine ufficiali consultate)
> **Scopo**: Riferimento autoritativo per tutte le skill, gate, validator e generator del progetto ColorForge AI.
> **Regola d'oro**: Se il codice contraddice questo documento, vince questo documento.

---

## 1. PUBLISHING LIMITS (CRITICO)

| Limite | Valore | Fonte |
|--------|--------|-------|
| Titoli per formato per **settimana** | **10** (non 5/giorno!) | help/topic/G202145060 |
| Account | richiesta esenzione via kdp.amazon.com/contact-us | idem |

⚠️ **Bug attuale**: Il nostro Publisher usa `max_daily_pubs_per_account = 5`. Va cambiato in `max_weekly_pubs_per_format = 10` (per account, per formato — paperback e hardcover sono separati).

Con 3 account × 10/settimana × 2 formati (paperback + hardcover) = **fino a 60 titoli/settimana** in teoria. Realistico: **30 paperback/settimana** = ~120/mese.

---

## 2. TRIM SIZES (PAPERBACK)

### Paperback — taglie standard supportate

| Codice | Inches | mm | Note |
|--------|--------|-----|------|
| `5x8` | 5" × 8" | 127 × 203.2 | regular |
| `5.06x7.81` | 5.06" × 7.81" | 128.5 × 198.4 | regular |
| `5.25x8` | 5.25" × 8" | 133.4 × 203.2 | regular |
| `5.5x8.5` | 5.5" × 8.5" | 139.7 × 215.9 | regular |
| `6x9` | 6" × 9" | 152.4 × 228.6 | **default**, regular |
| `6.14x9.21` | 6.14" × 9.21" | 156 × 234 | large |
| `6.69x9.61` | 6.69" × 9.61" | 169.9 × 244 | large |
| `7x10` | 7" × 10" | 177.8 × 254 | large |
| `7.44x9.69` | 7.44" × 9.69" | 188.9 × 246.1 | large |
| `7.5x9.25` | 7.5" × 9.25" | 190.5 × 235 | large |
| `8x10` | 8" × 10" | 203.2 × 254 | large — **kids** |
| `8.25x6` | 8.25" × 6" | 209.6 × 152.4 | large landscape |
| `8.25x8.25` | 8.25" × 8.25" | 209.6 × 209.6 | large square |
| `8.5x8.5` | 8.5" × 8.5" | 215.9 × 215.9 | large — **mandala/coloring** |
| `8.5x11` | 8.5" × 11" | 215.9 × 279.4 | large — **adult coloring** |

**Custom paperback**: width 4"–8.5", height 6"–11.69".
**Large trim** = width > 6.12" OR height > 9". Costi di stampa più alti.

### Hardcover — solo 5 taglie disponibili

| Codice | Inches |
|--------|--------|
| `5.5x8.5` | 5.5" × 8.5" |
| `6x9` | 6" × 9" |
| `6.14x9.21` | 6.14" × 9.21" |
| `7x10` | 7" × 10" |
| `8.25x11` | 8.25" × 11" |

- Page count: **75–550 pagine** (paperback: 24–828)
- No dust jacket: solo case laminate
- No Amazon.co.jp, no Expanded Distribution
- Royalty: 50% **o** 60% (secondo prezzo)

---

## 3. BLEED — REGOLE ESATTE

**Bleed = 0.125" (3.2 mm)** SOLO su 3 lati: top, bottom, outside edge (NON sul lato gutter).

### Formula KDP ufficiale (interno paperback con bleed):

Copy
Page width with bleed = trim_width + 0.125" Page height with bleed = trim_height + (0.125" × 2)

Copy
Esempio 6×9: pagina diventa **6.125" × 9.25"**.
Esempio 8.5×11: pagina diventa **8.625" × 11.25"**.

⚠️ **Nota importante**: il bleed sull'inside edge non esiste — quel lato è la rilegatura. Il nostro `pdf_assembler.py` ora è corretto (M4 fix), ma verifica che la formula sia esattamente questa.

### Bleed copertina (TUTTI i lati):

Cover Width = 0.125 + back_width + spine_width + front_width + 0.125 Cover Height = 0.125 + trim_height + 0.125

Copy
Sulla copertina il bleed è su **tutti e 4 i lati** (incluso top e bottom).

---

## 4. MARGINS / GUTTER (TABELLA UFFICIALE)

| Page count | Inside (gutter) | Outside no-bleed | Outside with-bleed |
|-----------|----------------|------------------|---------------------|
| 24–150 | **0.375"** (9.6 mm) | ≥ 0.25" | ≥ **0.375"** |
| 151–300 | **0.5"** (12.7 mm) | ≥ 0.25" | ≥ 0.375" |
| 301–500 | **0.625"** (15.9 mm) | ≥ 0.25" | ≥ 0.375" |
| 501–700 | **0.75"** (19.1 mm) | ≥ 0.25" | ≥ 0.375" |
| 701–828 | **0.875"** (22.3 mm) | ≥ 0.25" | ≥ 0.375" |

⚠️ **Bug attuale**: la nostra funzione `_compute_gutter_inches()` ha valori sbagliati. Per 24–150 pagine usa 0.5" invece di 0.375". Sprecando 0.125" di area utile per pagina.

⚠️ **Bug attuale 2**: outside margin non è verificato. KDP richiede ≥ 0.375" con bleed. Il nostro generator può posizionare immagini fino al bordo del trim → rischio rejection.

**Note**:
- Top/bottom/outside non devono avere lo stesso valore — basta che siano ≥ minimo.
- "Inside margin" = "gutter" — usa lo stesso valore in entrambi i campi.
- Page count viene **arrotondato al pari superiore** da KDP.

---

## 5. SPINE (DORSO)

### Formule esatte spine width

| Tipo paper/ink | Formula |
|----------------|---------|
| Black ink, white paper | `pages × 0.002252"` (0.0572 mm) |
| Black ink, cream paper | `pages × 0.0025"` (0.0635 mm) |
| Premium color paper | `pages × 0.002347"` (0.0596 mm) |
| Standard color paper | `pages × 0.002252"` (0.0572 mm) |

### Spine text rules

- Spine text consentito SOLO con **≥ 79 pagine** (non 100!)
- Cover Creator richiede ≥ 80 pagine
- Spazio testo–bordo spine: **≥ 0.0625"** (1.6 mm)
- Variance fold line: **±0.0625"** (1.6 mm) — non usare hard edges sullo spine
- Spine shift print variance: fino a 0.0125" (3.2 mm) accettabile

⚠️ **Bug attuale**: la nostra `kdp-specs.md` blocca spine text sotto 100 pagine. Va corretto a **79**.

---

## 6. INTERIOR FILE — FILE SPECIFICATIONS

| Elemento | Requisito |
|----------|-----------|
| Formato (con bleed) | **PDF obbligatorio** |
| Formato (no bleed) | PDF, DOC, DOCX, RTF, HTML, TXT |
| File size max | **650 MB** |
| PDF format | **PDF/X-1a preferito** |
| Image DPI minimo | **300 DPI** |
| Image DPI massimo raccomandato | 600 DPI (per restare < 650 MB) |
| Font minimo | **7 pt** |
| Font embedding | **completo** (no subset) — embed all fonts |
| Layers/transparency | **flatten** prima dell'export |
| Crop/trim marks | **vietati** |
| Encryption | **vietata** |
| Bookmarks/comments/metadata | **rimuovere** |
| Page spreads | **vietati** — single-page files only |
| Reading direction | LTR; RTL solo per ebraico, yiddish, giapponese |
| Page orientation | tutte le pagine stessa orientazione |
| Linea minima | **0.75 pt** (0.01" / 0.3 mm) |
| Grayscale fill | **min 10%** se uso ink B/W con sfondi grigi |
| Page count min | **24** |
| Page count max | dipende da ink/paper/trim (vedi calcolatore KDP) |

### Pagination rules
- Even numbers a sinistra, odd a destra (LTR)
- Max **4 pagine bianche consecutive** all'inizio o in mezzo
- Max **10 pagine bianche consecutive** alla fine

---

## 7. COVER FILE — SPECIFICATIONS

| Elemento | Requisito |
|----------|-----------|
| Formato | **PDF singolo** (back + spine + front in un file) |
| File size max | 650 MB (raccomandato < 40 MB) |
| Color mode | **CMYK** (immagini) |
| DPI | **≥ 300 DPI**, immagini @ 100% size, flatten |
| Bleed | 0.125" su tutti e 4 i lati |
| Safe zone | contenuto importante a **≥ 0.25"** dal bordo esterno |
| Spine safe zone | **≥ 0.0625"** dai bordi spine |
| Borders | sconsigliati; se presenti, ≥ 0.25" dentro il trim |
| Font embedding | **completo** |
| Cover Creator (alternativa) | accetta JPG, PNG, GIF |

### Barcode area
- Posizione: **angolo in basso a destra del back cover**
- Dimensione: **2" × 1.2"** (50.8 × 30.5 mm), area bianca
- Se non fornisci barcode, KDP ne aggiunge uno automaticamente
- ⚠️ **Vietato testo o oggetti in quest'area** — il barcode li coprirà

### eBook cover (per riferimento)
- Min: 1000 px altezza × 625 px larghezza
- Max: 10 000 × 10 000 px

---

## 8. METADATA — REGOLE TASSATIVE

### Title
- Massimo **200 caratteri** combinati title + subtitle
- Deve **corrispondere esattamente** al cover (front o spine)
- **Vietato**: "bestselling", "free", parole ripetute generiche ("notebook", "journal", "books"), HTML tags, "n/a", solo punteggiatura, riferimenti a marchi non autorizzati, riferimenti a "bundled set" o "boxed set"
- < 60 caratteri raccomandato (oltre i clienti scrollano)

### Subtitle
- Stessi requisiti del title
- Limite combinato 200 char con title

### Description
- Massimo **4 000 caratteri** (HTML tags inclusi nel conteggio)
- HTML supportati: `<br> <p> <b> <em> <i> <u> <h4>–<h6> <ol> <ul> <li>`
- HTML **non** supportati: `<h1> <h2> <h3>`
- **Vietati**: contenuto pornografico, telefoni, email, URL, recensioni, citazioni, richieste di review, advertising, info time-sensitive, info su prezzi/disponibilità, spoiler, emoji unicode, frasi keyword/tag

### Keywords
- Esattamente fino a **7** keyword/short phrase
- Best practice: phrase di **2–3 parole**
- **Vietate**: nomi altri autori, "bestselling", "free", "new", spelling errors, varianti spazi/punteggiatura, marchi non autorizzati, virgolette, "Kindle Unlimited", "KDP Select", HTML tags, info già nel title/category
- Useful types: setting, character types/roles, plot themes, story tone

### Author
- Pen name ammesso (purché non confondi con altro autore famoso)
- No HTML tags

### ISBN
- **Obbligatorio per paperback e hardcover** (eccezione: low-content book)
- Free KDP ISBN solo per uso su KDP
- Ogni formato (paperback vs hardcover) richiede ISBN diverso
- Imprint: 100 char max, case-sensitive (anche spazi finali contano)
- Free ISBN → imprint = "Independently published"

---

## 9. CONTENT GUIDELINES — AI DISCLOSURE

### Definizioni KDP ufficiali

- **AI-generated** (DEVE essere dichiarato): testo, immagini o traduzioni create da AI tool. Anche con editing successivo sostanziale, resta "generated".
- **AI-assisted** (NON va dichiarato): contenuto creato da te, con AI usato per editare, rifinire, brainstorming.

### Per ColorForge

Il nostro contenuto è **AI-generated** (immagini Gemini, testi Claude). Quindi:
- Flag `ai_disclosure: True` nel listing → **obbligatorio**
- Già implementato nel `ListingContract`
- Da dichiarare al momento della pubblicazione nel form KDP (campo specifico)

### Contenuto vietato (rejection automatica)
- Hate speech, abuse/sexual exploitation children, pornografia, glorificazione rape/pedofilia, terrorismo
- Copyright/trademark violation
- Public domain non differenziato (se versione free già su Amazon)
- Score/lyrics songs JASRAC (Giappone)

### Trademark blacklist (parziale, da estendere)
disney, marvel, dc comics, harry potter, pokemon, star wars, mickey mouse, pixar, frozen, paw patrol, peppa pig, bluey, encanto, super mario, nintendo, sonic, hello kitty, sanrio, pokemon, dragon ball, naruto, batman, superman, spider-man, avengers, lego, barbie...

⚠️ **Bug attuale**: il nostro `listing_gate.py` controlla solo 43 termini. Vanno aggiunti almeno: encanto, paw patrol, peppa pig, bluey, lego, hello kitty, dragon ball, naruto, sonic.

---

## 10. PRINTING COSTS — PAPERBACK (USD, Amazon.com)

### Black ink
| Pages | Cost |
|-------|------|
| 24–108 | $2.30 (fixed only) |
| 110–828 | $1.00 + ($0.012 × pages) |

### Premium color (ink consigliato per coloring books pubblicati a colori)
| Pages | Cost |
|-------|------|
| 24–40 | $3.60 (fixed only) |
| 42–828 | $1.00 + ($0.065 × pages) |

### Standard color (paperback only)
| Pages | Cost |
|-------|------|
| 72–600 | $1.00 + ($0.0255 × pages) |

**Per coloring books a stampa B/W**: black ink + white paper.
**Per coloring books con preview/cover a colori**: premium color (più costoso ma qualità superiore).

### Esempio realistico per coloring book 75 pagine B/W:
- Print cost: $1.00 + (75 × $0.012) = **$1.90**
- List price: $7.99
- Royalty 60%: 0.60 × $7.99 = $4.794
- Royalty netto: $4.794 − $1.90 = **$2.894 / copia**

---

## 11. ROYALTY & PRICING

### Paperback / Hardcover
- Royalty: **60%** (Amazon marketplace) o **50%** (Expanded Distribution)
- Hardcover: 50% e 60% disponibili
- Min list price = printing_cost / royalty_rate
- Max list price USD: **$250**
- Max EUR: 250, GBP: 250, CAD: 350, AUD: 350, JPY: 30 000

### eBook
- 35% (qualunque prezzo)
- 70% solo se prezzo USD $2.99–$9.99 e in territori eligible
- File size influenza prezzo minimo (3 MB / 10 MB tier)

⚠️ **Bug attuale**: Il nostro SEO listing genera prezzi via "anchor table". Verificare che `price_min ≥ printing_cost / 0.60`. Per 75 pagine B/W: min ≈ $3.17. OK.

### Fixed-price law countries
- **eBook**: Austria, Belgio, Francia, Germania, Grecia
- **Paperback/Hardcover**: aggiungere Italia, Messico, Olanda, Norvegia, Slovenia, Spagna
- In questi paesi, il prezzo deve essere identico su tutti i retailer.

---

## 12. KDP SELECT (solo eBook)

- Programma di **90 giorni**, **eBook only**
- **Esclusività**: durante l'enrollment, l'eBook NON può essere venduto digitalmente altrove (sito tuo, blog, altri retailer)
- Include automaticamente in Kindle Unlimited (KU)
- Benefici: Kindle Countdown Deals (KCD), Free Book Promotions
- ColorForge produce paperback → **non rilevante** finché non aggiungiamo eBook coloring

---

## 13. CATEGORIES (BISAC + KDP)

- KDP permette **3 categorie** durante setup
- Categorie diverse per marketplace e per formato (eBook vs paperback)
- **Coloring books NON sono "low-content"** — sono "activity books" (vedi sezione low-content)
- BISAC code consigliati per coloring book:
  - `GAM019000` Games & Activities / Coloring Books
  - `ART015000` Art / Color Theory
  - `CRA019000` Crafts & Hobbies / Reference

---

## 14. LOW-CONTENT BOOK — CHIARIMENTO CRITICO

Secondo KDP **ufficialmente**:
> Low-content books include notebooks, planners, diaries, prompt journals, log books, coupon books, score card templates. **Coloring books NON sono low-content** (sono activity books, with non-repetitive content).

**Implicazione per ColorForge**:
- ❌ NON selezionare "Low-content" durante setup KDP
- ✅ ISBN gratuito KDP è disponibile e raccomandato
- ✅ Series eligible (possiamo creare serie)
- ✅ Read Sample (Look Inside) supportato
- ✅ Expanded Distribution disponibile

---

## 15. PRE-PUBLICATION CHECKLIST (KDP MANUAL REVIEW)

Cosa verifica KDP nella revisione manuale:

- [ ] Title/author/ISBN nel manuscript matchano metadata KDP esattamente
- [ ] Bleed corretto: contenuto a 0.125" oltre trim (3 lati interno, 4 lati cover)
- [ ] Pagination sequenziale (even-left, odd-right)
- [ ] No più di 4 blank pages consecutive (10 alla fine)
- [ ] Testo ≥ 7 pt
- [ ] Spine text solo se ≥ 79 pagine, ≥ 0.0625" dai bordi
- [ ] No template placeholder ("Insert text here", "Book title", ecc.)
- [ ] Margins rispettati per page count
- [ ] Cover non eccede edge
- [ ] No "bundled set", "boxed set" wording
- [ ] No "spiral", "hard bound", "leather bound", "calendar" wording (binding mismatch)
- [ ] Font embedded
- [ ] Transparencies flattened
- [ ] No encryption, no crop marks, no annotations

---

## 16. PRINT OPTIONS — INK & PAPER

### Paperback
- **Black ink + white paper** 50–61 lb (74–90 GSM)
- **Black ink + cream paper** 50–61 lb (74–90 GSM)
- **Premium color + white paper** 60–71 lb (88–105 GSM)
- **Standard color + white paper** 50–61 lb (74–90 GSM)

### Hardcover
- Stesse opzioni paperback **eccetto standard color** (non disponibile)

### Cover finish
- **Glossy** (lucido) o **matte** (opaco)
- Hardcover: case laminate (no dust jacket)

⚠️ **Lock dopo publish**: ink/paper type **non modificabili** dopo pubblicazione. Per cambiare → unpublish + republish (nuova edizione).

---

## 17. TIMELINE PUBLICATION

- Title creation: limit 10/format/week per account
- Submission → automated check (Print Previewer) → manual check
- Approvazione: tipicamente 24–72h
- Categorie: fino a 72h per visualizzazione
- Updates a metadata (title, description, keyword): trigger re-review eccetto solo prezzo

---

## 18. FILE NAMING

- **Vietati**: emoji, caratteri speciali non supportati
- Raccomandato: ASCII, no spazi (usa underscore o trattino), estensione corretta `.pdf`
- Esempio buono: `coloring_book_ocean_mandala_75pages.pdf`
- Esempio cattivo: `Mandalas Océan™ 🐋.pdf`

---

## 19. BUG MAP — Discrepanze codice attuale vs spec ufficiali

| ID | Severità | File | Problema | Fix |
|----|----------|------|----------|-----|
| K01 | **P0** | publisher_agent.py | quota giornaliera (5/day) errata | weekly per format (10) |
| K02 | **P0** | pdf_assembler.py `_compute_gutter_inches` | gutter 0.5" per 24–150 invece di 0.375" | tabella corretta |
| K03 | **P0** | pdf_assembler.py | outside margin non validato (può essere 0") | aggiungere check ≥ 0.375" |
| K04 | **P1** | kdp-specs.md | spine text bloccato sotto 100 pagine | abbassare a 79 |
| K05 | **P1** | listing_gate.py | trademark blacklist incompleta | aggiungere encanto, peppa pig, ecc. |
| K06 | **P1** | generator.py cover | output RGB invece di CMYK | conversione CMYK con USWebCoatedSWOP |
| K07 | **P1** | generator.py cover | barcode area non riservata | white box 2"×1.2" angolo bottom-right |
| K08 | **P2** | strategist.py | trim_size hardcoded 8.5×11 | enum TrimSize (15 paperback + 5 hardcover) |
| K09 | **P2** | listing_gate.py | "low-content" check assente | flag esplicito `low_content: False` per coloring |
| K10 | **P2** | exceptions.py | nessuna validazione safety zone cover | CoverComplianceValidator |
| K11 | **P2** | book_plan.py | manca `paper_type` (white/cream/color) | enum PaperType |
| K12 | **P2** | book_plan.py | manca `cover_finish` (glossy/matte) | enum CoverFinish |
| K13 | **P3** | tutto | nessun controllo file size 650 MB | guard pre-upload |
| K14 | **P3** | front matter | non implementato | skill kdp-frontmatter |

---

## 20. RIFERIMENTI UFFICIALI

| Topic | URL |
|-------|-----|
| Trim size, bleed, margins | https://kdp.amazon.com/help/topic/GVBQ3CMEQW3W2VL6 |
| Paperback submission | https://kdp.amazon.com/help/topic/G201857950 |
| Cover paperback | https://kdp.amazon.com/help/topic/G201953020 |
| Cover hardcover | https://kdp.amazon.com/help/topic/GDTKFJPNQCBTMRV6 |
| Hardcover overview | https://kdp.amazon.com/help/topic/GAVW3FZZAKA2KY3B |
| Hardcover submission | https://kdp.amazon.com/help/topic/GKYZRXFBZH2LDXAK |
| Manuscript file specs | https://kdp.amazon.com/help/topic/G202145060 |
| Print options ink/paper | https://kdp.amazon.com/help/topic/G201834180 |
| Cover Creator | https://kdp.amazon.com/help/topic/G201113520 |
| Cover Calculator | https://kdp.amazon.com/cover-calculator |
| Metadata guidelines | https://kdp.amazon.com/help/topic/G201097560 |
| Description | https://kdp.amazon.com/help/topic/G201189630 |
| Keywords | https://kdp.amazon.com/help/topic/G201298500 |
| Categories | https://kdp.amazon.com/help/topic/G200652170 |
| Content guidelines + AI disclosure | https://kdp.amazon.com/help/topic/G200672390 |
| Low-content books | https://kdp.amazon.com/help/topic/GGE5T76TWKA85DJM |
| ISBN | https://kdp.amazon.com/help/topic/G201834170 |
| Royalty paperback | https://kdp.amazon.com/help/topic/GSQF43YAMUPFTMSP |
| Royalty hardcover | https://kdp.amazon.com/help/topic/G77F3WPD3KQLJTFS |
| eBook pricing | https://kdp.amazon.com/help/topic/G200634560 |
| Printing cost paperback | https://kdp.amazon.com/help/topic/G201834340 |
| Printing cost hardcover | https://kdp.amazon.com/help/topic/GHT976ZKSKUXBB6H |
| KDP Select | https://kdp.amazon.com/help/topic/G200798990 |
| Fix paperback formatting | https://kdp.amazon.com/help/topic/G201834260 |
| Manuscript templates | https://kdp.amazon.com/help/topic/G201834230 |
| Title creation limit | https://kdp.amazon.com/help/topic/G202145060 |
| Barcodes | https://kdp.amazon.com/help/topic/G5HDYGP4BXLX4RUW |

---

**Fine documento.** Aggiornare questo file quando KDP modifica le policy (ultimo check: 2026-05-06).