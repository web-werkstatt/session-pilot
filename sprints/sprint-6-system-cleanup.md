# Sprint 6: System Cleanup & Hardening

**Datum:** 2026-03-28
**Ziel:** Versteckte Systemprobleme beseitigen - DB-Bloat, Docker-Muell, offene Ports, tote Services

## Kontext

Bei der Analyse des Systems wurden mehrere versteckte Probleme gefunden, die Performance,
Speicher und Sicherheit betreffen. Die Session-Sync-Optimierung (Hash-Cache) wurde bereits
in Sprint 5.1 umgesetzt.

---

## Task 1: messages-Tabelle optimieren (11 GB)

**Prioritaet:** Hoch
**Problem:** Die `messages`-Tabelle belegt 11 GB in PostgreSQL. Die gesamte DB ist 11 GB -
fast alles steckt in dieser einen Tabelle. Vermutlich werden volle `content_json`-Blobs
mit Tool-Outputs, Screenshots und Base64-Daten gespeichert.

**Massnahmen:**
- [ ] Analysieren was den Platz frisst (content_json Durchschnittsgroesse, groesste Eintraege)
- [ ] Tool-Result-Content kuerzen (Bash-Output, Screenshots etc. auf sinnvolle Laenge)
- [ ] VACUUM FULL nach Bereinigung
- [ ] Pruefen ob Index auf messages sinnvoll ist

**Erwartetes Ergebnis:** DB-Groesse auf < 2 GB reduzieren

---

## Task 2: Docker aufraeumen (~211 GB rueckgewinnbar)

**Prioritaet:** Hoch
**Problem:** 182 GB Images (92 GB ungenutzt), 208 GB Build Cache (119 GB rueckgewinnbar),
131 Container (nur 9 aktiv), 153 Volumes (73 aktiv). Platte zu 60% voll.

**Massnahmen:**
- [ ] Gestoppte Container entfernen (`docker container prune`)
- [ ] Ungenutzte Images entfernen (`docker image prune -a` mit Filter)
- [ ] Build Cache bereinigen (`docker builder prune`)
- [ ] Verwaiste Volumes pruefen und entfernen
- [ ] Disk-Usage vorher/nachher dokumentieren

**Erwartetes Ergebnis:** ~150-200 GB Plattenplatz zurueckgewinnen

---

## Task 3: Offene Ports absichern

**Prioritaet:** Mittel (Sicherheit)
**Problem:** Folgende Ports sind auf 0.0.0.0 offen (nicht nur localhost):
- PostgreSQL (5432) - Datenbank direkt erreichbar
- Portainer (9000/9443) - Container-Management
- Ghost (2368) - Blog-Engine
- Webmin (10000) - Server-Admin-Panel
- FTP (21) - Unsicheres Protokoll
- Samba (139/445) - Windows-Freigaben
- xrdp (3389) - Remote Desktop

**Massnahmen:**
- [ ] Pruefen ob ufw/iptables aktiv ist
- [ ] Firewall aktivieren: nur SSH (22), HTTP/HTTPS, Dashboard (5055) von aussen
- [ ] Alle anderen Ports auf localhost oder Tailscale-Netz beschraenken
- [ ] Docker-Ports via `127.0.0.1:PORT:PORT` binden wo moeglich

**Erwartetes Ergebnis:** Nur notwendige Ports von aussen erreichbar

---

## Task 4: docker-mec-autostart.service fixen

**Prioritaet:** Niedrig
**Problem:** Service schlaegt bei jedem Boot fehl. Erzeugt Fehlermeldungen im Journal.

**Massnahmen:**
- [ ] Service-Datei pruefen
- [ ] Entweder reparieren oder deaktivieren
- [ ] Journal-Eintraege bestaetigen dass der Fehler weg ist

---

## Task 5: Unnoeetige Dienste deaktivieren

**Prioritaet:** Niedrig
**Problem:** Mehrere Dienste laufen dauerhaft ohne aktive Nutzung:

| Dienst | RAM | Zweck | Empfehlung |
|---|---|---|---|
| xrdp | minimal | Remote Desktop (doppelt mit NoMachine) | Deaktivieren |
| vsftpd | minimal | FTP-Server | Deaktivieren (unsicher, veraltet) |
| php8.4-fpm | ~70 MB | PHP-Anwendungen | Pruefen ob genutzt |
| samba (smbd/nmbd) | ~70 MB | Windows-Freigaben | Pruefen ob genutzt |
| webmin | ~32 MB | Web-Admin | Pruefen ob genutzt |
| snapd | ~43 MB | Snap-Packages | Pruefen ob genutzt |

**Massnahmen:**
- [ ] Jeden Dienst einzeln mit User abklaeren
- [ ] Ungenutzte deaktivieren (`systemctl disable --now`)
- [ ] RAM-Ersparnis dokumentieren

**Erwartetes Ergebnis:** ~200 MB RAM-Ersparnis, weniger Angriffsflaeche

---

## Bereits erledigt

### Sprint 5.1 - Performance & Sync
- [x] 20 Docker Container gestoppt (irtours, seo-suite, expense-manager, steuerrecht, etc.)
- [x] Ollama deaktiviert
- [x] PCP (Performance Co-Pilot) deaktiviert
- [x] Session-Sync Timer deaktiviert
- [x] Hash-basierter Sync-Cache implementiert (485s -> 0.83s)
- [x] Auto-Sync bei Sessions-Seitenaufruf mit 1h Cooldown
- [x] JSONL-Import Escape-Fehler behoben (\u0000, \x00)

### Sprint 6 - System Cleanup
- [x] messages-Tabelle: 11 GB -> 713 MB (4.4 Mio Duplikate entfernt, Bug gefixt)
- [x] Docker aufgeraeumt: ~300 GB freigegeben (Images, Build Cache, Volumes, Container)
- [x] docker-mec-autostart.service deaktiviert (kaputtes Netzwerk)
- [x] Message-Duplikat-Bug gefixt (DELETE vor INSERT)
- [x] NoneType-Absicherung bei Session-INSERT

### Sprint 6.1 - Code Cleanup
- [x] Verwaiste Dateien entfernt: context_tracker.py, dashboard.js, session-reviews.css, sessions-list.css
- [x] Ungenutzte Funktionen entfernt: get_git_status(), get_tool_for_model()
- [x] Python-Duplikate: WHERE-Builder (_build_timesheet_filter), Search-Parser (_parse_search_output)
- [x] JS-Duplikate: formatTokens/formatDate/formatDateTime nach base.js konsolidiert
- [x] CSS-Duplikate: .empty-state nur noch in components.css
- [x] session_import_utils.py: Shared Helpers (parse_ts, sanitize_content_json) extrahiert
- [x] scheduled_tasks.js: formatDate -> formatTimeAgo (korrekte Semantik)
- [x] CLAUDE.md aktualisiert mit neuen Patterns und Services

### Offen
- [x] Modal-Handling vereinheitlichen (generische openModal/closeModal in base.js)
- [ ] Fetch-Wrapper einfuehren (globale fetchJson() Funktion)
