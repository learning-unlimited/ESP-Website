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

Only the print server talks to printers (IPP, port 631); the web server (and
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

## Website settings (`local_settings.py`)

    PRINT_SERVER = {
        'url': 'https://esp-print.mit.edu:8631',
        'token': '<the print server\'s /etc/esp-print/token>',
        # 'ca': '/path/to/cert.pem',     # only to pin a self-signed certificate
    }

Without `PRINT_SERVER`, the Printers page offers laptop printing only.

Check it from the web server:

    curl -H "Authorization: Bearer <token>" https://esp-print.mit.edu:8631/queues/esp-location-1

(`{"error": "lpstat: Invalid destination name ..."}` until that location has a
printer connected; 401 means a wrong token.)
