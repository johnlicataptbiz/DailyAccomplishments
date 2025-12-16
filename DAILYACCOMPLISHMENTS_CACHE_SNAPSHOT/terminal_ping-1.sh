#!/usr/bin/env bash
# ActivityTracker terminal ping hook for zsh/fish/bash (zsh shown below)
# Usage (zsh): add to your ~/.zshrc
#   source "$HOME/terminal_ping.sh"

# zsh preexec hook
if [ -n "$ZSH_VERSION" ]; then
  function _at_ping_preexec() {
    command -v python3 >/dev/null 2>&1 || return 0
    PY=python3
    SCRIPT="$HOME/activity_tracker.py"
    [ -f "$SCRIPT" ] || return 0
    ("$PY" "$SCRIPT" ping --cwd "$PWD" >/dev/null 2>&1 &)
  }
  autoload -Uz add-zsh-hook 2>/dev/null || true
  add-zsh-hook preexec _at_ping_preexec 2>/dev/null || true
fi

# fish users can add a similar function in config.fish:
# function __at_ping --on-event fish_preexec; python3 ~/activity_tracker.py ping --cwd $PWD ^/dev/null &; end

