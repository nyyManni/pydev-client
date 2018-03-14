;; Copyright (C) 2017 Henrik Nyman

;; Author: Henrik Nyman <henrikjohannesnyman@gmail.com>

;; This program is free software; you can redistribute it and/or modify
;; it under the terms of the GNU General Public License as published by
;; the Free Software Foundation, either version 3 of the License, or
;; (at your option) any later version.

(require 'python) ; for python-shell-interpreter
;; (require 'load-relative)
;; (require-relative-list '("../../common/helper") "realgud-")
;; (require-relative-list '("../../common/run")    "realgud:")
(require-relative-list '("core" "track-mode") "realgud:pydev-")

;; This is needed, or at least the docstring part of it is needed to
;; get the customization menu to work in Emacs 24.
(defgroup realgud:pydev nil
  "The realgud interface to the Python debugger, pydev"
  :group 'realgud
  :group 'python
  :version "24.3")

(declare-function pydev-query-cmdline  'realgud:pydev-core)
(declare-function pydev-parse-cmd-args 'realgud:pydev-core)
(declare-function realgud:run-debugger 'realgud:run)
(declare-function realgud:run-process  'realgud:core)
(declare-function realgud:flatten      'realgud-utils)

;; -------------------------------------------------------------------
;; User-definable variables
;;

(defcustom realgud:pydev-command-name
  "pydevc"
  "File name for executing the Python debugger and command options.
This should be an executable on your path, or an absolute file name."
  :type 'string
  :group 'realgud:pydev)

(defcustom realgud:pydev-port
  50505
  "Port number for PyDev server to listen on."
  :type 'number
  :group 'realgud:pydev)


(declare-function pydev-track-mode (bool))

;; -------------------------------------------------------------------
;; The end.
;;

;;;###autoload
(defun realgud:pydev (&optional opt-cmd-line no-reset)
  "Invoke the pydev Python debugger and start the Emacs user interface.

String OPT-CMD-LINE is treated like a shell string; arguments are
tokenized by `split-string-and-unquote'. The tokenized string is
parsed by `pydev-parse-cmd-args' and path elements found by that
are expanded using `realgud:expand-file-name-if-exists'.

Normally, command buffers are reused when the same debugger is
reinvoked inside a command buffer with a similar command. If we
discover that the buffer has prior command-buffer information and
NO-RESET is nil, then that information which may point into other
buffers and source buffers which may contain marks and fringe or
marginal icons is reset. See `loc-changes-clear-buffer' to clear
fringe and marginal icons."
  (interactive)
  (realgud:run-debugger "pydev"
			'pydev-query-cmdline
			'pydev-parse-cmd-args
			'realgud:pydev-minibuffer-history
			opt-cmd-line no-reset
                        (when opt-cmd-line
                          (car (last (split-string opt-cmd-line))))))

;;;###autoload
(defalias 'pydev 'realgud:pydev)

;;;###autoload
(defun realgud:pydev-delayed ()
  "This is like `pydev', but assumes inside the program to be debugged, you
have a call to the debugger somewhere, e.g. 'from trepan.api import debug; debug()'.
Therefore we invoke python rather than the debugger initially.
"
  (interactive)
  (let* ((initial-debugger python-shell-interpreter)
	 (actual-debugger "pydev")
	 (cmd-str (pydev-query-cmdline initial-debugger))
	 (cmd-args (split-string-and-unquote cmd-str))
	 ;; XXX: python gets registered as the interpreter rather than
	 ;; a debugger, and the debugger position (nth 1) is missing:
	 ;; the script-args takes its place.
	 (parsed-args (pydev-parse-cmd-args cmd-args))
	 (script-args (nth 1 parsed-args))
	 (script-name (car script-args))
	 (parsed-cmd-args
	  (cl-remove-if 'nil (realgud:flatten parsed-args))))
    (realgud:run-process actual-debugger script-name parsed-cmd-args
			 'realgud:pydev-deferred-minibuffer-history)))



(defun realgud:pydev-start-daemon (filename modulep args)
  "Start remote debuggee with pydev.
The debuggee will load FILENAME with arguments ARGS.
If MODULEP is t, load a python module named FILENAME instead of a file."
  (let* ((key (file-name-nondirectory filename))
         (process (make-process :name (concat "pydevd: " key)
                                :buffer (concat "*pydevd: " key "*")
                                :noquery t
                                :command (remove
                                          nil
                                          `("pydevd" "--port"
                                            ,(number-to-string realgud:pydev-port)
                                            ,(when modulep "--module")
                                            "--server" "--file"
                                            ,filename ,@args)))))

    ;; This is required for supporting colored output from the process.
    (with-current-buffer (process-buffer process)
      (display-buffer (current-buffer))
      (require 'shell)
      (shell-mode)
      (set-process-filter process 'comint-output-filter))))

(defun realgud:pydev-debug-file (filename &rest args)
  "Start debugger with a FILENAME and command line arguments ARGS."
  (realgud:pydev-start-daemon filename nil args)
  (realgud:pydev (concat "pydevc --server 127.0.0.1 --port "
                         (number-to-string realgud:pydev-port)
                         " --print-locals=lisp"
                         " --autostart --break-at-start --file "
                         filename)))

;;;###autoload
(defun realgud:pydev-current-file (&optional with-args)
  "Start debugger in current file.

With prefix-argument WITH-ARGS, prompt for additional arguments to the script."
  (interactive "P")
  (let ((args (when with-args (read-from-minibuffer "args: "))))
    (realgud:pydev-debug-file (buffer-file-name))))

(defun realgud:pydev--module-entry-point (name)
  "Full path to entry point (__main__.py) of module NAME."
  (concat
   (file-name-directory
    (s-trim
     (let ((path
            (shell-command-to-string (concat "python -c 'import " name
                                             "; print( " name ".__file__)'"))))
       (when (s-contains-p "Traceback (most recent call last):" path)
        (user-error "Module %s not found" name))
      path)))
   "__main__.py"))


;;;###autoload
(defun realgud:pydev-module (name &rest args)
  "Start debugger from module NAME with command line arguments ARGS."
  (interactive
   (split-string (read-from-minibuffer
                  "Module name (arguments separated with space): ")))

  (realgud:pydev-start-daemon name t args)
  (realgud:pydev (concat "pydevc --server 127.0.0.1 --port "
                         (number-to-string realgud:pydev-port)
                         " --print-locals=lisp"
                         " --autostart --break-at-start --file "
                         (realgud:pydev--module-entry-point name))))

(realgud-deferred-invoke-setup "pydev")

(provide-me "realgud-")
