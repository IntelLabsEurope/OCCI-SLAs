#!/usr/bin/env bash
kill -9 $(ps -ef| grep "runme.py" | grep -v grep | awk '{ print $2 }')
