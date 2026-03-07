#!/bin/bash

PROGRAM="Spark"
INSTANCE="2015"

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

echo "Logging in..."
curl -L -c "${CURL_COOKIE_STORE}" "https://esp.mit.edu/admin/login/" >/dev/null 2>&1
CSRF_TOKEN=$(grep csrftoken "${CURL_COOKIE_STORE}" | awk '{print $NF}')
LOGIN_RESULT=$(curl -b "${CURL_COOKIE_STORE}" -c "${CURL_COOKIE_STORE}" \
    -d "username=${USERNAME}&password=${PASSWORD}&csrfmiddlewaretoken=${CSRF_TOKEN}&next=/admin/" \
    -w "%{http_code}|%{redirect_url}" -o /dev/null \
    "https://esp.mit.edu/admin/login/")
LOGIN_CODE=$(echo "${LOGIN_RESULT}" | cut -d'|' -f1)
LOGIN_REDIRECT=$(echo "${LOGIN_RESULT}" | cut -d'|' -f2)
if [ "${LOGIN_CODE}" = "302" ] && ! echo "${LOGIN_REDIRECT}" | grep -q "login"; then
    echo "Logged in successfully."
else
    echo "Login failed. Please check credentials."
    exit 1
fi

while (true); do
  TMPFILE="`mktemp`"
  curl -b "${CURL_COOKIE_STORE}" "https://esp.mit.edu/onsite/${PROGRAM}/${INSTANCE}/printschedules/${LOCATION}?gen_img&img_format=pdf" -o "${TMPFILE}" 2>/dev/null

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


