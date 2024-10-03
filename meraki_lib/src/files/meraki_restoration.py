#!/usr/bin/env python3
"""
Written by Christopher Corby, 5/26/22

This is a script to restore the dashboard from a backup through meraki_backup.py

History:
5/26/22 cmc Created

Requirements:
python 3, meraki, datetime, sys, getopt, meraki.aio, json, os, requests, asyncio

"""

def main(argv):
    """
    Parses arguments to get the API key
    """
    API_KEY = ''
    try:
        opts, args = getopt.getopt(argv, 'k:p:o:')
    except getopt.GetoptError:
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-k':
            API_KEY = arg
        if opt == '-p':
            MAIN_PATH = arg
    if API_KEY == '':
        sys.exit(2)
    
