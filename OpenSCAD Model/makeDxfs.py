# Copyright 2025 - Geoff SObering - All Rights Reserved
# Licensed under the GNU GENERAL PUBLIC LICENSE, Version 3

import os
import re
import subprocess
from time import sleep

betweenJobsSleep_s = 1;


def main(open_scad_file, dirDepth, build_fa, build_fs, osc, make_flag, list_make_flags):
    base_name = open_scad_file.split('.scad')[0]

    make_flags = [re.findall(r'^makeDxf(.*) = false;', line) for line in open(open_scad_file)]
    make_flags = list(map(lambda x: x[0], filter(lambda x: len(x) == 1, make_flags)))

    if list_make_flags:
        print(f"Available flags in '{open_scad_file}':")
        for flag in make_flags:
            print(f"   {flag}")
        return
    
    outputDir = '../' * dirDepth
    print(f'Output directory = {outputDir}')

    if make_flags:
        if make_flag and make_flag not in make_flags:
            print(f"ERROR: Unknown command-line make-flag: '{make_flag}'")
            return
        procs = []
        for flag in make_flags:
            if make_flag and make_flag != flag:
                continue
            print(f"\nStarting: {flag}")
            procs.append(subprocess.Popen(
                [
                    osc,
                    '-o', outputDir + base_name + ' ' + flag + '.dxf',
                    '--backend', 'Manifold',
                    '-D', 'build_fa=' + str(build_fa),
                    '-D', 'build_fs=' + str(build_fs),
                    '-D', 'developmentRender=false',
                    '-D', 'makeDxf' + flag + '=true',
                    open_scad_file
                ],
                bufsize=1, 
                universal_newlines=True))
            sleep(betweenJobsSleep_s)

        print('\nWaiting...', end='')
        for p in procs:
            p.wait()

        print("\nAll commands completed.\n")
              
        err_count = 0;
        for p in procs: 
            if(p.returncode != 0): err_count += 1
        if(err_count == 0): print("All commands completed with no errors.")
        else: print(f"\n\n=======> ERROR: {err_count} errors occured.\n\n")
    else:
        ret = subprocess.run(
            [
                osc,
                '-o', outputDir + base_name + '.stl',
                '--backend', 'Manifold',
                '-D', 'build_fa=' + str(build_fa),
                '-D', 'build_fs=' + str(build_fs),
                '-D', 'developmentRender=false',
                open_scad_file
            ],
            bufsize=1, 
            universal_newlines=True,
        )

        print(f"ret = {ret}")
        print(f"ret.returncode = {ret.returncode}")

        if(ret.returncode != 0):
            print(f"ERROR processing '{open_scad_file}'")

    print("Done!")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Create STLs from an OpenSCAD file.")
    parser.add_argument("open_scad_file", type=str, help="OpenSCAD file to render.")
    parser.add_argument("--dirDepth", "-d", type=int, default=1, help="Depth of the SCAD file from the STL destination.")
    parser.add_argument("--build_fa", "-fa", type=int, default=2, help="Rendering angle.")
    parser.add_argument("--build_fs", "-fs", type=float, default=0.5, help="Rendering minimum length.")
    parser.add_argument("--make_flag", "-mf", type=str, default="", help="Make-flag to render.")
    parser.add_argument("--list", "-l", action='store_true', help="List Make-flags in file.")
    parser.add_argument(
        "-osc",
        type=str,
        default=r"C:\tools\OpenSCAD-2025.12.09-x86-64\openscad.exe", #"C:\Program Files\OpenSCAD\openscad.exe",
        help="OpenSCAD executable path.")

    args = parser.parse_args()
    print(args)

    main(
        args.open_scad_file, 
        args.dirDepth,
        args.build_fa, 
        args.build_fs, 
        args.osc, 
        args.make_flag,
        args.list)
