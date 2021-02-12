# Makefile for use in deploying stable releases to sites.
# To use this, cd to the chapter site, then run `make -f path/to/this/file`.
# If the chapter has a custom branch, or local changes that can't be rebased,
# the script will exit, and you'll need to fix it up then run "make finish".
# TODO(benkraft): at some point maybe we'll want a proper automation framework
# like puppet or chef or whatever.
SHELL=/bin/bash
SITE:=$(notdir $(PWD))
STASH:=$(shell sudo -u www-data git diff HEAD --quiet || echo true)

sr-12: NEWBRANCH=stable-release-12
sr-12: OLDBRANCH=stable-release-11
sr-12: pre src finish

pre:
	@echo "Backing things up and fixing permissions."
	@# get credentials, if we lack them, before we try to do anything fancy with pipes
	sudo -v
	@# We might not have write permissions on the homedir, but www-data should.
	set -o pipefail; sudo -u postgres pg_dump $(SITE)_django | gzip | sudo -u www-data tee $(SITE)_$(shell date +"%Y%m%d").sql.gz >/dev/null
	-sudo chown -RL "www-data:www-data" .

src:
	@echo "Attempting to do the git stuff automatically; if this fails for any reason, fix it up and run 'make finish'."
	[ "$$(git rev-parse --abbrev-ref HEAD)" = "$(OLDBRANCH)" ]  # Assert we're on OLDBRANCH
	if [ "$(STASH)" = "true" ] ; then sudo -u www-data git stash ; fi
	sudo -u www-data git fetch origin
	sudo -u www-data git remote prune origin
	sudo -u www-data git checkout origin/$(NEWBRANCH)
	if [ "$(STASH)" = "true" ] ; then sudo -u www-data git stash pop ; fi

finish:
	@echo "Updating the site; if this fails for any reason, fix it up and (re-)run 'make finish'."
	esp/update_deps.sh
	sudo -u www-data esp/manage.py update
	@echo "Done! Go test some things."

.PHONY: pre src finish
