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
