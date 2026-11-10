"""Run the whole pipeline. Every step is resumable; the long ones (02_pc4, 04_geocode) checkpoint to raw/*.jsonl.

    python -I build_all.py            # full run
    python -I build_all.py --skip-geocode   # build outputs from whatever the caches hold
"""
import os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = ["01_download.py", "02_pc4.py", "04_geocode.py", "05_build_po.py", "06_build_vo.py",
         "07_build_pc4.py", "08_build_meta.py", "09_validate.py"]


def main():
    skip = "--skip-geocode" in sys.argv
    for s in STEPS:
        if skip and s in ("02_pc4.py", "04_geocode.py"):
            continue
        print("==", s, flush=True)
        r = subprocess.run([sys.executable, "-I", os.path.join(HERE, s)])
        if r.returncode != 0:
            raise SystemExit("step failed: " + s)


if __name__ == "__main__":
    main()
