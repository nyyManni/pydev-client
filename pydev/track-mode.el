;; Copyright (C) 2015-2016 Free Software Foundation, Inc

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
;; Python "pydev" Debugger tracking a comint buffer.

(require 'load-relative)
(require-relative-list '(
			 "../../common/cmds"
			 "../../common/menu"
			 "../../common/track"
			 "../../common/track-mode"
			 )
		       "realgud-")
(require-relative-list '("core" "init") "realgud:pydev-")
(require-relative-list '("../../lang/python") "realgud-lang-")

(declare-function realgud-track-mode 'realgud-track-mode)
(declare-function realgud-track-mode-hook 'realgud-track-mode)
(declare-function realgud-track-mode-setup 'realgud-track-mode)
(declare-function realgud:track-set-debugger 'realgud-track-mode)
(declare-function realgud-python-populate-command-keys 'realgud-lang-python)

(realgud-track-mode-vars "pydev")

(declare-function realgud-track-mode(bool))

(realgud-python-populate-command-keys pydev-track-mode-map)

(defun pydev-track-mode-hook()
  (if pydev-track-mode
      (progn
	(use-local-map pydev-track-mode-map)
	(message "using pydev mode map")
	)
    (message "pydev track-mode-hook disable called")
    )
)

(define-minor-mode pydev-track-mode
  "Minor mode for tracking pydev source locations inside a process shell via realgud.
pydev is a Python debugger. See URL `http://code.google.com/p/python3-trepan/'.

If called interactively with no prefix argument, the mode is toggled. A prefix
argument, captured as ARG, enables the mode if the argument is positive, and
disables it otherwise.

\\{pydev-track-mode-map}
"
  :init-value nil
  ;; :lighter " pydev"   ;; mode-line indicator from realgud-track is sufficient.
  ;; The minor mode bindings.
  :global nil
  :group 'realgud:pydev
  :keymap pydev-track-mode-map
  (realgud:track-set-debugger "pydev")
  (if pydev-track-mode
      (progn
	(realgud-track-mode-setup 't)
	(pydev-track-mode-hook))
    (progn
      (setq realgud-track-mode nil)
      ))
)


(defun realgud-track-locals (text cmdmark &rest args)
  "Track local variables."
  (condition-case nil
      (when (realgud-cmdbuf?)
        (let ((locals-re "$$\\((\\(?:.*
\\)*.*)\\)$\\$"))
          (when(string-match locals-re text)
            (let ((locals (car (read-from-string (match-string 1 text)))))

              (with-current-buffer (get-buffer-create "*realgud-locals*")
                (erase-buffer)
                (let ((len (1+ (apply #'max (mapcar
                                             (lambda (l)
                                               (length (symbol-name (car l))))
                                             locals)))))
                  (mapc
                   (lambda (l)
                     (insert (format (concat "%-" (number-to-string len) "s%s\n")
                                     (propertize (symbol-name (car l))
                                                 'face 'font-lock-type-face)
                                     (replace-regexp-in-string "
" "\\\\n" (cadr l)))))

                   locals)))))))
    (error nil)))

(advice-add 'realgud-track-loc :after 'realgud-track-locals)

(define-key pydev-short-key-mode-map "T" 'realgud:cmd-backtrace)

(provide-me "realgud:pydev-")
