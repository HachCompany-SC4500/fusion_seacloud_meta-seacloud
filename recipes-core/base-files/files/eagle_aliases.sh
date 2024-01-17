alias be0='systemctl stop backend'
alias be1='systemctl start backend'
alias be01='be0 && be1'
alias bes='systemctl status backend'
alias belog='tail -F /var/log/backend.log'

alias fe0='systemctl stop frontend'
alias fe1='systemctl start frontend'
alias fe01='fe0 && fe1'
alias fes='systemctl status frontend'
alias felog='tail -F /var/log/frontend.log'

alias fcc0='systemctl stop fcc'
# The command "systemctl reset-failed fcc.service" is here to avoid unexpected reboot
# after too many start attempts; see /etc/systemd/system/fcc.service for more information.
alias fcc1='systemctl reset-failed fcc.service && systemctl start fcc'
alias fcc01='fcc0 && fcc1'
alias fccs='systemctl status fcc'
alias fcclog='tail -F /var/log/fcc.log'

alias log0='systemctl stop logger-server'
alias log1='systemctl start logger-server'
alias log01='log0 && log1'
alias logs='systemctl status logger-server'
alias logconf='vi /etc/logger-server.conf'

# alias to put the device in development mode (e.g. after FIT test)
alias development-mode='touch /media/persistent/development'
