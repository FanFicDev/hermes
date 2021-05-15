#!/usr/bin/bash

list="$(~/hermes/he_listCommands)"
complete -W "${list}" hermes

# TODO: default support for aliases?
complete -W "${list}" he

