Workflow
========

Recommended one-time setup
--------------------------

Remove ``--global`` if you don't want it to apply to other git repos on your computer: ::

  git config --global user.name "Your Name"
  git config --global user.email you@something.edu

Other git config you might find useful: ::

  git config --global push.default simple # makes git only push the current branch, which is useful for not accidentally messing things up
  git config --global color.{ui,status,branch,diff,interactive,grep} auto # makes various interfaces usefully colorful
  git config --global log.decorate true # shows branch information in `git log` by default
  git config --global core.pager "less -R"
  git config --global pager.{status,branch,diff,show,log} true
  git config --global color.pager true
  git config --global core.editor vim # or emacs, nano, your favorite text editor, etc.
  git config --global grep.lineNumber true

For normal, non-urgent features and bug fixes
---------------------------------------------

The following workflow applies if you've already been added as a collaborator to the repository.  If not, you should fork it using the button on Github, add it as a remote, and replace all of the ``git push``/``git push origin`` steps with ``git push remote-name``.

From the directory ``/esp``: ::

  git checkout main
  git pull
  ./update_deps.sh # on vagrant: see vagrant docs; no need to bother if deps haven’t changed
  ./manage.py update # on vagrant: fab manage:cmd=update
  git checkout -b new-branch-name

Write some code!
Test your code!

Look at what you’ve changed (``git status`` and/or ``git diff``), and then run ``git commit -a``, and type a commit message (see `<http://tbaggery.com/2008/04/19/a-note-about-git-commit-messages.html>` for good commit message style).  Repeat a few times from “write some code!” if you want to make multiple commits.

When you’re ready to make a pull request, or want other people to be able to pull your code: ::

  git push --set-upstream origin new-branch-name

Now go to `<https://github.com/learning-unlimited/ESP-Website>`_. If you’re logged in, you should see a banner near the top suggesting that you make a pull request. Click the button, write up a summary of your pull request, and submit it.

Now wait for someone to review your pull request. If it takes a long time, poke a friend to review it.

When someone reviews your pull request, they will probably have some comments. If they have a lot to say, or suggest some major changes, don’t feel bad! This is a normal part of the code review process. Now you need to address their comments. If you disagree with what they’ve said, or want to discuss more, feel free to do that on the pull request. To change your code: ::

  git checkout new-branch-name # only if you’d switched to another branch while waiting
  Make some changes
  Test your changes
  git commit -a -m "Fixed foo, bar, and baz"
  git push

The reviewer will look at your changes. In some cases, you might go through a few more cycles of this. Once everything is resolved, they’ll merge your pull request. Congratulations!

For urgent features and fixes
-----------------------------

The following is MIT-specific, although by using a different prod branch a similar thing might work for other sites. ::

  git pull
  git checkout $(git merge-base main mit-prod)
  git checkout -b urgent-branch-name

Write some code!
Test your code! Be careful, since you’re putting this on our live server without full review. ::

  git commit -a -m "Did something important"
  git push --set-upstream origin urgent-branch-name

  git checkout mit-prod
  git merge urgent-branch-name
  git push

Pull code as described in `<https://esp.mit.edu/wiki/index.php/The_Server#Pulling_New_Code>`_.

Make a pull request for ``urgent-branch-name`` as described above
