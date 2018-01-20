;;; realgud-pydev.el --- realgud front-end to the Python PyDev debugger

;; Author: Rocky Bernstein
;; Version: 1.0
;; Package-Type: multi
;; Package-Requires: ((realgud "1.4.3") (cl-lib "0.5") (emacs "24"))
;; URL: http://github.com/nyyManni/pydev-client
;; Compatibility: GNU Emacs 24.x

;; Copyright (C) 2017 Henrik Nyman

;; Author: Henrik Nyman <henrikjohannesnyman@gmail.com>

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

;;; Commentary:

;; realgud support for the Python PyDev debugger
;;
;; PyDev is the Python debugger used in Eclipse Python IDE and PyCharm. It has
;; support for debugging threaded applications such as Django and CherryPy.

;;; Code:

;; Press C-x C-e at the end of the next line configure the program in
;; for building via "make" to get set up.
;; (compile (format "EMACSLOADPATH=:%s:%s ./autogen.sh" (file-name-directory (locate-library "test-simple.elc")) (file-name-directory (locate-library "realgud.elc"))))

(require 'load-relative)

(defgroup realgud-pydev  nil
  "Realgud interface to Python PyDev debugger"
  :group 'realgud
  :version "24.3")

(require-relative-list '("./pydev/pydev") "realgud-")

(provide-me)

;;; realgud-pydev.el ends here
