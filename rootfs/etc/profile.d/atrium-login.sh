# atrium-login: show the login banner (/usr/local/sbin/atrium-motd) for an SSH login shell.
# The prompt itself stays Fedora's (/etc/profile.d/bash-color-prompt.sh) - it is colored already.
# Installed as /etc/profile.d/atrium-login.sh (bash reads it for login shells via /etc/profile).
# 2026-10-13: created (user: "the console is colored already, but there is no intro with data at login")
[ -n "${BASH_VERSION:-}" ] || return 0
case $- in *i*) ;; *) return 0 ;; esac

# only for an SSH login shell (not for scp/sftp, su, cron, the TV session)
if shopt -q login_shell && [ -n "${SSH_TTY:-}" ] && [ -x /usr/local/sbin/atrium-motd ]; then
    /usr/local/sbin/atrium-motd
fi
