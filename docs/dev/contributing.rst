Workflow
========

To set up your dev server, see `<vagrant.rst>`_.  The remainder of this document assumes you've set up a dev server, and are ready to contribute a change.

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
  ./manage.py update # on vagrant: fab refresh
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

Make a pull request for ``urgent-branch-name`` as described above.

A note on rebasing
------------------

In our workflow, there is generally no need to rebase or squash.  If you are working on a pull request, it's fine to rebase or squash your changes to keep the history easy to review, if you know exactly what that means, why you might want to do it, and when it is safe to do so.  (Answering those questions is beyond the scope of this document.)  If you're not sure whether now is a safe time, just skip the rebase/squash: it's very easy to make a mess and GitHub has gotten good enough that it doesn't make things much cleaner for reviewers, either.  A good old ``git merge`` will do just fine.

One exception: when merging a pull request to ``main`` via the GitHub UI button, we generally prefer the "squash" option, unless the individual changes in the pull request are fairly distinct or there is a lot of history to preserve, in which case "merge" is better.  (If GitHub doesn't offer "squash", then "merge" is also best.)  If the pull request is *from* ``main`` or will be merged into multiple branches, definitely use "merge".  If you're not sure, ask a more experienced contributor which to use!
