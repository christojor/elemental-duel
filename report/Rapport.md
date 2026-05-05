# Elemental Duel - Skriftlig rapport

## 1. Inledning och syfte
Detta projekt genomfördes inom kursen Cloud Native Computing (Inlämningsuppgift 2) med målet att bygga, testa och driftsätta en molnnativ applikation med CI/CD till Kubernetes.

Lösningen levererar **Elemental Duel** — en spelapplikation baserat på sten-sax-påse, men med ett uttökat regelverk med fem element (eld, vatten, jord, luft och blixt) där spelaren duellerar mot datorn. Varje element slår exakt två andra element och förlorar mot två andra, vilket skapar en symmetrisk och välbalanserad spelmekanik.

Lösningen består av tre mikrotjänster:
1. Ett spel-API i Go (Battle API) med MySQL som databas för att lagra spelrundor.
2. Ett kompletterande CRUD-API i Python (Analytics API) med en separat databas (SQLite) för att samla statistik-snapshots.
3. En frontend i Python/Flask som konsumerar API:erna och presenterar spelets användargränssnitt.

Arkitekturen, lokala körinstruktioner och tekniska detaljer finns sammanfattade i README (se `README.md`). Denna rapport fokuserar på lösningens tekniska utformning, drift och verifiering.

## 2. Arkitekturöversikt
Applikationen är uppdelad i tre mikrotjänster:

- **Battle API (Go + Gin + GORM)**
  - Ansvarar för spelrundor och statistik
  - Lagrar spelomgångar i MySQL
  - Exponerar endpointar för health, rundor och statistik

- **Analytics API (Python + Flask-RESTX + SQLAlchemy)**
  - Hämtar statistik från Battle API och sparar snapshots
  - Exponerar full CRUD för snapshots
  - Dokumenteras med surfbar Swagger på `/docs`
  - Lagrar data i SQLite som separat analysdatabas

- **Frontend (Python + Flask + Jinja2)**
  - Visar spelomgång, resultat och statistik
  - Anropar Battle API för att spela rundor
  - Anropar Analytics API för sammanställning

I Kubernetes körs dessa som separata Deployments/Services med tillhörande konfiguration i manifests under respektive tjänsts `k8s`-katalog.

### 2.1 Tjänstkommunikation och resiliens
Tjänsterna kommunicerar via synkrona HTTP-anrop:
- Frontend anropar Battle API för att spela en rund
- Frontend anropar Analytics API för statistik
- Analytics API anropar i sin tur Battle API för att hämta aktuell spelstatistik

Lösningen implementerar graceful degradation för redundans:
- Battle API fungerar utan databasanslutning (rundor sparas inte men stridsrundan spelas)
- Frontend hanterar timeouts mot Analytics API med ett fallback-värde
- Tjänsterna lokaliseras via miljövariabler (BATTLE_API_URL, ANALYTICS_API_URL) vilket gör systemen portabla mellan lokal Docker Compose och Kubernetes

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

### 4.2 AWS EKS för molnklustring
Lösningen är framtagen för deployment på AWS EKS (Elastic Kubernetes Service). En separat overlay finns i `k8s-aws/` med anpassningar för molnmiljön (StorageClass: `gp2`, frontend Service: `LoadBalancer`). Detta höll lokal setup och cloud setup tydligt separerade.

### 4.3 Datapersistens och backup
- MySQL och SQLite använder persistent storage i Kubernetes
- Automatiska backups till AWS S3 (Simple Storage Service) sker via schemalagda CronJobs — både MySQL-dump och SQLite-fil lagras i objektlagring
- S3-autentiseringsuppgifter hålls utanför versionshantering via template + gitignore (se README)

## 5. Teststrategi och kvalitet
Projektet använder en testpyramid:
- **Unit tests** för Go och Python-tjänster
- **Integrationstester** för samspel mellan tjänster
- **API-tester** med Postman/Newman
- **E2E-tester** med Playwright (desktop + mobil layout)

Resultatet är att både intern logik och verkliga användarflöden verifieras.

## 6. Dokumentation och reproducerbarhet
README fungerar som operativ manual och innehåller:
- Arkitektursammanfattning
- Steg-för-steg för lokal körning (Docker Compose och Kubernetes)
- API-översikt
- Testöversikt
- CI/CD-beskrivning

Se `README.md` för exakta kommandon, portar, endpointar och felsökningsnära information.

## 7. Skärmdumpsbilagor
Skärmdumpar som illustrerar deployed Kubernetes cluster och pods lämnas separat vid sidan om repo och rapport.

## 8. Slutsats
Projektet levererar en komplett cloud native-lösning med separerade tjänster, databaspersistens, testautomatisering och reproducerbar drift i både lokal miljö och Kubernetes.

Sammantaget dokumenteras lösningen på ett sätt som gör den möjlig att granska, köra och verifiera med stöd av instruktionerna i README samt de separata skärmdumpsbilagorna i inlämningen.
