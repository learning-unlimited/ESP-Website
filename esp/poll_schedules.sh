#!/bin/bash

PROGRAM="Splash"
INSTANCE="2010"

echo "What printer do you want to print to? (lpr printer name)"
read PRINTERNAME

echo "Please enter the onsite username and password for the ESP website:"
echo -n "Username: "
read USERNAME

echo -n "Password: "
read -s PASSWORD
echo

CURL_COOKIE_STORE="curl_cookies.txt"

echo "Logging in..."
curl -c "${CURL_COOKIE_STORE}" "https://esp.mit.edu/admin/" >/dev/null 2>&1
curl -b "${CURL_COOKIE_STORE}" -c "${CURL_COOKIE_STORE}" -d "username=${USERNAME}&password=${PASSWORD}&this_is_the_login_form=1" "https://esp.mit.edu/admin/" >/dev/null 2>&1
echo "Logged in!"

while (true); do
	TMPFILE="`mktemp -t esp_print_tmp`"	
	curl -b "${CURL_COOKIE_STORE}" "https://esp.mit.edu/onsite/${PROGRAM}/${INSTANCE}/printschedules?gen_img&img_format=ps" -o "${TMPFILE}" 2>/dev/null

	if [ -n "`cat "${TMPFILE}"`" ]; then
		lpr -P "${PRINTERNAME}" < "${TMPFILE}"
		echo -n "Printed! "
		date
		rm "${TMPFILE}"
	else
		echo -n "."
		rm "${TMPFILE}"
		sleep 10s
	fi
done

