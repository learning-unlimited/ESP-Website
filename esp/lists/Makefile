
do-admin : listadmin.ini
	listadmin -f listadmin.ini

esp-lists.txt : 
	ssh esp.mit.edu /bin/ls -1 /var/lib/mailman/lists/ > esp-lists.txt

listadmin.ini : listadmin.ini.base esp-lists.txt Makefile
	cat listadmin.ini.base > listadmin.ini
	cat listadmin.ini.local >> listadmin.ini
	cat esp-lists.txt | sed -e 's#$$#@esp.mit.edu#' >> listadmin.ini
	chmod og-rwx listadmin.ini
