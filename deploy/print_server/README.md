# Print server

The website sends day-of print jobs for network printers (Printers page) to a
separate print server running CUPS, so the web server itself needs no CUPS.
`esp-print-server` is a small HTTPS API (Python standard library only) in
front of the print server's CUPS: the website (`esp/esp/utils/print_server.py`)
asks it, with a bearer token, what a printer is and supports (IPP
Get-Printer-Attributes, for the Printers page's "Check printer" and settings),
to create or delete a location's queue, and to print PDFs. CUPS converts each
PDF into whatever the printer accepts (driverless queues,
`lpadmin -m everywhere`). The API is described at the top of the script.

Only the print server talks to printers (IPP on port 631, or raw/LPD on 9100/515
for printers without IPP); the web server (and
its print worker) only needs to reach the print server's API port (8631).
Firewall 8631 so only the web server (and dev machines, if any) can reach it:
everything else is refused by the token anyway, but there's no reason to let
the rest of the network open connections to it.

## Setting up a print server (Debian/Ubuntu)

    sudo apt install cups cups-filters certbot
    sudo useradd --system --no-create-home --shell /usr/sbin/nologin --groups lpadmin espprint
    sudo install -m 755 esp-print-server /usr/local/bin/esp-print-server
    sudo install -m 755 esp-pjl-backend /usr/lib/cups/backend/esppjl
    sudo install -m 755 esp-print-cert-deploy /usr/local/sbin/esp-print-cert-deploy
    sudo install -d -m 750 -o root -g espprint /etc/esp-print
    python3 -c 'import secrets; print(secrets.token_urlsafe(32))' | sudo install -m 640 -o root -g espprint /dev/stdin /etc/esp-print/token
    sudo install -m 644 esp-print-server.service /etc/systemd/system/

Get a TLS certificate with certbot, with `esp-print-cert-deploy` as the deploy
hook: it copies each new certificate to `/etc/esp-print/` for the service and
restarts it. For a name Let's Encrypt can reach over HTTP:

    sudo certbot certonly --standalone -d esp-print.mit.edu --deploy-hook /usr/local/sbin/esp-print-cert-deploy

(For a name that only resolves to a private address, use certbot's DNS
challenge instead, with whatever DNS hooks that domain has.) Then:

    sudo systemctl enable --now esp-print-server

## Printers that aren't driverless

"Check printer" picks the driver. Printers with IPP 2.0 that take PDF or
raster get driverless queues. Others get the model's own driver when one is
installed here (it knows the model from SNMP), else CUPS's generic
PostScript or PCL driver. Installed drivers so far:

- **Older HP printers with IPP 1.1** (e.g. Color LaserJet CP4525): HP's
  PostScript PPDs, so color and duplex are offered:

      sudo apt install printer-driver-postscript-hp

- **Canon printers with no IPP at all**, which only speak UFR II LT (e.g.
  LBP6230dw; `CID:CA_UFRIILT` in its SNMP device ID). The print server then
  prints raw to port 9100 (else LPD, 515) with Canon's driver: "UFRII LT
  Printer Driver for Linux" V5.00, `linux-UFRIILT-drv-v500-uken-18.tar.gz`
  from `https://gdlp01.c-wss.com/gds/0/0100005950/10/` (sha512 starts
  `e7b964f3d4541e1e`; the UFR II V6 driver doesn't cover these models).
  Install its `64-bit_Driver/Debian/cnrdrvcups-ufr2lt-uk_5.00-1_amd64.deb`,
  plus the library it needs but doesn't declare, then undo the setuid status
  tool and world-writable directories its install script makes (none are
  needed for printing):

      sudo apt install ./cnrdrvcups-ufr2lt-uk_5.00-1_amd64.deb libcupsimage2t64
      sudo dpkg-statoverride --update --add root root 0755 /usr/lib/Canon/CUPS_SFPR/Utilities/pksmncapr
      sudo chown root:lp /var/cache/Canon /var/cache/Canon/CUPS_SFPR
      sudo chmod 775 /var/cache/Canon /var/cache/Canon/CUPS_SFPR
      sudo chmod 755 /etc/cngplp2l/account /etc/cngplp2l/options

  Check with `ldd /usr/lib/cups/filter/rastertosfp` (nothing "not found"):
  a missing library shows only as the job stopping, with the filter's status
  127 in `/var/log/cups/error_log`.

## How PDFs reach older printers

A printer that isn't driverless (it gets its model's own driver, or a generic
PostScript or PCL one) is printed to raw on port 9100 when that's open
(`socket://<printer>:9100`), not over IPP: such a printer's IPP server takes a
whole job in one HTTP request and can drop a large one partway, which makes
CUPS stop the queue (an HP CP4525 dropped a 70 MB job twice over IPP; over
9100 it printed in 40 s). Its IPP is still used to ask what it supports.

A queue with the model's own driver or a generic PostScript one gets
`pdftops-renderer-default=pdftocairo`: CUPS turns PDFs into PostScript with
Cairo rather than Ghostscript, whose output for PDFs with images or
transparency is enormous (a 1.1 MB Google Slides map became 70 MB per job,
which an HP CP4525 dropped partway through over IPP; Cairo made 2 MB). On a
sample of real jobs (schedules, receipts, deposit slips, and PDFs from Word,
Canva, Firefox and Google) Cairo's output was 2-35x smaller and rendered the
same. Copies are never repeated in the data: the filters ask the printer for
them (`NumCopies` in the PostScript or the raster header).

## Knowing a job printed (PJL printers)

Over port 9100 CUPS's own backend (`socket://`) only hands the job over, so
CUPS calls a job completed as soon as the printer has the data, even when the
printer is out of paper and the job sits in its memory (and prints whenever
someone loads paper, even after it was printed elsewhere). So a printer whose
SNMP device ID lists PJL (`CMD:PJL,...`: HP, Brother, most lasers) gets this
server's own backend instead, `esppjl://<printer>:9100` (`esp-pjl-backend`,
installed as `/usr/lib/cups/backend/esppjl`, mode 755 so CUPS runs it as
`lp`, not root). Over the same connection it:

