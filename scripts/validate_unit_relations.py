#!/usr/bin/env python3
from validate_loadouts import ARMIES,validate_army
def main():
    for army in ARMIES:validate_army(army)
    print("embedded Unit_Profiles relationship validation: OK")
if __name__=="__main__":main()
