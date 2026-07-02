#!/usr/bin/env bash
#
# harden-ollama.sh
# Mette in sicurezza Ollama su un host AlmaLinux: resta raggiungibile dai
# container Docker (rete privata) ma NON dall'esterno (internet).
# Idempotente: puoi rilanciarlo piu' volte senza danni.

# 'set -e' interrompe lo script al primo comando che fallisce.
# 'set -u' fa fallire se usi una variabile non definita (evita errori silenziosi).
# 'set -o pipefail' propaga l'errore anche dentro le pipe (cmd1 | cmd2).
set -euo pipefail

# --- Parametri configurabili -------------------------------------------------

# Porta su cui ascolta Ollama (default 11434).
OLLAMA_PORT="${OLLAMA_PORT:-11434}"

# Porta dell'API FillForm da aprire verso l'esterno; lascia vuoto per non aprirla.
API_PORT="${API_PORT:-8000}"

# Range IP privato usato dalle reti bridge di Docker (172.17.x - 172.31.x).
DOCKER_SUBNET="172.16.0.0/12"

# --- Controlli preliminari ---------------------------------------------------

# 'id -u' restituisce l'UID dell'utente corrente; 0 = root. Senza root non
# possiamo installare pacchetti ne' modificare il firewall: usciamo con errore.
if [[ "$(id -u)" -ne 0 ]]; then
  echo "Errore: esegui questo script come root (sudo)." >&2
  exit 1
fi

# Rileva la porta SSH ATTIVA leggendo i socket in ascolto del processo sshd,
# cosi' apriamo quella giusta anche se non e' la 22 standard, evitando di
# chiuderci fuori dalla sessione SSH. Se non la troviamo, ripieghiamo su 22.
SSH_PORT="$(ss -lntp 2>/dev/null | awk '/sshd/ {split($4,a,":"); print a[length(a)]; exit}')"
SSH_PORT="${SSH_PORT:-22}"
echo ">> Porta SSH rilevata: ${SSH_PORT}"

# --- 1. Ollama in ascolto su tutte le interfacce -----------------------------
# Serve perche' i container lo raggiungono via host.docker.internal (gateway
# del bridge), non via 127.0.0.1. Il firewall, piu' sotto, blocca l'esterno.

# Crea la cartella del drop-in systemd per il servizio ollama (se manca).
# '-p' non da' errore se la cartella esiste gia'.
mkdir -p /etc/systemd/system/ollama.service.d

# Scrive il drop-in che imposta OLLAMA_HOST. Il blocco 'cat <<EOF > file'
# (here-doc) riversa nel file tutto cio' che sta tra EOF e EOF.
cat <<EOF > /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_HOST=0.0.0.0:${OLLAMA_PORT}"
EOF
echo ">> Drop-in systemd scritto (OLLAMA_HOST=0.0.0.0:${OLLAMA_PORT})"

# Ricarica le unit di systemd per fargli leggere il nuovo drop-in...
systemctl daemon-reload
# ...e riavvia Ollama applicando il nuovo bind.
systemctl restart ollama
echo ">> Ollama riavviato"

# --- 2. Firewall: installa e avvia firewalld ---------------------------------

# 'command -v firewall-cmd' restituisce successo se il comando esiste. Il '!'
# nega: se NON esiste, lo installiamo con dnf ('-y' = conferma automatica).
if ! command -v firewall-cmd >/dev/null 2>&1; then
  echo ">> firewalld non presente: installazione..."
  dnf install -y firewalld
fi

# Abilita firewalld all'avvio ('enable') e lo fa partire subito ('--now').
systemctl enable --now firewalld
echo ">> firewalld attivo"

# --- 3. Regole firewall ------------------------------------------------------
# Usiamo '--permanent' per scrivere la config su disco (sopravvive ai reboot);
# le regole diventano attive dopo il '--reload' finale.

# Garantisce l'accesso SSH sulla zona pubblica PRIMA di tutto, per non perdere
# la sessione corrente. Apriamo la porta SSH effettiva rilevata sopra.
firewall-cmd --permanent --zone=public --add-port="${SSH_PORT}/tcp"
echo ">> SSH (${SSH_PORT}/tcp) consentito su zona public"

# Mette le subnet Docker nella zona 'trusted' (che permette tutto): cosi' i
# container possono raggiungere qualunque porta dell'host, inclusa Ollama.
firewall-cmd --permanent --zone=trusted --add-source="${DOCKER_SUBNET}"
echo ">> Subnet Docker ${DOCKER_SUBNET} marcata come trusted"

# Blocca esplicitamente la porta di Ollama sulla zona pubblica (internet):
# il traffico dai container passa dalla zona trusted, quindi non e' toccato.
firewall-cmd --permanent --zone=public \
  --add-rich-rule="rule port port=\"${OLLAMA_PORT}\" protocol=\"tcp\" drop"
echo ">> Porta Ollama ${OLLAMA_PORT}/tcp bloccata dall'esterno"

# Se API_PORT non e' vuoto, apre la porta dell'API verso l'esterno.
# '-n' e' vero quando la stringa NON e' vuota.
if [[ -n "${API_PORT}" ]]; then
  firewall-cmd --permanent --zone=public --add-port="${API_PORT}/tcp"
  echo ">> API (${API_PORT}/tcp) aperta su zona public"
fi

# Applica tutte le regole permanenti alla configurazione runtime.
firewall-cmd --reload
echo ">> Regole firewall applicate"

# --- 4. Riepilogo e verifica -------------------------------------------------

echo ""
echo "=== Stato firewall (zona public) ==="
firewall-cmd --zone=public --list-all

echo ""
echo "=== Socket in ascolto sulla porta Ollama ==="
# Mostra su quali IP ascolta Ollama (atteso: 0.0.0.0:${OLLAMA_PORT}).
ss -lntp | grep ":${OLLAMA_PORT}" || echo "Nessun listener su ${OLLAMA_PORT} (Ollama e' partito?)"

echo ""
echo "Fatto. Ollama e' raggiungibile dai container ma non da internet."
echo "Verifica dall'esterno (da un'altra macchina) che vada in timeout:"
echo "  nc -vz <IP_PUBBLICO> ${OLLAMA_PORT}"
