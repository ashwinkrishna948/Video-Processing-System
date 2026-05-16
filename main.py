"""Entry point.

    python main.py --url "https://youtube.com/watch?v=..."
    python main.py --subtitle input.srt --lang Telugu
    python main.py --subtitle input.txt --lang Hindi --output out.srt
"""
import argparse
import sys

from dotenv import load_dotenv
load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(description="Video pipeline or subtitle translation.")
    parser.add_argument("--url",      help="YouTube URL → full video analysis + XLS report")
    parser.add_argument("--subtitle", metavar="FILE", help="SRT/TXT → bilingual subtitle file")
    parser.add_argument("--lang",     default="Telugu", help="Translation language (default: Telugu)")
    parser.add_argument("--output",   default="",       help="Output path for subtitle mode")
    parser.add_argument("--workers",  type=int, default=8)
    args = parser.parse_args()

    if args.url:
        from pipeline import run
        report = run(args.url)
        print(f"\nReport saved: {report}")

    elif args.subtitle:
        from subtitle import run as sub_run
        sub_run(args.subtitle, args.lang, args.output, args.workers)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