- asks the printer's status first (`@PJL INFO STATUS`) and, while the printer
  is out of paper, jammed or offline, holds the job here, telling CUPS why
  (`STATE: +media-empty-error`, and the printer's display text as the
  queue's message), which the website shows on Printer Setup at once;
- sends the job as a named PJL job (`@PJL JOB NAME=...` / `@PJL EOJ`) with
  job reports on (`@PJL USTATUS JOB=ON`) and the printer's status changes
  (`USTATUS DEVICE=ON`), and exits only when the printer reports
  `USTATUS JOB END`, which it sends once the job's last page is in the
  output bin; so CUPS's "completed" means printed.

Printers without PJL (e.g. Canon's UFR II LT ones) stay on `socket://`. An
existing queue changes only when its location is reconnected on Printer
Setup. To watch a job by hand: `lpstat -l -p <queue>` (the backend's
messages), or CUPS's `error_log`.

To check a printer speaks PJL (this prints nothing):

    python3 -c 'import socket; s = socket.create_connection(("<printer>", 9100), 5); s.sendall(b"\x1b%-12345X@PJL INFO STATUS\r\n\x1b%-12345X"); s.settimeout(5); print(s.recv(4096))'

## Stopped queues

When a printer drops a job partway through (e.g. a color job whose PostScript
is too large for it), CUPS's backend exits with "stop printer", and CUPS then
stops (disables) the whole queue, whatever its `printer-error-policy`: every
job waits until the queue is re-enabled. The website's print worker sees this
(the queue's state is `stopped`), re-enables the queue (`POST
/queues/<queue>/enable`, which runs `cupsenable`), and decides what to do with
the job: see `_queue_stopped` in `esp/esp/program/controllers/printing.py`. By
hand: `sudo cupsenable <queue>`.

## Website settings (`local_settings.py`)

    PRINT_SERVER = {
        'url': 'https://esp-print.mit.edu:8631',
        'token': '<the print server\'s /etc/esp-print/token>',
        # 'ca': '/path/to/cert.pem',     # only to pin a self-signed certificate
    }

Without `PRINT_SERVER`, the Printers page offers laptop printing only.

Check it from the web server:

    curl -H "Authorization: Bearer <token>" https://esp-print.mit.edu:8631/queues/esp-01jd3k8w6p0b2c4d5e6f7g8h9j

(`{"error": "lpstat: Invalid destination name ..."}` until that location has a
printer connected; 401 means a wrong token.)
