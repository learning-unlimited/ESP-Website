#!/bin/bash

if [ -z "$1" ]; then
    echo "Usage: $0 <program_name> [instance]"
    echo "Example: $0 Spark 2015"
    exit 1
fi

PROGRAM="$1"
INSTANCE="${2:-2015}"

echo "What printer do you want to print to? (lpr printer name)"
read PRINTERNAME

echo "Where are you? (ESP website printer name)"
read LOCATION

echo "Please enter the onsite username and password for the ESP website:"
echo -n "Username: "
read USERNAME

echo -n "Password: "
read -s PASSWORD
echo

CURL_COOKIE_STORE="curl_cookies.txt"
BASE_URL="https://esp.mit.edu"

echo "Logging in..."
# Fetch the login page HTML and save the CSRF cookie; extract the masked
# csrfmiddlewaretoken from the rendered form (NOT the raw cookie value,
# which is a different format and would cause Django to return 400).
LOGIN_PAGE=$(curl -s -L -c "${CURL_COOKIE_STORE}" "${BASE_URL}/admin/login/")
CSRF_TOKEN=$(echo "${LOGIN_PAGE}" | grep -o 'name="csrfmiddlewaretoken" value="[^"]*"' | grep -o 'value="[^"]*"' | cut -d'"' -f2)
LOGIN_CODE=$(curl -s -b "${CURL_COOKIE_STORE}" -c "${CURL_COOKIE_STORE}" \
    -d "username=${USERNAME}&password=${PASSWORD}&csrfmiddlewaretoken=${CSRF_TOKEN}&next=/admin/" \
    -H "Referer: ${BASE_URL}/admin/login/" \
    -w "%{http_code}" -o /dev/null \
    "${BASE_URL}/admin/login/")
if [ "${LOGIN_CODE}" = "302" ]; then
    echo "Logged in successfully."
else
    echo "Login failed. Please check credentials."
    exit 1
fi

while (true); do
  TMPFILE="`mktemp`"
  curl -b "${CURL_COOKIE_STORE}" "${BASE_URL}/onsite/${PROGRAM}/${INSTANCE}/printschedules/${LOCATION}?gen_img&img_format=pdf" -o "${TMPFILE}" 2>/dev/null

  if [ -n "`cat "${TMPFILE}"`" ]; then
    lpr -P "${PRINTERNAME}" < "${TMPFILE}"
    echo -n "Printed! "
    date
    rm "${TMPFILE}"
  else
    echo -n "."
    rm "${TMPFILE}"
    sleep 2s 
  fi  
done


