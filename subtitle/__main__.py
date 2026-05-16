"""python -m subtitle input.srt --lang Telugu"""
import argparse
from subtitle import run

p = argparse.ArgumentParser(description="Bilingual SRT subtitle generator")
p.add_argument("input")
p.add_argument("--lang",    default="Telugu")
p.add_argument("--output",  default="")
p.add_argument("--workers", type=int, default=8)
args = p.parse_args()
run(args.input, args.lang, args.output, args.workers)
