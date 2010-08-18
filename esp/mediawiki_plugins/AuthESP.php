<?php
# Copyright (C) 2009 Adam Seering <aseering@mit.edu>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
# http://www.gnu.org/copyleft/gpl.html

require_once( 'AuthPlugin.php' );
 
class AuthESP extends AuthPlugin {
 
  function userExists( $username )
  {
    $descriptorspec = array(
      0 => array("pipe", "r"),  // stdin is a pipe that the child will read from
      1 => array("pipe", "w"),  // stdout is a pipe that the child will write to
      2 => array("file", "/dev/null", "w") // Not currently handling stderr
    );

    $process = proc_open("/esp/web/esp/esp/cmdline_auth.py", $descriptorspec, $pipes);

    fwrite($pipes[0], "USER_EXISTS\n${username}\n");
    fclose($pipes[0]);
    $return_value = stream_get_contents($pipes[1]);
    fclose($pipes[1]);

    proc_close($process);

#    $fh = fopen("/tmp/testfile.txt", "w");
#    fwrite($fh, $return_value);
#    fwrite($fh, ($return_value == "true"));

    return ($return_value == "true");
  }
 
  function authenticate($username, $password)
  {
    $descriptorspec = array(
      0 => array("pipe", "r"),  // stdin is a pipe that the child will read from
      1 => array("pipe", "w"),  // stdout is a pipe that the child will write to
      2 => array("file", "/dev/null", "w") // Not currently handling stderr
    );

    $process = proc_open("/esp/web/esp/esp/cmdline_auth.py", $descriptorspec, $pipes);

    fwrite($pipes[0], "AUTHENTICATE\n${username}\n${password}");
    fclose($pipes[0]);
    $return_value = stream_get_contents($pipes[1]);
    fclose($pipes[1]);

    proc_close($process);

    $fh = fopen("/tmp/testfile.txt", "w");
    fwrite($fh, $return_value);
    fwrite($fh, ($return_value == "true"));

    return ($return_value == "true");
  }
 
  function autoCreate() {
     return true;
  }
 
}
