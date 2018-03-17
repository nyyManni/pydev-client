;; Copyright (C) 2010-2017 Free Software Foundation, Inc

;; Author: Rocky Bernstein <rocky@gnu.org>

;; This program is free software; you can redistribute it and/or modify
;; it under the terms of the GNU General Public License as published by
;; the Free Software Foundation, either version 3 of the License, or
;; (at your option) any later version.

;; This program is distributed in the hope that it will be useful,
;; but WITHOUT ANY WARRANTY; without even the implied warranty of
;; MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
;; GNU General Public License for more details.

;; You should have received a copy of the GNU General Public License
;; along with this program.  If not, see <http://www.gnu.org/licenses/>.

;; pydev: Python 3.2 and beyond

(eval-when-compile (require 'cl-lib))   ;For setf.

(require 'load-relative)
(require-relative-list '("../../common/regexp"
			 "../../common/loc"
			 "../../common/init")
		       "realgud-")
(require-relative-list '("../../lang/python") "realgud-lang-")

(defvar realgud-pat-hash)
(declare-function make-realgud-loc-pat (realgud-loc))

(defvar realgud:pydev-pat-hash (make-hash-table :test 'equal)
  "Hash key is the what kind of pattern we want to match:
backtrace, prompt, etc.  The values of a hash entry is a
realgud-loc-pat struct")

(declare-function make-realgud-loc 'realgud-loc)

;; realgud-loc-pat that describes a pydev location generally shown
;; before a command prompt.
;;
;; For example:
;;   (/usr/bin/zonetab2pot.py:15): <module>
;;   (/usr/bin/zonetab2pot.py:15 remapped <string>): <module>
;; or MS Windows:
;;   (c:\\mydirectory\\gcd.py:10): <module>
(setf (gethash "loc" realgud:pydev-pat-hash)
      realgud:python-trepan-loc-pat)

;; Regular expression that describes a pydev prompt.
;; Note: the prompt in nested debugging
;; For example:
(setf (gethash "prompt" realgud:pydev-pat-hash)
      (make-realgud-loc-pat
       :regexp   "^(pydevc) "
       ))


;; realgud-loc-pat that describes a pydev backtrace line.
;; For example:
;; ->0 get_distribution(dist='trepan==0.3.9')
;;     called from file '/python2.7/dist-packages/pkg_res.py' at line 341
;; ##1 load_entry_point(dist='tr=0.3.9', group='console_scripts', name='tr')
;;     called from file '/python2.7/dist-packages/pkg_res.py' at line 351
;; ##2 <module> exec()

(setf (gethash "debugger-backtrace" realgud:pydev-pat-hash)
      realgud:python-trepan-backtrace-pat)

;;  realgud-loc-pat that describes a Python backtrace line.
(setf (gethash "lang-backtrace" realgud:pydev-pat-hash)
      realgud-python-backtrace-loc-pat)

;;  realgud-loc-pat that describes location in a pytest error
(setf (gethash "pytest-error" realgud:pydev-pat-hash)
      realgud-pytest-error-loc-pat)

;;  Regular expression that describes location in a flake8 message
(setf (gethash "flake8-msg" realgud:pydev-pat-hash)
      realgud-flake8-msg-loc-pat)

;;  realgud-loc-pat that describes a "breakpoint set" line
(setf (gethash "brkpt-set" realgud:pydev-pat-hash)
      realgud:python-trepan-brkpt-set-pat)

;;  realgud-loc-pat that describes a "delete breakpoint" line
(setf (gethash "brkpt-del" realgud:pydev-pat-hash)
      realgud:python-trepan-brkpt-del-pat)

;; realgud-loc-pat that describes a debugger "disable" (breakpoint) response.
;; For example:
;;   Breakpoint 4 disabled.
(setf (gethash "brkpt-disable" realgud:pydev-pat-hash)
      realgud:python-trepan-brkpt-disable-pat)

;; realgud-loc-pat that describes a debugger "enable" (breakpoint) response.
;; For example:
;;   Breakpoint 4 enabled.
(setf (gethash "brkpt-enable" realgud:pydev-pat-hash)
      realgud:python-trepan-brkpt-enable-pat)

;; realgud-loc-pat for a termination message.
(setf (gethash "termination" realgud:pydev-pat-hash)
       "^pydevc: That's all, folks...")

(setf (gethash "font-lock-keywords" realgud:pydev-pat-hash)
      realgud:python-debugger-font-lock-keywords)

(setf (gethash "pydev" realgud-pat-hash) realgud:pydev-pat-hash)

(defvar realgud:pydev-command-hash (make-hash-table :test 'equal)
  "Hash key is command name like 'shell' and the value is
  the pydev command to use, like 'python'")

(setf (gethash "eval"  realgud:pydev-command-hash) "eval %s")
(setf (gethash "shell" realgud:pydev-command-hash) "python")
(setf (gethash "until" realgud-command-hash) "continue %l")

(setf (gethash "quit" realgud:pydev-command-hash) "exit")
(setf (gethash "delete" realgud:pydev-command-hash) "clear")
(setf (gethash "return" realgud:pydev-command-hash) "return")


(setf (gethash "pydev" realgud-command-hash) realgud:pydev-command-hash)

(provide-me "realgud:pydev-")
