# Elemental Duel - Skriftlig rapport

## 1. Inledning och syfte
Detta projekt genomfördes inom kursen Cloud Native Computing (Inlämningsuppgift 2) med målet att bygga, testa och driftsätta en molnnativ applikation med CI/CD till Kubernetes.

Lösningen består av tre delar:
1. Ett spel-API i Go (Battle API) med MySQL som databas.
2. Ett kompletterande CRUD-API i Python (Analytics API) med en annan databas (SQLite).
3. En frontend i Python/Flask som konsumerar API:erna.

Arkitekturen, lokala körinstruktioner och tekniska detaljer finns sammanfattade i README (se `README.md`). Denna rapport fokuserar på lösningens tekniska utformning, drift och verifiering.

## 2. Arkitekturöversikt
Applikationen är uppdelad i tre mikrotjänster:

- **Battle API (Go + Gin + GORM)**
  - Ansvarar för spelrundor och statistik.
  - Lagrar spelomgångar i MySQL.
  - Exponerar endpointar för health, rundor och statistik.

- **Analytics API (Python + Flask-RESTX + SQLAlchemy)**
  - Hämtar statistik från Battle API och sparar snapshots.
  - Exponerar full CRUD för snapshots.
  - Dokumenteras med surfbar Swagger på `/docs`.
  - Lagrar data i SQLite som separat analysdatabas.

- **Frontend (Python + Flask + Jinja2)**
  - Visar spelläge, resultat och statistik.
  - Anropar Battle API för att spela rundor.
  - Anropar Analytics API för sammanställning.

I Kubernetes körs dessa som separata Deployments/Services med tillhörande konfiguration i manifests under respektive tjänsts `k8s`-katalog.

Fördjupning och exakta kommandon finns i `README.md`.

## 3. CI/CD-flöde
CI/CD-lösningen är uppdelad i flera jobb:

1. **Path filter i monorepo**
   - Endast relevanta jobb körs beroende på vilka mappar som ändrats.

2. **Service-specifika jobb**
   - Battle API: Go-format/lint (`gofmt`, `go vet`) + tester + image build/push.
   - Analytics API: Python lint/test + image build/push.
   - Frontend: Python lint/test + image build/push.

3. **Full-suite jobb**
   - Startar hela stacken med Docker Compose.
   - Kör integrationstester, Newman (API-kontrakt) och Playwright (E2E).

Detta verifierar både komponentnivå och systemnivå innan kod anses klar.

Detaljer om körning och testlager finns i `README.md`.

## 4. Kubernetes och drift
### 4.1 Lokal Kubernetes
Lösningen är körbar lokalt i Kubernetes med manifests i:
- `k8s/`
- `battle-api-go/k8s/`
- `analytics-api-py/k8s/`
- `frontend-py/k8s/`

Frontend är konfigurerad för lokal åtkomst via ClusterIP + port-forward. Exakta steg och kommandon finns i README.

### 4.2 AWS/EKS-overlay
För molnkluster finns separat overlay i `k8s-aws/` (bl.a. StorageClass/LoadBalancer-anpassning). Detta höll lokal setup och cloud setup tydligt separerade.

### 4.3 Datapersistens och backup
- MySQL och SQLite använder persistent storage i Kubernetes.
- Backup till S3 sker via schemalagda CronJobs.
- S3-hemligheter hålls utanför versionshantering via template + gitignore (se README).

## 5. Teststrategi och kvalitet
Projektet använder en testpyramid:
- **Unit tests** för Go och Python-tjänster.
- **Integrationstester** för samspel mellan tjänster.
- **API-tester** med Postman/Newman.
- **E2E-tester** med Playwright (desktop + mobil layout).

Resultatet är att både intern logik och verkliga användarflöden verifieras.

## 6. Dokumentation och reproducerbarhet
README fungerar som operativ manual och innehåller:
- arkitektursammanfattning,
- steg-för-steg för lokal körning (Docker Compose och Kubernetes),
- API-översikt,
- testöversikt,
- CI/CD-beskrivning.

Se `README.md` för exakta kommandon, portar, endpointar och felsökningsnära information.

## 7. Skärmdumpsbilagor (lämnas separat)
Följande skärmdumpar hänvisas till i inlämningen och bifogas separat tillsammans med rapporten:

1. **Bilaga A - Kubernetes pods i Running**
   - Exempel: `kubectl get pods -n elemental-duel`

2. **Bilaga B - Frontend i webbläsare**
   - Spelrunda genomförd och resultat visat.

3. **Bilaga C - Analytics Swagger**
   - `/docs` öppnad och CRUD-endpointar synliga.

4. **Bilaga D - CI pipeline lyckad i GitHub Actions**
   - Samtliga relevanta jobb gröna.

5. **Bilaga E - Container images i registry**
   - Battle, Analytics, Frontend publicerade.

6. **Bilaga F - S3-backup artefakter**
   - Uppladdade backupfiler från CronJobs.

## 8. Slutsats
Projektet levererar en komplett cloud native-lösning med separerade tjänster, databaspersistens, testautomatisering och reproducerbar drift i både lokal miljö och Kubernetes.

Sammantaget dokumenteras lösningen på ett sätt som gör den möjlig att granska, köra och verifiera med stöd av instruktionerna i README samt de separata skärmdumpsbilagorna i inlämningen.
