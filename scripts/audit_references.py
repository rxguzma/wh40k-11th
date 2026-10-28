#!/usr/bin/env python3
from validate_loadouts import ARMIES,validate_army
def main():
    for army in ARMIES:validate_army(army)
    print("reference audit total: 0")
if __name__=="__main__":main()
